# Recipes API

## Overview

The recipes module handles all recipe CRUD operations, media uploads, and public recipe discovery.

**Base URL:** `/recipes`

**Registered in:** `routes/__init__.py`

```python
app.register_blueprint(recipes_bp, url_prefix="/recipes")
```

---

## Recipe Schema

### Fields

| Field               | Type     | Required | Description                                                |
| ------------------- | -------- | -------- | ---------------------------------------------------------- |
| `title`             | string   | ✅       | Recipe name (1–255 chars)                                  |
| `description`       | string   | ✅       | Short description (min 1 char)                             |
| `ingredients`       | string[] | ✅       | Non-empty list of ingredients                              |
| `steps`             | string[] | ✅       | Cooking steps in order                                     |
| `cuisine_type`      | string   | ✅       | e.g. `"Filipino"`, `"Italian"`, `"Japanese"` (1–100 chars) |
| `cook_time_minutes` | int      | ✅       | Cook time in minutes (>= 0)                                |
| `servings`          | int      | ✅       | Number of servings (>= 1)                                  |
| `is_published`      | bool     | ❌       | Whether recipe is publicly visible (default: `false`)      |
| `favorites_count`   | int      | ❌       | Read-only — managed by DB, never sent by client            |

> `favorites_count` is `dump_only` — it is returned in responses but ignored on create/update.

---

## Endpoints

---

### GET `/recipes/`

Get all published recipes. No authentication required.

**Response `200`:**

```json
{
  "data": [
    {
      "id": 1,
      "title": "Chicken Adobo",
      "description": "A classic Filipino braised chicken dish",
      "ingredients": ["500g chicken", "1/2 cup soy sauce"],
      "steps": ["Marinate chicken", "Brown chicken", "Simmer for 30 mins"],
      "cuisine_type": "Filipino",
      "cook_time_minutes": 30,
      "servings": 4,
      "is_published": true,
      "favorites_count": 12,
      "author_id": "uuid",
      "created_at": "2026-05-12T..."
    }
  ],
  "message": "Recipes retrieved successfully"
}
```

**Error responses:**
| Status | Meaning |
|---|---|
| `500` | Database error |

---

### GET `/recipes/get_all`

Get all recipes including unpublished ones, with their media. No authentication required.

> ⚠️ Consider restricting this to admin only before going to production.

**Response `200`:**

```json
{
  "data": [
    {
      "id": 1,
      "title": "Chicken Adobo",
      "recipe_media": [
        {
          "id": 1,
          "url": "https://...",
          "media_type": "image",
          "caption": "Finished dish",
          "position": 0
        }
      ]
    }
  ],
  "message": "Recipes retrieved successfully"
}
```

**Error responses:**
| Status | Meaning |
|---|---|
| `500` | Database error |

---

### GET `/recipes/<recipe_id>`

Get a single recipe by ID, including its media.

**URL parameter:**
| Param | Type | Description |
|---|---|---|
| `recipe_id` | int | ID of the recipe |

**Response `200`:**

```json
{
  "data": {
    "id": 1,
    "title": "Chicken Adobo",
    "description": "A classic Filipino braised chicken dish",
    "ingredients": ["500g chicken", "1/2 cup soy sauce"],
    "steps": ["Marinate chicken", "Brown chicken", "Simmer for 30 mins"],
    "cuisine_type": "Filipino",
    "cook_time_minutes": 30,
    "servings": 4,
    "is_published": true,
    "favorites_count": 12,
    "author_id": "uuid",
    "recipe_media": []
  },
  "message": "Recipe retrieved successfully"
}
```

**Error responses:**
| Status | Meaning |
|---|---|
| `404` | Recipe not found |
| `500` | Database error |

---

### POST `/recipes/create`

Create a new recipe for the authenticated user.

**Auth Required:** Yes

**Request body:**

```json
{
  "title": "Chicken Adobo",
  "description": "A classic Filipino braised chicken dish slow-cooked in soy sauce and vinegar.",
  "ingredients": [
    "500g chicken thighs",
    "1/2 cup soy sauce",
    "1/2 cup white vinegar",
    "5 cloves garlic, crushed",
    "2 bay leaves",
    "1 tsp black peppercorns"
  ],
  "steps": [
    "Marinate chicken in soy sauce, vinegar, garlic, bay leaves and peppercorns for 30 minutes",
    "Brown the chicken on both sides for about 5 minutes",
    "Pour in the marinade and bring to a boil",
    "Lower heat and simmer for 30 minutes until chicken is tender",
    "Serve over steamed rice"
  ],
  "cuisine_type": "Filipino",
  "cook_time_minutes": 40,
  "servings": 4,
  "is_published": true
}
```

**Response `201`:**

```json
{
  "data": {
    "id": 1,
    "title": "Chicken Adobo",
    "author_id": "your-user-uuid",
    "cuisine_type": "Filipino",
    "cook_time_minutes": 40,
    "servings": 4,
    "is_published": true,
    "favorites_count": 0,
    "created_at": "2026-05-12T..."
  },
  "message": "Recipe created successfully"
}
```

**Error responses:**
| Status | Meaning |
|---|---|
| `400` | Validation failed — check `details` for which fields failed |
| `401` | Not authenticated |
| `500` | Database error |

---

### PUT `/recipes/update/<recipe_id>`

Update a recipe. Only the owner can update. Send only the fields you want to change.

**Auth Required:** Yes (owner only)

**URL parameter:**
| Param | Type | Description |
|---|---|---|
| `recipe_id` | int | ID of the recipe to update |

**Request body** (all fields optional):

