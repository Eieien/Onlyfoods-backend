"""
routes/recommendations.py

Changes in this version:
  - PyTorch embedding model replaces TF-IDF (via updated model.py)
  - user_id passed to recommend methods → seen tracking (no repeated results)
  - Diversity built into recommend_by_recipe (top results kept, rest shuffled)
  - POST /recommendations/fine-tune  → fine-tunes model on swipe triplets
  - POST /recommendations/reset-seen → clears seen history for a user
  - /personalized uses model's recommend_personalized() directly
"""

from flask import Blueprint, jsonify, request
from utils.model import RecipeRecommender
import os

recommendations_bp = Blueprint("recommendations", __name__)

MODEL_PATH = "recipe_recommender.pkl"
recommender = (
    RecipeRecommender.load(MODEL_PATH)
    if os.path.exists(MODEL_PATH)
    else RecipeRecommender()
)

# In-memory swipe store
# Structure: { user_id: { "liked": [...recipes], "disliked": [...titles] } }
_swipe_store: dict = {}


# ── /train ───────────────────────────────────────────────────────────────────

@recommendations_bp.route("/train", methods=["POST"])
def train():
    # If you're pulling recipes from Supabase directly instead of receiving them in body:
    # recipes = supabase.table("recipes").select("*").eq("active", True).eq("is_published", True).execute().data
    from supabase_client import supabase

    try:
        rows = (
            supabase.table("recipes")
            .select("*, recipe_media(*)")        # ← includes media
            .eq("active", True)
            .eq("is_published", True)
            .execute()
            .data
        )
    except Exception as e:
        print(f"[train] Supabase error: {e}")
        return jsonify({"error": "Failed to fetch recipes", "details": str(e)}), 500



    # data = request.get_json()
    # if not data or "recipes" not in data:
    #     return jsonify({"error": "recipes field required"}), 400

    if not rows:
        return jsonify({"error": "No recipes found"}), 400

    # Filter here as a safety net in case caller sends stale/inactive recipes
    # active_recipes = [r for r in data["recipes"] if r.get("active", True)]

    # try:
    #     recommender.fit(active_recipes)
    #     recommender.save(MODEL_PATH)
    #     return jsonify({"status": "ok", "trained_on": len(active_recipes)})
    # except Exception as e:
    #     return jsonify({"error": str(e)}), 500

    try:
        recommender.fit(rows)
        recommender.save(MODEL_PATH)
        return jsonify({"status": "ok", "trained_on": len(rows)})
    except Exception as e:
        print(f"[train] fit() error: {e}")
        return jsonify({"error": str(e)}), 500

# ── /fine-tune ───────────────────────────────────────────────────────────────

