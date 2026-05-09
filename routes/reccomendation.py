from flask import Blueprint, jsonify, request
from flask import session
from supabase_client import supabase
from schemas import ProfileSchema, ProfileUpdateSchema
from utils.model import RecipeRecommender
from .auth import get_current_user

reccomendations_bp = Blueprint("reccomendations", __name__)

MODEL_PATH = "recipe_recommender.pkl"

recommender = RecipeRecommender.load(MODEL_PATH) if os.path.exists(MODEL_PATH) else RecipeRecommender()

@reccomendations_bp.route("/reccomendations/train", methods=["POST"])''
def train():
    """
    Body: { "recipes": [ <RecipeCreateSchema>, ... ] }
    """
    data = request.get_json()
    if not data or "recipes" not in data:
        return jsonify({"error": "recipes field required"}), 400

    try:
        recommender.fit(data["recipes"])
        recommender.save(MODEL_PATH)
        return jsonify({"status": "ok", "trained_on": len(data["recipes"])})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@reccomendations_bp.route("/reccomendations/reccomend", methods=["POST"])
def recommend_by_recipe():
    """
    Body: { "recipe": <RecipeCreateSchema>, "n": 5 }
    Returns recipes similar to the submitted recipe.
    """
    data = request.get_json()
    if not data or "recipe" not in data:
        return jsonify({"error": "recipe field required"}), 400

    n = data.get("n", 5)
    try:
        results = recommender.recommend_by_recipe(data["recipe"], n=n)
        return jsonify({"recommendations": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@reccomendations_bp.route("/reccomendations/filter", methods=["GET"])
def recommend_by_filters():
    """
    Query params: cuisine_type, difficulty, max_total_time, n
    Returns recipes matching the filters, ranked by cluster quality.
    """
    cuisine_type = request.args.get("cuisine_type")
    difficulty = request.args.get("difficulty")
    max_total_time = request.args.get("max_total_time", type=int)
    n = request.args.get("n", default=5, type=int)

    try:
        results = recommender.recommend_by_filters(
            cuisine_type=cuisine_type,
            difficulty=difficulty,
            max_total_time=max_total_time,
            n=n
        )
        return jsonify({"recommendations": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@reccomendations_bp.route("/recipes/<int:index>/similar", methods=["GET"])
def recommend_by_index(index):
    """
    Returns recipes similar to the recipe at position `index` in training data.
    """
    n = request.args.get("n", default=5, type=int)
    try:
        results = recommender.recommend_by_index(index, n=n)
        return jsonify({"recommendations": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@reccomendations_bp.route("/recipes/filter", methods=["GET"])
def recommend_by_filters():
    """
    Query params: cuisine_type, difficulty, max_total_time, n
    e.g. /recipes/filter?cuisine_type=italian&difficulty=easy&max_total_time=30
    """
    try:
        results = recommender.recommend_by_filters(
            cuisine_type   = request.args.get("cuisine_type"),
            difficulty     = request.args.get("difficulty"),
            max_total_time = request.args.get("max_total_time", type=int),
            n              = request.args.get("n", default=5, type=int)
        )
        return jsonify({"recommendations": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500