```json
{
  "title": "Updated Title",
  "description": "Updated description",
  "ingredients": ["new ingredient 1", "new ingredient 2"],
  "steps": ["new step 1", "new step 2"],
  "cuisine_type": "Japanese",
  "cook_time_minutes": 25,
  "servings": 2,
  "is_published": false
}
```

**Response `200`:**

```json
{
  "data": { "updated recipe object" },
  "message": "Recipe updated successfully"
}
```

**Error responses:**
| Status | Meaning |
|---|---|
| `400` | Validation failed |
| `401` | Not authenticated |
| `403` | Forbidden — not the recipe owner |
| `404` | Recipe not found |
| `500` | Database error |

---

### DELETE `/recipes/<recipe_id>` _(updated)_

> No longer hard-deletes the row or removes storage files. Now a soft delete.

### Purpose

Archives a recipe owned by the authenticated user. Inserts a record into the `archives` table and sets `active = false` on the recipe — excluding it from all feeds and recommendations immediately. Media files in storage are preserved.

### URL param

- `recipe_id` (int)

### Headers

- `Authorization: Bearer <access_token>`

### Request body

- None

### Responses

- `200` `{ "message": "Recipe archived successfully" }`
- `401` not authenticated / invalid token
- `403` `{ "error": "Forbidden" }` — not the recipe owner
- `404` `{ "error": "Recipe not found" }`
- `500` `{ "error": "Database error", "details": "..." }`

### Behavior notes

Runs in this order:

1. Inserts into `archives` — stores `recipe_id`, `author_id`, `archived_at` (auto-timestamped)
2. Sets `active = false` on the recipe row
3. Storage files in `recipe-media` are left untouched

### Axios example

```ts
export async function archiveRecipe(accessToken: string, recipeId: number) {
  const res = await api.delete(`/api/recipes/${recipeId}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return res.data;
}
```

---

### DELETE `/recipes/<recipe_id>`

Delete a recipe and all its associated media. Only the owner can delete.

**Auth Required:** Yes (owner only)

**URL parameter:**
| Param | Type | Description |
|---|---|---|
| `recipe_id` | int | ID of the recipe to delete |

**Response `200`:**

```json
{
  "message": "Recipe deleted successfully"
}
```

**Error responses:**
| Status | Meaning |
|---|---|
| `401` | Not authenticated |
| `403` | Forbidden — not the recipe owner |
| `404` | Recipe not found |
| `500` | Database error |

> Media files are deleted from Supabase Storage before the recipe row is removed.

---

### POST `/recipes/<recipe_id>/media`

Upload an image or video for a recipe. Only the owner can upload media.

**Auth Required:** Yes (owner only)

**Form data** (multipart/form-data):
| Field | Type | Required | Description |
|---|---|---|---|
| `file` | file | ✅ | Image or video file |
| `caption` | string | ❌ | Optional caption |
| `position` | int | ❌ | Display order (default `0`) |

**Allowed file types:**

| Type  | Formats              | Max Size |
| ----- | -------------------- | -------- |
| Image | jpeg, png, webp, gif | 10 MB    |
| Video | mp4, quicktime, webm | 100 MB   |

**Response `201`:**

```json
{
  "data": {
    "id": 1,
    "recipe_id": 1,
    "url": "https://your-supabase-url/storage/...",
    "storage_path": "user-uuid/recipe-id/filename.jpg",
    "media_type": "image",
    "caption": "Finished dish",
    "position": 0
  },
  "message": "Media uploaded successfully"
}
```

**Error responses:**
| Status | Meaning |
|---|---|
| `400` | No file provided |
| `401` | Not authenticated |
| `403` | Forbidden — not the recipe owner |
| `404` | Recipe not found |
| `413` | File too large |
| `415` | Unsupported file type |
| `500` | Upload failed |

---

### DELETE `/recipes/<recipe_id>/media/<media_id>`

Delete a specific media item from a recipe. Only the owner can delete media.

**Auth Required:** Yes (owner only)

**URL parameters:**
| Param | Type | Description |
|---|---|---|
| `recipe_id` | int | ID of the recipe |
| `media_id` | int | ID of the media item to delete |

**Response `200`:**

```json
{
  "message": "Media deleted successfully"
}
```

**Error responses:**
| Status | Meaning |
|---|---|
| `401` | Not authenticated |
| `403` | Forbidden — not the recipe owner |
| `404` | Recipe or media not found |
| `500` | Database error |

---

## Endpoint Summary

| Method   | Endpoint                         | Auth     | Description                   |
| -------- | -------------------------------- | -------- | ----------------------------- |
| `GET`    | `/recipes/`                      | ❌       | Get all published recipes     |
| `GET`    | `/recipes/get_all`               | ❌       | Get all recipes with media    |
| `GET`    | `/recipes/<id>`                  | ❌       | Get single recipe with media  |
| `POST`   | `/recipes/create`                | ✅       | Create a new recipe           |
| `PUT`    | `/recipes/update/<id>`           | ✅ Owner | Update a recipe               |
| `DELETE` | `/recipes/<id>`                  | ✅ Owner | Delete a recipe and its media |
| `POST`   | `/recipes/<id>/media`            | ✅ Owner | Upload image or video         |
| `DELETE` | `/recipes/<id>/media/<media_id>` | ✅ Owner | Delete a media item           |

---

## Production Checklist

- [ ] Restrict `GET /recipes/get_all` to admin only
- [ ] Add pagination to `GET /recipes/` for large datasets
- [ ] Consider adding search/filter by `cuisine_type` or `cook_time_minutes`
- [ ] Set up Supabase Storage bucket policies to restrict direct file access
