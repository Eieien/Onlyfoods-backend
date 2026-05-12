from flask import Blueprint, request, jsonify
from supabase_client import supabase, get_authenticated_client
from .auth import get_current_user

favorites_bp = Blueprint("favorites", __name__)


@favorites_bp.route("/<int:recipe_id>/save", methods=["POST"])
def save_recipe(recipe_id):
    user_id, access_token, err = get_current_user()
    if err:
        return err

    recipe = supabase.table("recipes").select("id, favorites_count").eq("id", recipe_id).execute()
    if not recipe.data:
        return jsonify({"error": "Recipe not found"}), 404

    existing = (
        supabase.table("saved_recipes")
        .select("*")
        .eq("user_id", user_id)
        .eq("recipe_id", recipe_id)
        .execute()
    )
    if existing.data:
        return jsonify({"error": "Recipe already saved"}), 409

    try:
        client = get_authenticated_client(access_token)
        res = (
            client.table("saved_recipes")
            .insert({"user_id": user_id, "recipe_id": recipe_id})
            .execute()
        )
        if not res.data:
            return jsonify({"error": "Failed to save recipe"}), 500
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500

    # Manually increment favorites_count
    try:
        current_count = recipe.data[0]["favorites_count"] or 0
        supabase.table("recipes").update(
            {"favorites_count": current_count + 1}
        ).eq("id", recipe_id).execute()
    except Exception:
        pass  # Don't fail the request if count update fails

    return jsonify({
        "data": res.data[0],
        "message": "Recipe saved successfully"
    }), 201


@favorites_bp.route("/<int:recipe_id>/save", methods=["DELETE"])
def unsave_recipe(recipe_id):
    user_id, access_token, err = get_current_user()
    if err:
        return err

    existing = (
        supabase.table("saved_recipes")
        .select("*")
        .eq("user_id", user_id)
        .eq("recipe_id", recipe_id)
        .execute()
    )
    if not existing.data:
        return jsonify({"error": "Recipe not in saved list"}), 404

    try:
        client = get_authenticated_client(access_token)
        client.table("saved_recipes").delete().eq("user_id", user_id).eq("recipe_id", recipe_id).execute()
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500

    # Manually decrement favorites_count, floor at 0
    try:
        recipe = supabase.table("recipes").select("favorites_count").eq("id", recipe_id).execute()
        if recipe.data:
            current_count = recipe.data[0]["favorites_count"] or 0
            supabase.table("recipes").update(
                {"favorites_count": max(current_count - 1, 0)}
            ).eq("id", recipe_id).execute()
    except Exception:
        pass  # Don't fail the request if count update fails

    return jsonify({"message": "Recipe unsaved successfully"}), 200


@favorites_bp.route("/me/saved", methods=["GET"])
def get_saved_recipes():
    user_id, access_token, err = get_current_user()
    if err:
        return err

    try:
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(50, max(1, int(request.args.get("per_page", 10))))
    except ValueError:
        return jsonify({"error": "Invalid pagination parameters"}), 400

    offset = (page - 1) * per_page

    try:
        count_res = (
            supabase.table("saved_recipes")
            .select("*", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        total = count_res.count or 0
        total_pages = (total + per_page - 1) // per_page

        res = (
            supabase.table("saved_recipes")
            .select("saved_at, recipes(*)")
            .eq("user_id", user_id)
            .order("saved_at", desc=True)
            .range(offset, offset + per_page - 1)
            .execute()
        )

        return jsonify({
            "data": res.data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages
            },
            "message": "Saved recipes retrieved successfully"
        }), 200
    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500