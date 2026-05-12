from flask import Blueprint, request, jsonify
from supabase_client import supabase, get_authenticated_client
from schemas import RecipeCreateSchema, RecipeUpdateSchema
from .auth import get_current_user

recipes_bp = Blueprint("recipes", __name__)


# ── GET /recipes/ ─────────────────────────────────────────────────────────────

@recipes_bp.route("/", methods=["GET"])
def get_all_public_recipes():
    """
    GET /recipes/
    Get all published recipes (public, no auth required).

    Response (200):
    {
        "data": [recipe objects],
        "message": "Recipes retrieved successfully"
    }
    """
    try:
        res = supabase.table("recipes").select("*").eq("is_published", True).execute()
        return jsonify({
            "data": res.data,
            "message": "Recipes retrieved successfully"
        }), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500


# ── GET /recipes/get_all ──────────────────────────────────────────────────────

@recipes_bp.route("/get_all", methods=["GET"])
def get_all_recipes():
    """
    GET /recipes/get_all
    Get all recipes including unpublished, with media (no auth required).

    Response (200):
    {
        "data": [recipe objects with media],
        "message": "Recipes retrieved successfully"
    }
    """
    try:
        res = supabase.table("recipes").select("*, recipe_media(*)").execute()
        return jsonify({
            "data": res.data,
            "message": "Recipes retrieved successfully"
        }), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500


# ── GET /recipes/<recipe_id> ──────────────────────────────────────────────────

@recipes_bp.route("/<int:recipe_id>", methods=["GET"])
def get_recipe(recipe_id):
    """
    GET /recipes/<recipe_id>
    Get a single recipe by ID, including its media.

    Response (200):
    {
        "data": {recipe object with media},
        "message": "Recipe retrieved successfully"
    }

    Error Responses:
        404 - Recipe not found
        500 - Database error
    """
    try:
        res = supabase.table("recipes").select("*, recipe_media(*)").eq("id", recipe_id).execute()

        if not res.data:
            return jsonify({"error": "Recipe not found"}), 404

        return jsonify({
            "data": res.data[0],
            "message": "Recipe retrieved successfully"
        }), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500


# ── POST /recipes/create ──────────────────────────────────────────────────────

@recipes_bp.route("/create", methods=["POST"])
def create_recipe():
    """
    POST /recipes/create
    Create a new recipe for the authenticated user.

    Auth Required: Yes

    Request Body:
    {
        "title":             "str (required) - name of the recipe",
        "description":       "str (required) - short description",
        "ingredients":       ["str"] (required) - non-empty list of ingredients,
        "steps":             ["str"] (required) - cooking steps in order,
        "cuisine_type":      "str (required) - e.g. Filipino, Italian, Japanese",
        "cook_time_minutes": int (required, >= 0) - cooking time in minutes,
        "servings":          int (required, >= 1) - number of servings,
        "is_published":      bool (optional, default: false)
    }

    Example:
    {
        "title": "Chicken Adobo",
        "description": "A classic Filipino braised chicken dish",
        "ingredients": ["500g chicken", "1/2 cup soy sauce", "1/2 cup vinegar", "5 cloves garlic"],
        "steps": ["Marinate chicken for 30 mins", "Brown chicken in pan", "Simmer for 30 mins"],
        "cuisine_type": "Filipino",
        "cook_time_minutes": 30,
        "servings": 4,
        "is_published": true
    }

    Response (201):
    {
        "data": {recipe object},
        "message": "Recipe created successfully"
    }

    Error Responses:
        400 - Validation failed (missing or invalid fields)
        401 - Not authenticated
        500 - Database error
    """
    user_id, access_token, err = get_current_user()
    if err:
        return err

    data = request.get_json()

    schema = RecipeCreateSchema()
    errors = schema.validate(data)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    validated_data = schema.load(data)

    # favorites_count is dump_only — strip it so it's never sent on insert
    validated_data.pop("favorites_count", None)
    validated_data["author_id"] = user_id

    try:
        client = get_authenticated_client(access_token)
        res = client.table("recipes").insert(validated_data).execute()

        if not res.data:
            return jsonify({"error": "Failed to create recipe"}), 500

        return jsonify({
            "data": res.data[0],
            "message": "Recipe created successfully"
        }), 201
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500


# ── PUT /recipes/update/<recipe_id> ──────────────────────────────────────────

@recipes_bp.route("/update/<int:recipe_id>", methods=["PUT"])
def update_recipe(recipe_id):
    """
    PUT /recipes/update/<recipe_id>
    Update a recipe (owner only). Only send fields you want to change.

    Auth Required: Yes

    Request Body (all fields optional):
    {
        "title":             "str",
        "description":       "str",
        "ingredients":       ["str"],
        "steps":             ["str"],
        "cuisine_type":      "str",
        "cook_time_minutes": int (>= 0),
        "servings":          int (>= 1),
        "is_published":      bool
    }

    Response (200):
    {
        "data": {updated recipe object},
        "message": "Recipe updated successfully"
    }

    Error Responses:
        400 - Validation failed
        401 - Not authenticated
        403 - Forbidden (not the owner)
        404 - Recipe not found
        500 - Database error
    """
    user_id, access_token, err = get_current_user()
    if err:
        return err

    res = supabase.table("recipes").select("author_id").eq("id", recipe_id).execute()
    if not res.data:
        return jsonify({"error": "Recipe not found"}), 404
    if res.data[0]["author_id"] != user_id:
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json()
    schema = RecipeUpdateSchema()
    errors = schema.validate(data)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    validated_data = schema.load(data)

    try:
        client = get_authenticated_client(access_token)
        res = client.table("recipes").update(validated_data).eq("id", recipe_id).execute()

        if not res.data:
            return jsonify({"error": "Failed to update recipe"}), 500

        return jsonify({
            "data": res.data[0],
            "message": "Recipe updated successfully"
        }), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500


