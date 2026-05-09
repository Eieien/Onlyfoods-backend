from flask import Blueprint, jsonify, request
from flask import session
from supabase_client import supabase, get_authenticated_client
from schemas import ProfileSchema, ProfileUpdateSchema
from .auth import get_current_user

profiles_bp = Blueprint("profiles", __name__)


@profiles_bp.route("/", methods=["GET"])
def get_all_profiles():
    """
    GET /api/profiles/
    Get all profiles (public).

    Response (200):
    {
        "data": [profile objects],
        "message": "Profiles retrieved successfully"
    }
    """
    try:
        res = supabase.table("profiles").select("*").execute()
        return jsonify({
            "data": res.data,
            "message": "Profiles retrieved successfully"
        }), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500


@profiles_bp.route("/<string:user_id>", methods=["GET"])
def get_profile(user_id):
    """
    GET /api/profiles/<user_id>
    Get a single profile by user ID (public).

    Response (200):
    {
        "data": {profile object},
        "message": "Profile retrieved successfully"
    }
    """
    try:
        res = supabase.table("profiles").select("*").eq("id", user_id).execute()
        if not res.data:
            return jsonify({"error": "Profile not found"}), 404

        return jsonify({
            "data": res.data[0],
            "message": "Profile retrieved successfully"
        }), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500


@profiles_bp.route("/me", methods=["GET"])
def get_my_profile():
    """
    GET /api/profiles/me
    Get the authenticated user's profile.

    Auth Required: Yes (session)

    Response (200):
    {
        "data": {profile object},
        "message": "Profile retrieved successfully"
    }
    """
    user_id, access_token, err = get_current_user()
    if err:
        return err

    try:
        client = get_authenticated_client(access_token)
        res = client.table("profiles").select("*").eq("id", user_id).execute()
        if not res.data:
            return jsonify({"error": "Profile not found"}), 404

        return jsonify({
            "data": res.data[0],
            "message": "Profile retrieved successfully"
        }), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500


@profiles_bp.route("/me", methods=["PUT"])
def update_my_profile():
    user_id, access_token, err = get_current_user()
    if err:
        return err

    data = request.get_json()

    schema = ProfileUpdateSchema()
    errors = schema.validate(data)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    validated_data = schema.load(data)

    try:
        client = get_authenticated_client(access_token)
        res = client.table("profiles").update(validated_data).eq("id", user_id).execute()
        if not res.data:
            return jsonify({"error": "Failed to update profile"}), 500

        return jsonify({
            "data": res.data[0],
            "message": "Profile updated successfully"
        }), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500


@profiles_bp.route("/me/avatar", methods=["POST"])
def upload_avatar():
    user_id, access_token, err = get_current_user()
    if err:
        return err

    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file provided"}), 400

    ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    MAX_SIZE = 5 * 1024 * 1024  # 5MB

    if file.content_type not in ALLOWED_TYPES:
        return jsonify({"error": "Unsupported file type"}), 415

    file_bytes = file.read()
    if len(file_bytes) > MAX_SIZE:
        return jsonify({"error": "File too large. Maximum size is 5MB"}), 413

    storage_path = f"avatars/{user_id}/{file.filename}"

    try:
        client = get_authenticated_client(access_token)

        # Upload to Supabase Storage
        client.storage.from_("avatars").upload(storage_path, file_bytes, {
            "content-type": file.content_type
        })

        avatar_url = client.storage.from_("avatars").get_public_url(storage_path)

        # Update profile with new avatar URL
        res = client.table("profiles").update({"avatar_url": avatar_url}).eq("id", user_id).execute()
        if not res.data:
            return jsonify({"error": "Failed to update avatar"}), 500

        return jsonify({
            "data": {"avatar_url": avatar_url},
            "message": "Avatar uploaded successfully"
        }), 200
    except Exception as e:
        return jsonify({"error": "Upload failed", "details": str(e)}), 500