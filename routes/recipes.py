from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from supabase_client import supabase
from schemas import RecipeCreateSchema, RecipeUpdateSchema

recipes_bp = Blueprint("recipes", __name__)


@recipes_bp.route("", methods=["POST"])
@jwt_required()
def create_recipe():
    """
    POST /api/recipes
    Create a new recipe for the authenticated user.
    
    Auth Required: Yes (JWT token)
    
    Request body:
    {
        "title": "str (required)",
        "description": "str (required)",
        "ingredients": ["str"] (required, non-empty list),
        "steps": ["str"] (required, non-empty list),
        "cuisine_type": "str (required)",
        "difficulty": "easy|medium|hard (required)",
        "prep_time_minutes": int (required, >= 0),
        "cook_time_minutes": int (required, >= 0),
        "servings": int (required, >= 1),
        "image_url": "str (optional)",
        "is_published": bool (optional, default: false)
    }
    
    Response (201):
    {
        "data": {recipe object},
        "message": "Recipe created successfully"
    }
    """
    user_id = get_jwt_identity()
    data = request.get_json()
    
    # Validate request data
    schema = RecipeCreateSchema()
    errors = schema.validate(data)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400
    
    # Load and prepare data
    validated_data = schema.load(data)
    validated_data["author_id"] = user_id
    
    try:
        res = supabase.table("recipes").insert(validated_data).execute()
        
        if not res.data:
            return jsonify({"error": "Failed to create recipe"}), 500
        
        return jsonify({
            "data": res.data,
            "message": "Recipe created successfully"
        }), 201
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500


@recipes_bp.route("/<int:recipe_id>", methods=["GET"])
def get_recipe(recipe_id):
    """
    GET /api/recipes/<recipe_id>
    Retrieve a single recipe by ID.
    
    Auth Required: No
    
    Response (200):
    {
        "data": {recipe object},
        "message": "Recipe retrieved successfully"
    }
    """
    try:
        res = supabase.table("recipes").select("*").eq("id", recipe_id).execute()
        
        if not res.data:
            return jsonify({"error": "Recipe not found"}), 404
        
        return jsonify({
            "data": res.data[0],
            "message": "Recipe retrieved successfully"
        }), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500


@recipes_bp.route("/<int:recipe_id>", methods=["PUT"])
@jwt_required()
def update_recipe(recipe_id):
    """
    PUT /api/recipes/<recipe_id>
    Update a recipe (owner only).
    
    Auth Required: Yes (JWT token)
    
    Request body: (all fields optional, only provide fields to update)
    {
        "title": "str",
        "description": "str",
        "ingredients": ["str"],
        "steps": ["str"],
        "cuisine_type": "str",
        "difficulty": "easy|medium|hard",
        "prep_time_minutes": int,
        "cook_time_minutes": int,
        "servings": int,
        "image_url": "str",
        "is_published": bool
    }
    
    Response (200):
    {
        "data": {updated recipe object},
        "message": "Recipe updated successfully"
    }
    """
    user_id = get_jwt_identity()
    data = request.get_json()
    
    # Check if recipe exists
    res = supabase.table("recipes").select("author_id").eq("id", recipe_id).execute()
    
    if not res.data:
        return jsonify({"error": "Recipe not found"}), 404
    
    # Check ownership
    if res.data[0]["author_id"] != user_id:
        return jsonify({"error": "Forbidden"}), 403
    
    # Validate request data
    schema = RecipeUpdateSchema()
    errors = schema.validate(data)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400
    
    validated_data = schema.load(data)
    
    try:
        res = supabase.table("recipes").update(validated_data).eq("id", recipe_id).execute()
        
        if not res.data:
            return jsonify({"error": "Failed to update recipe"}), 500
        
        return jsonify({
            "data": res.data[0],
            "message": "Recipe updated successfully"
        }), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500


@recipes_bp.route("/<int:recipe_id>", methods=["DELETE"])
@jwt_required()
def delete_recipe(recipe_id):
    """
    DELETE /api/recipes/<recipe_id>
    Delete a recipe (owner only).
    
    Auth Required: Yes (JWT token)
    
    Response (200):
    {
        "message": "Recipe deleted successfully"
    }
    """
    user_id = get_jwt_identity()
    
    # Check if recipe exists and verify ownership
    res = supabase.table("recipes").select("author_id").eq("id", recipe_id).execute()
    
    if not res.data:
        return jsonify({"error": "Recipe not found"}), 404
    
    if res.data[0]["author_id"] != user_id:
        return jsonify({"error": "Forbidden"}), 403
    
    try:
        supabase.table("recipes").delete().eq("id", recipe_id).execute()
        
        return jsonify({"message": "Recipe deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500