@recommendations_bp.route("/fine-tune", methods=["POST"])
def fine_tune():
    """
    Fine-tunes the embedding model on swipe triplets so recommendations
    evolve based on user behavior without full retraining.

    Body: {
        "swipe_history": [
            { "anchor": <recipe>, "liked": <recipe>, "disliked": <recipe> },
            ...
        ],
        "epochs": 5   // optional, default 5
    }
    Call this nightly or after every 50 swipes accumulate.
    """
    data          = request.get_json() or {}
    swipe_history = data.get("swipe_history", [])
    epochs        = data.get("epochs", 5)

    if len(swipe_history) < 3:
        return jsonify({"error": "Need at least 3 swipe triplets to fine-tune"}), 400

    try:
        recommender.fine_tune_on_swipes(swipe_history, epochs=epochs)
        recommender.save(MODEL_PATH)
        return jsonify({"status": "ok", "fine_tuned_on": len(swipe_history)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# routes.py

@recommendations_bp.route("/", methods=["POST"])
def recommend():
    if not recommender.fitted:
        return jsonify({"error": "Model not trained yet"}), 503

    data      = request.get_json() or {}
    n         = data.get("n", 5)
    user_id   = data.get("user_id")
    diversity = max(0.0, min(1.0, float(data.get("diversity", 0.5))))

    # ── 1. Filter-based ──────────────────────────────────────────────────────
    cuisine_types = data.get("cuisine_types", [])
    if isinstance(cuisine_types, str):
        cuisine_types = [cuisine_types]
    if not isinstance(cuisine_types, list):
        cuisine_types = []

    cook_time_map = {
        "under_30": (None, 30),
        "30_to_60": (30,   60),
        "over_60":  (60,   None),
    }
    cook_time_key             = data.get("cook_time")
    min_cook_time, max_cook_time = cook_time_map.get(cook_time_key, (None, None))

    servings_map = {
        "1":      (1, 1),
        "2_to_3": (2, 3),
        "4_to_5": (4, 5),
        "6_to_7": (6, 7),
        "8_plus": (8, None),
    }
    servings_key            = data.get("servings")
    min_servings, max_servings = servings_map.get(servings_key, (None, None))

    ingredients = [
        i.strip().lower()
        for i in data.get("ingredients", [])
        if isinstance(i, str) and i.strip()
    ]

    has_filters = bool(cuisine_types or cook_time_key or servings_key or ingredients)

    if has_filters:
        try:
            if ingredients:
                results = recommender.recommend_by_ingredients(
                    ingredients=ingredients, n=n, user_id=user_id, diversity=diversity,
                )
            else:
                results = recommender.recommend_by_filters(
                    cuisine_types=cuisine_types,
                    min_cook_time=min_cook_time,
                    max_cook_time=max_cook_time,
                    min_servings=min_servings,
                    max_servings=max_servings,
                    n=n,
                    user_id=user_id,
                )
            return jsonify({"recommendations": results, "mode": "filter"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ── 2. Personalized — fetch saved_recipes from Supabase ──────────────────
    if user_id:
        try:
            from supabase_client import supabase

            rows = (
                supabase.table("saved_recipes")
                .select("recipe:recipes(*, recipe_media(*))")
                .eq("user_id", user_id)
                .execute()
                .data
            )
            favorite_recipes = [row["recipe"] for row in rows if row.get("recipe")]
        except Exception as e:
            print(f"[recommend] Could not fetch favorites for {user_id}: {e}")
            favorite_recipes = []
    else:
        favorite_recipes = []

    if favorite_recipes:
        try:
            results = recommender.recommend_personalized(
                liked_recipes=favorite_recipes,
                disliked_titles=[],
                n=n,
                user_id=user_id,
            )
            # If exhausted, reset seen and retry
            if not results and user_id:
                recommender.reset_seen(user_id)
                results = recommender.recommend_personalized(
                    liked_recipes=favorite_recipes,
                    disliked_titles=[],
                    n=n,
                    user_id=user_id,
                )
            return jsonify({"recommendations": results, "mode": "personalized"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ── 3. Anchor-recipe similarity ───────────────────────────────────────────
    anchor_recipe = data.get("recipe")
    anchor_index  = data.get("index")

    if anchor_recipe is not None:
        try:
            results = recommender.recommend_by_recipe(
                anchor_recipe, n=n, user_id=user_id
            )
            return jsonify({"recommendations": results, "mode": "similarity"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    if anchor_index is not None:
        try:
            results = recommender.recommend_by_index(anchor_index, n=n, user_id=user_id)
            return jsonify({"recommendations": results, "mode": "similarity"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

# ── 4. Cold start ─────────────────────────────────────────────────────────
    try:
        results = recommender.recommend_by_filters(
            cuisine_types=[], min_cook_time=None, max_cook_time=None,
            min_servings=None, max_servings=None, n=n, user_id=user_id,
        )
        # If nothing returned, seen list is exhausted — reset and try again
        if not results and user_id:
            recommender.reset_seen(user_id)
            results = recommender.recommend_by_filters(
                cuisine_types=[], min_cook_time=None, max_cook_time=None,
                min_servings=None, max_servings=None, n=n, user_id=user_id,
            )
        return jsonify({"recommendations": results, "mode": "cold_start"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# ── /reset-seen ──────────────────────────────────────────────────────────────

@recommendations_bp.route("/reset-seen", methods=["POST"])
def reset_seen():
    """
    Clears the seen history for a user so they can get fresh recommendations.
    Body: { "user_id": "..." }
    Useful for testing or when a user explicitly wants to rediscover recipes.
    """
    data    = request.get_json() or {}
    user_id = data.get("user_id")

    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    recommender.reset_seen(user_id)
    return jsonify({"status": "ok", "message": f"Seen history cleared for {user_id}"})