# ── DELETE /recipes/<recipe_id> ───────────────────────────────────────────────

@recipes_bp.route("/<int:recipe_id>", methods=["DELETE"])
def delete_recipe(recipe_id):
    """
    DELETE /recipes/<recipe_id>
    Delete a recipe and all its media (owner only).

    Auth Required: Yes

    Response (200):
    {
        "message": "Recipe deleted successfully"
    }

    Error Responses:
        401 - Not authenticated
        403 - Forbidden (not the owner)
        404 - Recipe not found
        500 - Database error
    """
    user_id, access_token, err = get_current_user()
    if err:
        return err

    res = supabase.table("recipes").select("author_id").eq("id", recipe_id).execute()
    if not res.data:
        return jsonify({"error": "Recipe not found"}), 404
    if res.data[0]["author_id"] != user_id:
        return jsonify({"error": "Forbidden"}), 403

    try:
        # Delete media from storage first before removing the recipe row
        media = supabase.table("recipe_media").select("storage_path").eq("recipe_id", recipe_id).execute()
        if media.data:
            paths = [m["storage_path"] for m in media.data]
            supabase.storage.from_("recipe-media").remove(paths)

        client = get_authenticated_client(access_token)
        client.table("recipes").delete().eq("id", recipe_id).execute()

        return jsonify({"message": "Recipe deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500


# ── POST /recipes/<recipe_id>/media ──────────────────────────────────────────

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/webm"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024   # 10 MB
MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100 MB


@recipes_bp.route("/<int:recipe_id>/media", methods=["POST"])
def upload_media(recipe_id):
    """
    POST /recipes/<recipe_id>/media
    Upload an image or video for a recipe (owner only).

    Auth Required: Yes

    Form Data:
        file:     image or video file (required)
        caption:  str (optional)
        position: int (optional, default 0)

    Allowed image types: jpeg, png, webp, gif (max 10MB)
    Allowed video types: mp4, quicktime, webm (max 100MB)

    Response (201):
    {
        "data": {recipe_media object},
        "message": "Media uploaded successfully"
    }

    Error Responses:
        400 - No file provided
        401 - Not authenticated
        403 - Forbidden (not the owner)
        404 - Recipe not found
        413 - File too large
        415 - Unsupported file type
        500 - Upload failed
    """
    user_id, access_token, err = get_current_user()
    if err:
        return err

    res = supabase.table("recipes").select("author_id").eq("id", recipe_id).execute()
    if not res.data:
        return jsonify({"error": "Recipe not found"}), 404
    if res.data[0]["author_id"] != user_id:
        return jsonify({"error": "Forbidden"}), 403

    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file provided"}), 400

    content_type = file.content_type

    if content_type not in ALLOWED_IMAGE_TYPES and content_type not in ALLOWED_VIDEO_TYPES:
        return jsonify({"error": "Unsupported file type"}), 415

    file_bytes = file.read()
    max_size   = MAX_VIDEO_SIZE if content_type in ALLOWED_VIDEO_TYPES else MAX_IMAGE_SIZE
    if len(file_bytes) > max_size:
        limit = "100MB" if content_type in ALLOWED_VIDEO_TYPES else "10MB"
        return jsonify({"error": f"File too large. Maximum size is {limit}"}), 413

    media_type   = "video" if content_type in ALLOWED_VIDEO_TYPES else "image"
    caption      = request.form.get("caption", None)
    position     = request.form.get("position", 0)
    storage_path = f"{user_id}/{recipe_id}/{file.filename}"

    try:
        supabase.storage.from_("recipe-media").upload(storage_path, file_bytes, {
            "content-type": content_type
        })

        public_url = supabase.storage.from_("recipe-media").get_public_url(storage_path)

        media_res = supabase.table("recipe_media").insert({
            "recipe_id":    recipe_id,
            "url":          public_url,
            "storage_path": storage_path,
            "media_type":   media_type,
            "caption":      caption,
            "position":     position
        }).execute()

        if not media_res.data:
            return jsonify({"error": "Failed to save media record"}), 500

        return jsonify({
            "data":    media_res.data[0],
            "message": "Media uploaded successfully"
        }), 201
    except Exception as e:
        return jsonify({"error": "Upload failed", "details": str(e)}), 500


# ── DELETE /recipes/<recipe_id>/media/<media_id> ──────────────────────────────

@recipes_bp.route("/<int:recipe_id>/media/<int:media_id>", methods=["DELETE"])
def delete_media(recipe_id, media_id):
    """
    DELETE /recipes/<recipe_id>/media/<media_id>
    Delete a specific media item from a recipe (owner only).

    Auth Required: Yes

    Response (200):
    {
        "message": "Media deleted successfully"
    }

    Error Responses:
        401 - Not authenticated
        403 - Forbidden (not the owner)
        404 - Recipe or media not found
        500 - Database error
    """
    user_id, access_token, err = get_current_user()
    if err:
        return err

    recipe = supabase.table("recipes").select("author_id").eq("id", recipe_id).execute()
    if not recipe.data:
        return jsonify({"error": "Recipe not found"}), 404
    if recipe.data[0]["author_id"] != user_id:
        return jsonify({"error": "Forbidden"}), 403

    media = supabase.table("recipe_media").select("*").eq("id", media_id).eq("recipe_id", recipe_id).execute()
    if not media.data:
        return jsonify({"error": "Media not found"}), 404

    try:
        supabase.storage.from_("recipe-media").remove([media.data[0]["storage_path"]])
        supabase.table("recipe_media").delete().eq("id", media_id).execute()

        return jsonify({"message": "Media deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500