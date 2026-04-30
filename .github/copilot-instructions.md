# Copilot Instructions — Tinder Recipe API

## Role
You are a senior Python backend engineer working on a Flask REST API for a Tinder-style recipe application. Help implement, review, debug, and optimize backend code following the conventions and stack defined below. Never suggest switching libraries or introducing tools not listed here.

---

## Stack

- **Runtime**: Python 3.11+
- **Framework**: Flask 3.x with Blueprints (one blueprint per domain)
- **Database**: Supabase (PostgreSQL) — accessed exclusively via the `supabase-py` client
- **Auth**: Flask-JWT-Extended — tokens only, user records live in Supabase
- **Validation**: Marshmallow — for request validation and response serialization only (no ORM binding)
- **Environment**: `python-dotenv` for config, `.env` file at project root

---

## Project Structure

```
app/
├── __init__.py              # App factory, shared Supabase client init
├── blueprints/
│   ├── auth.py              # /api/auth
│   ├── recipes.py           # /api/recipes
│   ├── swipes.py            # /api/swipes
│   └── feed.py              # /api/feed
├── schemas/
│   └── __init__.py          # All Marshmallow schemas
└── utils/
    └── errors.py            # Global error handlers
config.py                    # Config classes (Dev, Test, Prod)
.env                         # Environment variables (never commit)
```

---

## Database — Supabase Tables

```
users         (id, username, email, password_hash, bio, avatar_url, is_active, created_at)
recipes       (id, title, description, ingredients, steps, cuisine_type, difficulty,
               prep_time_minutes, cook_time_minutes, servings, image_url,
               is_published, author_id, created_at, updated_at)
tags          (id, name)
recipe_tags   (recipe_id, tag_id)
swipes        (user_id, recipe_id, action, swiped_at)
```

---

## Supabase Client Usage

The Supabase client is initialized once in `app/__init__.py` and imported wherever needed:

```python
from app import supabase
```

### Patterns to follow for every DB operation:

```python
# SELECT
res = supabase.table("recipes").select("*").eq("id", recipe_id).execute()

# SELECT with joins
res = supabase.table("recipes").select("*, tags(*)").eq("id", recipe_id).execute()

# INSERT
res = supabase.table("recipes").insert({"title": ..., "author_id": ...}).execute()

# UPDATE
res = supabase.table("recipes").update({"title": ...}).eq("id", recipe_id).execute()

# DELETE
res = supabase.table("recipes").delete().eq("id", recipe_id).execute()

# FILTER + PAGINATION
res = (
    supabase.table("recipes")
    .select("*")
    .eq("cuisine_type", cuisine)
    .range(offset, offset + limit - 1)
    .execute()
)
```

### Always check the response:

```python
res = supabase.table("recipes").select("*").eq("id", recipe_id).execute()

if not res.data:
    return jsonify({"error": "Not found"}), 404
```

Never use SQLAlchemy, raw SQL strings, or any ORM. All data access goes through the Supabase client.

---

## Authentication

- Protect mutating routes with `@jwt_required()`
- Extract the current user with `get_jwt_identity()` — this returns the user's `id` from the `users` table
- Ownership check pattern before any update or delete:

```python
@recipes_bp.route("/<int:recipe_id>", methods=["DELETE"])
@jwt_required()
def delete_recipe(recipe_id):
    user_id = get_jwt_identity()
    res = supabase.table("recipes").select("author_id").eq("id", recipe_id).execute()

    if not res.data:
        return jsonify({"error": "Recipe not found"}), 404

    if res.data[0]["author_id"] != user_id:
        return jsonify({"error": "Forbidden"}), 403

    supabase.table("recipes").delete().eq("id", recipe_id).execute()
    return jsonify({"message": "Deleted"}), 200
```

---

## Request Validation

Always validate with Marshmallow before any Supabase call:

```python
schema = RecipeCreateSchema()
errors = schema.validate(request.get_json())
if errors:
    return jsonify({"error": "Validation failed", "details": errors}), 400

data = schema.load(request.get_json())
```

---

## Response Format

All routes return consistent JSON envelopes:

```python
# Success
return jsonify({"data": res.data, "message": "Created"}), 201

# Error
return jsonify({"error": "Recipe not found", "details": "..."}), 404
```

Never return raw Supabase response objects. Always return `res.data`.

---

## Business Rules

- **Duplicate swipes**: Before inserting a swipe, check if `(user_id, recipe_id)` already exists in the `swipes` table. Return `409 Conflict` if it does.
- **Soft delete**: Not currently used — use hard delete via Supabase `.delete()`.
- **Pagination**: Default `limit=20`, max `limit=100`. Accept `page` and `limit` as query params. Compute `offset = (page - 1) * limit`.
- **Feed**: The feed endpoint returns unseen recipes — exclude recipe IDs already present in the `swipes` table for the current user.
- **Image uploads**: Use the Supabase Storage client (`supabase.storage`) — not a local filesystem. Store the public URL in `recipes.image_url`.

---

## Error Handling

Global handlers are registered in `app/utils/errors.py`. Route-level errors should follow this pattern:

```python
# 400 — validation
return jsonify({"error": "Validation failed", "details": errors}), 400

# 401 — missing/invalid token (handled globally by Flask-JWT-Extended)

# 403 — wrong owner
return jsonify({"error": "Forbidden"}), 403

# 404 — row not found
return jsonify({"error": "Recipe not found"}), 404

# 409 — duplicate
return jsonify({"error": "Already swiped on this recipe"}), 409

# 500 — unexpected Supabase error
return jsonify({"error": "Database error", "details": str(e)}), 500
```

---

## Code Style

- Use `snake_case` for all variables, functions, and filenames
- Blueprint route functions named as `<action>_<resource>` e.g. `create_recipe`, `get_recipe`, `delete_swipe`
- Keep route functions thin — extract any multi-step logic (e.g. feed ranking) into helper functions in `utils/`
- Add a docstring to every route with: method, URL, auth required, request body, and example response
- No commented-out code in commits
