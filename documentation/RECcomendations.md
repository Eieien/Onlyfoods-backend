# Recommendations API

## Overview

The recommendations module powers recipe discovery using a **PyTorch embedding model + KNN cosine similarity**. It learns from user swipe behavior over time and avoids showing the same recipes twice per user session.

**Base URL:** `/recommendations`

**Registered in:** `routes/__init__.py`

```python
app.register_blueprint(recommendations_bp, url_prefix="/recommendations")
```

---

## How It Works

```
User opens app
      ↓
Cold start → /filter (no history yet)
      ↓
User swipes → POST /swipe (records likes/dislikes)
      ↓
Personalized → POST /personalized (taste centroid via embeddings)
      ↓
Nightly      → POST /fine-tune (model learns from swipe triplets)
```

- **Seen tracking** — pass `user_id` to any recommend endpoint and the model automatically skips recipes already shown to that user.
- **Diversity** — results are partially shuffled so the same query never returns the exact same list twice.
- **Fine-tuning** — swipe triplets (anchor / liked / disliked) pull similar recipes closer and push disliked ones further apart in embedding space, then re-index the KNN immediately.

---

## Authentication

Auth is currently **disabled for testing**. Before going to production, uncomment the auth guards in:

- `POST /train` — restrict to admin only
- `POST /swipe` — replace manual `user_id` with `get_current_user()`

---

## Endpoints

---

### POST `/recommendations/train`

Trains the embedding model and KNN from scratch on a list of recipes. Must be called at least once before any other endpoint works. Saves the model to `recipe_recommender.pkl`.

> ⚠️ Admin only in production. Uncomment the auth guard before deploying.

**Request body:**

```json
{
  "recipes": [ <RecipeSchema>, ... ]
}
```

**Recipe schema** (all fields required):
| Field | Type | Description |
|---|---|---|
| `title` | string | Recipe name |
| `description` | string | Short description |
| `ingredients` | string[] | List of ingredients |
| `steps` | string[] | Cooking steps |
| `cuisine_type` | string | e.g. `"italian"`, `"thai"` |
| `cook_time_minutes` | int | Cook time in minutes |
| `servings` | int | Number of servings |
| `is_published` | bool | Only published recipes are trained on |
| `favorites_count` | int | Total saves — boosts ranking |

**Success response `200`:**

```json
{
  "status": "ok",
  "trained_on": 20
}
```

**Error responses:**
| Status | Meaning |
|---|---|
| `400` | `recipes` field missing from body |
| `500` | Training failed (check server logs) |

---

### POST `/recommendations/fine-tune`

Fine-tunes the existing model on swipe triplets without full retraining. Each triplet teaches the model to rank liked recipes closer to the anchor and disliked ones further away. Re-indexes the KNN immediately after training.

**Recommended trigger:** nightly cron job, or after every 50 swipes accumulate.

**Request body:**

```json
{
  "swipe_history": [
    {
      "anchor":   { <RecipeSchema> },
      "liked":    { <RecipeSchema> },
      "disliked": { <RecipeSchema> }
    }
  ],
  "epochs": 5
}
```

| Field           | Type  | Required | Default | Description             |
| --------------- | ----- | -------- | ------- | ----------------------- |
| `swipe_history` | array | ✅       | —       | Min 3 triplets required |
| `epochs`        | int   | ❌       | `5`     | Training iterations     |

**Success response `200`:**

```json
{
  "status": "ok",
  "fine_tuned_on": 5
}
```

**Error responses:**
| Status | Meaning |
|---|---|
| `400` | Fewer than 3 swipe triplets provided |
| `500` | Fine-tuning failed |

---

### POST `/recommendations/recommend`

Returns recipes similar to a given recipe. Skips recipes the user has already seen if `user_id` is provided. Results are partially shuffled for diversity so repeated calls return different results.

**Request body:**

```json
{
  "recipe":  { <RecipeSchema> },
  "n":       5,
  "user_id": "user_123"
}
```

