from flask import Blueprint, jsonify, request
from utils.supabase import supabase, get_authenticated_client
from .auth import get_current_user

archives_bp = Blueprint("archives", __name__)


# ── GET /archives ─────────────────────────────────────────────────────────────

@archives_bp.route("/", methods=["GET"])
def get_archives():
    """
    GET /archives
    Returns all archives belonging to the current user.
    Auth Required: Yes

    Query params:
        page     - page number, default 1
        per_page - results per page, default 10, max 50

    Response (200):
    {
        "archives": [
            {
                "id": 1,
                "recipe_id": 42,
                "author_id": "uuid",
                "archived_at": "2024-01-01T00:00:00Z",
                "reason": null,
                "recipe": { ...full recipe row... },
                "media": [ ...recipe_media rows... ]
            }
        ],
        "page": 1,
        "per_page": 10,
        "total": 3
    }

    Error Responses:
        401 - Not authenticated
        500 - Database error
    """
    user_id, access_token, err = get_current_user()
    if err:
        return err

    page     = request.args.get("page", default=1, type=int)
    per_page = min(request.args.get("per_page", default=10, type=int), 50)
    offset   = (page - 1) * per_page

    try:
        client = get_authenticated_client(access_token)

        res = (
            client.table("archives")
            .select("*")
            .eq("author_id", user_id)
            .order("archived_at", desc=True)
            .range(offset, offset + per_page - 1)
            .execute()
        )

        archives = res.data or []

        enriched = []
        for archive in archives:
            recipe_id = archive["recipe_id"]

            recipe_res = client.table("recipes").select("*").eq("id", recipe_id).execute()
            media_res  = client.table("recipe_media").select("*").eq("recipe_id", recipe_id).execute()

            enriched.append({
                **archive,
                "recipe": recipe_res.data[0] if recipe_res.data else None,
                "media":  media_res.data or [],
            })

        return jsonify({
            "archives": enriched,
            "page":     page,
            "per_page": per_page,
            "total":    len(enriched),
        }), 200

    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500


# ── GET /archives/<archive_id> ────────────────────────────────────────────────

@archives_bp.route("/<int:archive_id>", methods=["GET"])
def get_archive(archive_id):
    """
    GET /archives/<archive_id>
    Returns a single archive with full recipe and media.
    Only accessible by the owner.
    Auth Required: Yes

    Response (200):
    {
        "id": 1,
        "recipe_id": 42,
        "author_id": "uuid",
        "archived_at": "2024-01-01T00:00:00Z",
        "reason": null,
        "recipe": { ...full recipe row... },
        "media": [ ...recipe_media rows... ]
    }

    Error Responses:
        401 - Not authenticated
        403 - Forbidden (not the owner)
        404 - Archive not found
        500 - Database error
    """
    user_id, access_token, err = get_current_user()
    if err:
        return err

    try:
        client = get_authenticated_client(access_token)

        res = (
            client.table("archives")
            .select("*")
            .eq("id", archive_id)
            .eq("author_id", user_id)   # RLS + app-level ownership in one query
            .execute()
        )

        if not res.data:
            return jsonify({"error": "Archive not found"}), 404

        archive   = res.data[0]
        recipe_id = archive["recipe_id"]

        recipe_res = client.table("recipes").select("*").eq("id", recipe_id).execute()
        media_res  = client.table("recipe_media").select("*").eq("recipe_id", recipe_id).execute()

        return jsonify({
            **archive,
            "recipe": recipe_res.data[0] if recipe_res.data else None,
            "media":  media_res.data or [],
        }), 200

    except Exception as e:
        return jsonify({"error": "Database error", "details": str(e)}), 500