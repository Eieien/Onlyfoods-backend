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


# ── /recommend ───────────────────────────────────────────────────────────────

@recommendations_bp.route("/recommend", methods=["POST"])
def recommend_by_recipe():
    """
    Body: { "recipe": <RecipeCreateSchema>, "n": 5, "user_id": "optional" }
    Returns diverse, non-repeated recommendations similar to the given recipe.
    Pass user_id to enable seen tracking across calls.
    """
    data = request.get_json()
    if not data or "recipe" not in data:
        return jsonify({"error": "recipe field required"}), 400

    n       = data.get("n", 5)
    user_id = data.get("user_id")

    try:
        results = recommender.recommend_by_recipe(
            data["recipe"], n=n, user_id=user_id
        )
        return jsonify({"recommendations": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── /filter ──────────────────────────────────────────────────────────────────

@recommendations_bp.route("/filter", methods=["GET"])
def recommend_by_filters():
    """
    Query params: cuisine_type, max_cook_time, n, user_id
    Used for cold-start (new users with no swipe history).
    Excludes already-seen recipes if user_id is passed.
    """
    try:
        results = recommender.recommend_by_filters(
            cuisine_type  = request.args.get("cuisine_type"),
            max_cook_time = request.args.get("max_cook_time", type=int),
            n             = request.args.get("n", default=5, type=int),
            user_id       = request.args.get("user_id"),
        )
        return jsonify({"recommendations": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── /similar/<index> ─────────────────────────────────────────────────────────

@recommendations_bp.route("/similar/<int:index>", methods=["GET"])
def recommend_by_index(index):
    """
    Returns recipes similar to the recipe at position `index` in training data.
    Query params: n, user_id
    """
    n       = request.args.get("n", default=5, type=int)
    user_id = request.args.get("user_id")
    try:
        results = recommender.recommend_by_index(index, n=n, user_id=user_id)
        return jsonify({"recommendations": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── /swipe ───────────────────────────────────────────────────────────────────

@recommendations_bp.route("/swipe", methods=["POST"])
def record_swipe():
    """
    Records a swipe for the current user.
    Body: { "user_id": "...", "recipe": <RecipeCreateSchema>, "direction": "like"|"dislike" }
    """
    # Uncomment once auth is wired:
    # user = get_current_user()
    # if not user:
    #     return jsonify({"error": "unauthorized"}), 401
    # user_id = user["id"]

    data      = request.get_json()
    user_id   = data.get("user_id", "anon")
    recipe    = data.get("recipe")
    direction = data.get("direction")

    if not recipe or direction not in ("like", "dislike"):
        return jsonify({"error": "recipe and direction ('like'|'dislike') required"}), 400

    store = _swipe_store.setdefault(user_id, {"liked": [], "disliked": []})

    if direction == "like":
        titles = [r["title"] for r in store["liked"]]
        if recipe["title"] not in titles:
            store["liked"].append(recipe)
    else:
        if recipe["title"] not in store["disliked"]:
            store["disliked"].append(recipe["title"])

    return jsonify({"status": "recorded", "direction": direction})


# ── /personalized ────────────────────────────────────────────────────────────

@recommendations_bp.route("/personalized", methods=["POST"])
def recommend_personalized():
    """
    Builds a taste centroid from liked recipes using the embedding model,
    then queries KNN — much more accurate than the old sparse matrix centroid.

    Body (option A — pass recipes directly):
        { "liked_recipes": [...], "disliked_titles": [...], "n": 5, "user_id": "..." }

    Body (option B — look up from swipe store):
        { "user_id": "user_123", "n": 5 }
    """
    if not recommender.fitted:
        return jsonify({"error": "model not trained yet"}), 503

    data    = request.get_json() or {}
    n       = data.get("n", 5)
    user_id = data.get("user_id")

    # Resolve liked / disliked
    if user_id and "liked_recipes" not in data:
        store           = _swipe_store.get(user_id, {"liked": [], "disliked": []})
        liked_recipes   = store["liked"]
        disliked_titles = store["disliked"]
    else:
        liked_recipes   = data.get("liked_recipes", [])
        disliked_titles = data.get("disliked_titles", [])

    try:
        results = recommender.recommend_personalized(
            liked_recipes   = liked_recipes,
            disliked_titles = disliked_titles,
            n               = n,
            user_id         = user_id,
        )
        mode = "cold_start" if not liked_recipes else "personalized"
        return jsonify({"recommendations": results, "mode": mode})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── /by-ingredients ──────────────────────────────────────────────────────────

@recommendations_bp.route("/by-ingredients", methods=["GET"])
def recommend_by_ingredients():
    """
    Returns a randomized feed of recipes containing ALL of the given ingredients.
    Recipes may have additional ingredients beyond what was queried.

    Query params:
        ingredients  - comma-separated list e.g. ?ingredients=chicken,basil
        n            - number of results (default 10)
        user_id      - optional, enables seen tracking for fresh feeds
        diversity    - float 0.0–1.0, how shuffled the feed is (default 0.5)

    Example:
        GET /recommendations/by-ingredients?ingredients=chicken,basil&n=10&user_id=abc
    
    Response (200):
    {
        "ingredients_queried": ["chicken", "basil"],
        "count": 6,
        "recommendations": [
            { "recipe": { ... }, "similarity": null },
            ...
        ]
    }

    Error Responses:
        400 - No ingredients provided
        503 - Model not trained yet
        500 - Server error
    """
    if not recommender.fitted:
        return jsonify({"error": "Model not trained yet"}), 503

    raw_ingredients = request.args.get("ingredients", "")
    if not raw_ingredients:
        return jsonify({"error": "At least one ingredient is required"}), 400

    ingredients = [i.strip().lower() for i in raw_ingredients.split(",") if i.strip()]
    if not ingredients:
        return jsonify({"error": "At least one valid ingredient is required"}), 400

    n         = request.args.get("n", default=10, type=int)
    user_id   = request.args.get("user_id")
    diversity = request.args.get("diversity", default=0.5, type=float)
    diversity = max(0.0, min(1.0, diversity))  # clamp to 0.0–1.0

    try:
        results = recommender.recommend_by_ingredients(
            ingredients = ingredients,
            n           = n,
            user_id     = user_id,
            diversity   = diversity,
        )
        return jsonify({
            "ingredients_queried": ingredients,
            "count":               len(results),
            "recommendations":     results,
        }), 200
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