| Field     | Type   | Required | Default | Description                         |
| --------- | ------ | -------- | ------- | ----------------------------------- |
| `recipe`  | object | ✅       | —       | The recipe to find similar ones for |
| `n`       | int    | ❌       | `5`     | Number of results to return         |
| `user_id` | string | ❌       | `null`  | Enables seen tracking across calls  |

**Success response `200`:**

```json
{
  "recommendations": [
    {
      "recipe": { <RecipeSchema> },
      "similarity": 0.87
    }
  ]
}
```

`similarity` is a float between `0` and `1` — higher means more similar.

**Error responses:**
| Status | Meaning |
|---|---|
| `400` | `recipe` field missing |
| `500` | Model error (may not be trained yet) |

---

### GET `/recommendations/filter`

Returns recipes matching the given filters, sorted by `favorites_count` descending. Used for cold-start when a new user has no swipe history. Skips seen recipes if `user_id` is passed.

**Query parameters:**
| Param | Type | Required | Description |
|---|---|---|---|
| `cuisine_type` | string | ❌ | Filter by cuisine e.g. `italian` |
| `max_cook_time` | int | ❌ | Max cook time in minutes |
| `n` | int | ❌ | Number of results (default `5`) |
| `user_id` | string | ❌ | Enables seen tracking |

**Example request:**

```
GET /recommendations/filter?cuisine_type=italian&max_cook_time=30&n=3&user_id=user_123
```

**Success response `200`:**

```json
{
  "recommendations": [
    {
      "recipe": { <RecipeSchema> },
      "similarity": null
    }
  ]
}
```

> `similarity` is `null` for filter results since no embedding comparison is done.

---

### GET `/recommendations/similar/<index>`

Returns recipes similar to the recipe at position `index` in the training data. Useful for a "More like this" button on a recipe detail page.

**URL parameter:**
| Param | Type | Description |
|---|---|---|
| `index` | int | Position of the recipe in the trained dataset (0-based) |

**Query parameters:**
| Param | Type | Required | Description |
|---|---|---|---|
| `n` | int | ❌ | Number of results (default `5`) |
| `user_id` | string | ❌ | Enables seen tracking |

**Example request:**

```
GET /recommendations/similar/0?n=4&user_id=user_123
```

**Success response `200`:**

```json
{
  "recommendations": [
    {
      "recipe": { <RecipeSchema> },
      "similarity": 0.91
    }
  ]
}
```

**Error responses:**
| Status | Meaning |
|---|---|
| `500` | Index out of range or model not trained |

### GET `/recommendations/by-ingredients` _(new)_

### Purpose

Returns a randomized feed of active recipes that contain **all** of the queried ingredients. Recipes may have additional ingredients beyond what was specified. Results are shuffled feed-style so repeat calls feel fresh.

### Headers

- `Authorization: Bearer <access_token>`

### Query params

- `ingredients` (string, required) — comma-separated list e.g. `chicken,basil`
- `n` (int, default `10`) — number of results
- `user_id` (string, optional) — enables seen tracking so already-shown recipes are skipped on repeat calls
- `diversity` (float, default `0.5`, range `0.0–1.0`) — controls how shuffled the feed is; higher = more random

### Responses

- `200`

```json
{
  "ingredients_queried": ["chicken", "basil"],
  "count": 6,
  "recommendations": [
    { "recipe": { "..." }, "similarity": null }
  ]
}
```

- `400` `{ "error": "At least one ingredient is required" }`
- `503` `{ "error": "Model not trained yet" }`
- `500` `{ "error": "..." }`

### Behavior notes

- All queried ingredients must be present in the recipe — it is a strict AND match, not OR
- Results are scored by ingredient overlap then shuffled based on the `diversity` value
- Inactive recipes (`active = false`) are excluded
- Pass `user_id` for seen tracking — same recipe will not appear again for that user until `reset-seen` is called

### Axios example

```ts
export async function getRecipesByIngredients(
  ingredients: string[],
  n = 10,
  userId?: string,
  diversity = 0.5,
) {
  const res = await api.get("/api/recommendations/by-ingredients", {
    params: {
      ingredients: ingredients.join(","),
      n,
      user_id: userId,
      diversity,
    },
  });
  return res.data;
}
```

---

