# Recipes API (Mobile)

All endpoints are mounted under:

- `{{API_BASE_URL}}/api/recipes/...`

Authentication (mobile):

- `Authorization: Bearer <access_token>`

---

## Endpoint summary

| Method | Path                            | Description                           | Auth         |
| ------ | ------------------------------- | ------------------------------------- | ------------ |
| GET    | `/`                             | Get all published recipes             | No           |
| POST   | `/create`                       | Create recipe (owner)                 | Yes (Bearer) |
| GET    | `/get_all`                      | Get all recipes + media               | No           |
| GET    | `/<recipe_id>`                  | Get recipe by id + media              | No           |
| PUT    | `/update/<recipe_id>`           | Update recipe (owner)                 | Yes (Bearer) |
| DELETE | `/<recipe_id>`                  | Delete recipe + media (owner)         | Yes (Bearer) |
| POST   | `/<recipe_id>/media`            | Upload image/video for recipe (owner) | Yes (Bearer) |
| DELETE | `/<recipe_id>/media/<media_id>` | Delete media (owner)                  | Yes (Bearer) |

---

## Common error responses

Typical shapes:

```json
{ "error": "Validation failed", "details": { ... } }
```

```json
{ "error": "Forbidden" }
```

```json
{ "error": "Database error", "details": "..." }
```

---

## GET `/recipes/`

### Purpose

Get all recipes where `is_published = true`.

### Responses

- `200` `{ "data": [ ... ], "message": "Recipes retrieved successfully" }`
- `500` `{ "error": "Database error", "details": "..." }`

---

## POST `/recipes/create`

### Purpose

Create a recipe for the authenticated user.

### Headers

- `Content-Type: application/json`
- `Authorization: Bearer <access_token>`

### Request body

Validated by `RecipeCreateSchema`:

```json
{
  "title": "string (required)",
  "description": "string (required)",
  "ingredients": ["string"],
  "steps": ["string"],
  "cuisine_type": "string (required)",
  "difficulty": "easy | medium | hard",
  "prep_time_minutes": 0,
  "cook_time_minutes": 0,
  "servings": 1,
  "is_published": false
}
```

### Responses

- `201` `{ "data": { ... }, "message": "Recipe created successfully" }`
- `400` `{ "error": "Validation failed", "details": { ... } }`
- `401` `{ "error": "Not authenticated" }` or invalid token variants
- `500` `{ "error": "Database error", "details": "..." }`

---

## GET `/recipes/get_all`

### Purpose

Get all recipes with nested `recipe_media(*)`.

### Responses

- `200` `{ "data": [ ... ], "message": "Recipes retrieved successfully" }`
- `500` `{ "error": "Database error", "details": "..." }`

---

## GET `/recipes/<recipe_id>`

### Purpose

Get one recipe by id with nested `recipe_media(*)`.

### URL param

- `recipe_id` (int)

### Responses

- `200` `{ "data": { ... }, "message": "Recipe retrieved successfully" }`
- `404` `{ "error": "Recipe not found" }`
- `500` `{ "error": "Database error", "details": "..." }`

---

## PUT `/recipes/update/<recipe_id>`

### Purpose

Update a recipe if the authenticated user is the author.

### Headers

- `Content-Type: application/json`
- `Authorization: Bearer <access_token>`

### Request body

Validated by `RecipeUpdateSchema` (fields optional but validated when provided):

```json
{
  "title": "string",
  "description": "string",
  "ingredients": ["string"],
  "steps": ["string"],
  "cuisine_type": "string",
  "difficulty": "easy | medium | hard",
  "prep_time_minutes": 0,
  "cook_time_minutes": 0,
  "servings": 1,
  "is_published": true
}
```

### Responses

- `200` `{ "data": { ... }, "message": "Recipe updated successfully" }`
- `401` not authenticated / invalid token
- `403` `{ "error": "Forbidden" }`
- `404` `{ "error": "Recipe not found" }`
- `400` validation failure
- `500` database error

---

## DELETE `/recipes/<recipe_id>`

### Purpose

Delete a recipe (owner only). Also deletes associated media objects.

### Headers

- `Authorization: Bearer <access_token>`

### Responses

- `200` `{ "message": "Recipe deleted successfully" }`
- `401` not authenticated / invalid token
- `403` `{ "error": "Forbidden" }`
- `404` `{ "error": "Recipe not found" }`
- `500` database error

---

## POST `/recipes/<recipe_id>/media`

### Purpose

Upload an image or video file for a recipe (owner only). Saves record in `recipe_media`.

### Headers

- `Authorization: Bearer <access_token>`
- `Content-Type: multipart/form-data`

### Form-data

- `file` (required)
- `caption` (optional)
- `position` (optional, default `0`)

### Constraints

- Image types: `image/jpeg`, `image/png`, `image/webp`, `image/gif` (max `10MB`)
- Video types: `video/mp4`, `video/quicktime`, `video/webm` (max `100MB`)

### Responses

- `201` `{ "data": { ... }, "message": "Media uploaded successfully" }`
- `400` `{ "error": "No file provided" }`
- `401` not authenticated / invalid token
- `403` `{ "error": "Forbidden" }`
- `404` `{ "error": "Recipe not found" }`
- `413` file too large
- `415` unsupported file type
- `500` upload failure

---

## DELETE `/recipes/<recipe_id>/media/<media_id>`

### Purpose

Delete a specific media item (owner only).

### Headers

- `Authorization: Bearer <access_token>`

### Responses

- `200` `{ "message": "Media deleted successfully" }`
- `401` not authenticated / invalid token
- `403` `{ "error": "Forbidden" }`
- `404` recipe/media not found
- `500` database error

---

## Axios (mobile) examples

```ts
export async function getPublishedRecipes() {
  const res = await api.get("/api/recipes/");
  return res.data;
}

export async function getRecipe(recipeId: number) {
  const res = await api.get(`/api/recipes/${recipeId}`);
  return res.data;
}

export async function updateRecipe(
  accessToken: string,
  recipeId: number,
  payload: {
    title?: string;
    description?: string;
    ingredients?: string[];
    steps?: string[];
    cuisine_type?: string;
    difficulty?: "easy" | "medium" | "hard";
    prep_time_minutes?: number;
    cook_time_minutes?: number;
    servings?: number;
    is_published?: boolean;
  },
) {
  const res = await api.put(`/api/recipes/update/${recipeId}`, payload, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return res.data;
}

export async function deleteRecipe(accessToken: string, recipeId: number) {
  const res = await api.delete(`/api/recipes/${recipeId}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return res.data;
}
```

### Create recipe

```ts
export async function createRecipe(accessToken: string, payload: any) {
  const res = await api.post("/api/recipes/create", payload, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return res.data;
}
```

### Upload media (multipart)

```ts
export async function uploadRecipeMedia(
  accessToken: string,
  recipeId: number,
  file: { uri: string; name: string; type: string },
) {
  const form = new FormData();
  form.append("file", file as any);

  const res = await api.post(`/api/recipes/${recipeId}/media`, form, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "multipart/form-data",
    },
  });

  return res.data;
}
```
