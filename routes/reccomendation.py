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
from .auth import get_current_user
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

    data = request.get_json()
    if not data or "recipes" not in data:
        return jsonify({"error": "recipes field required"}), 400

    # Filter here as a safety net in case caller sends stale/inactive recipes
    active_recipes = [r for r in data["recipes"] if r.get("active", True)]

    try:
        recommender.fit(active_recipes)
        recommender.save(MODEL_PATH)
        return jsonify({"status": "ok", "trained_on": len(active_recipes)})
    except Exception as e:
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


# routes/recommendations.py

@recommendations_bp.route("/recommendations", methods=["POST"])
def recommend():
    if not recommender.fitted:
        return jsonify({"error": "Model not trained yet"}), 503

    data      = request.get_json() or {}
    n         = data.get("n", 5)
    user_id   = data.get("user_id")
    diversity = max(0.0, min(1.0, float(data.get("diversity", 0.5))))

    # ── 1. Filter-based ──────────────────────────────────────────────────────
    cuisine_type  = data.get("cuisine_type")
    max_cook_time = data.get("max_cook_time")
    ingredients   = [
        i.strip().lower()
        for i in data.get("ingredients", [])
        if isinstance(i, str) and i.strip()
    ]

    if cuisine_type or max_cook_time is not None or ingredients:
        try:
            if ingredients:
                results = recommender.recommend_by_ingredients(
                    ingredients=ingredients, n=n, user_id=user_id, diversity=diversity,
                )
            else:
                results = recommender.recommend_by_filters(
                    cuisine_type=cuisine_type, max_cook_time=max_cook_time,
                    n=n, user_id=user_id,
                )
            return jsonify({"recommendations": results, "mode": "filter"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ── 2. Personalized — fetch saved_recipes from Supabase ──────────────────
    # The model only needs the recipe objects, not the DB rows themselves.
    # We fetch here on the server so the client never has to send the full list.
    if user_id:
        try:
            from supabase_client import supabase  # your existing client

            rows = (
                supabase.table("saved_recipes")
                .select("recipe:recipes(*)")   # join to get full recipe data
                .eq("user_id", user_id)
                .execute()
                .data
            )
            favorite_recipes = [row["recipe"] for row in rows if row.get("recipe")]
        except Exception as e:
            # Non-fatal — fall through to cold start rather than erroring out
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
            cuisine_type=None, max_cook_time=None, n=n, user_id=user_id,
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