### POST `/recommendations/swipe`

Records a like or dislike for a recipe. Stored in memory during development — move to a Supabase `swipes` table before production.

> 🔧 Replace `user_id` in the body with `get_current_user()` once auth is wired.

**Request body:**

```json
{
  "user_id":   "user_123",
  "recipe":    { <RecipeSchema> },
  "direction": "like"
}
```

| Field       | Type   | Required | Description                   |
| ----------- | ------ | -------- | ----------------------------- |
| `user_id`   | string | ✅       | The user performing the swipe |
| `recipe`    | object | ✅       | The recipe being swiped on    |
| `direction` | string | ✅       | `"like"` or `"dislike"`       |

**Success response `200`:**

```json
{
  "status": "recorded",
  "direction": "like"
}
```

**Error responses:**
| Status | Meaning |
|---|---|
| `400` | Missing `recipe` or invalid `direction` |

---

### POST `/recommendations/personalized`

Builds a taste profile by averaging the embedding vectors of liked recipes (centroid), then queries KNN for the nearest matches. Falls back to `/filter` if no liked recipes exist yet (cold start).

**Option A — pass recipes directly (good for testing):**

```json
{
  "liked_recipes":   [ <RecipeSchema>, ... ],
  "disliked_titles": [ "Chicken Ramen", "Guacamole" ],
  "n":               5,
  "user_id":         "user_123"
}
```

**Option B — look up from swipe store:**

```json
{
  "user_id": "user_123",
  "n": 5
}
```

| Field             | Type     | Required | Description                                  |
| ----------------- | -------- | -------- | -------------------------------------------- |
| `user_id`         | string   | ❌       | Reads swipe store + enables seen tracking    |
| `liked_recipes`   | array    | ❌       | Pass directly instead of reading swipe store |
| `disliked_titles` | string[] | ❌       | Titles to exclude from results               |
| `n`               | int      | ❌       | Number of results (default `5`)              |

**Success response `200`:**

```json
{
  "recommendations": [
    {
      "recipe": { <RecipeSchema> },
      "similarity": 0.84
    }
  ],
  "mode": "personalized"
}
```

`mode` is either `"personalized"` or `"cold_start"`.

**Error responses:**
| Status | Meaning |
|---|---|
| `503` | Model not trained yet — call `/train` first |
| `500` | Embedding or KNN error |

---

### POST `/recommendations/reset-seen`

Clears the seen recipe history for a user so they can receive fresh recommendations from scratch. Useful for testing or if the user explicitly wants to rediscover recipes.

**Request body:**

```json
{
  "user_id": "user_123"
}
```

**Success response `200`:**

```json
{
  "status": "ok",
  "message": "Seen history cleared for user_123"
}
```

**Error responses:**
| Status | Meaning |
|---|---|
| `400` | `user_id` missing from body |

---

## Endpoint Summary

| Method | Endpoint                           | Description                       |
| ------ | ---------------------------------- | --------------------------------- |
| `POST` | `/recommendations/train`           | Train model from scratch          |
| `POST` | `/recommendations/fine-tune`       | Fine-tune on swipe triplets       |
| `POST` | `/recommendations/recommend`       | Similar recipes to a given recipe |
| `GET`  | `/recommendations/filter`          | Filter by cuisine / cook time     |
| `GET`  | `/recommendations/similar/<index>` | Similar to recipe at index        |
| `POST` | `/recommendations/swipe`           | Record a like or dislike          |
| `POST` | `/recommendations/personalized`    | Personalized taste-based results  |
| `POST` | `/recommendations/reset-seen`      | Clear seen history for a user     |

---

## Production Checklist

- [ ] Uncomment admin auth guard in `POST /train`
- [ ] Uncomment `get_current_user()` in `POST /swipe` and remove manual `user_id`
- [ ] Replace in-memory `_swipe_store` with a Supabase `swipes` table
- [ ] Replace in-memory `_seen_store` (in `model.py`) with Redis or Supabase
- [ ] Set up a nightly cron job or APScheduler to call `POST /fine-tune`
- [ ] Retrain model after any bulk recipe import via `POST /train`
