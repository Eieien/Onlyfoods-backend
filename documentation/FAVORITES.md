# Favorites API (Mobile)

All endpoints are mounted under:

- `{{API_BASE_URL}}/favorites/...`

Auth (mobile):

- `Authorization: Bearer <access_token>`

---

## Endpoint summary

| Method | Path                | Description                       | Auth         |
| ------ | ------------------- | --------------------------------- | ------------ |
| POST   | `/<recipe_id>/save` | Save a recipe                     | Yes (Bearer) |
| DELETE | `/<recipe_id>/save` | Unsave a recipe                   | Yes (Bearer) |
| GET    | `/me/saved`         | Get saved recipes with pagination | Yes (Bearer) |

---

## Common error responses

- `404` `{ "error": "Recipe not found" }`
- `409` `{ "error": "Recipe already saved" }` or `{ "error": "Recipe not in saved list" }`
- `400` `{ "error": "Invalid pagination parameters" }`
- `401` not authenticated / invalid token variants
- `500` `{ "error": "Database error", "details": "..." }`

---

## POST `/favorites/<recipe_id>/save`

### Purpose

Save a recipe to the authenticated user’s saved list.

### URL param

- `recipe_id` (int)

### Headers

- `Authorization: Bearer <access_token>`

### Request body

- None

### Responses

- `201` `{ "data": { ... }, "message": "Recipe saved successfully" }`
- `404` `{ "error": "Recipe not found" }`
- `409` `{ "error": "Recipe already saved" }`
- `401` not authenticated / invalid token
- `500` `{ "error": "Database error", "details": "..." }`

---

## DELETE `/favorites/<recipe_id>/save`

### Purpose

Remove a recipe from the authenticated user’s saved list.

### URL param

- `recipe_id` (int)

### Headers

- `Authorization: Bearer <access_token>`

### Request body

- None

### Responses

- `200` `{ "message": "Recipe unsaved successfully" }`
- `404` `{ "error": "Recipe not in saved list" }`
- `401` not authenticated / invalid token
- `500` `{ "error": "Database error", "details": "..." }`

---

## GET `/favorites/me/saved`

### Purpose

Get the authenticated user’s saved recipes.

### Headers

- `Authorization: Bearer <access_token>`

### Query params

- `page` (int, default `1`)
- `per_page` (int, default `10`, clamped to max `50`)

### Responses

- `200`

```json
{
  "data": [ ... ],
  "pagination": {
    "page": 1,
    "per_page": 10,
    "total": 42,
    "total_pages": 5
  },
  "message": "Saved recipes retrieved successfully"
}
```

- `400` `{ "error": "Invalid pagination parameters" }`
- `401` not authenticated / invalid token
- `500` `{ "error": "Database error", "details": "..." }`

---

## Axios (mobile) examples

```ts
export async function getSavedRecipes(
  accessToken: string,
  page = 1,
  perPage = 10,
) {
  const res = await api.get("/favorites/me/saved", {
    headers: { Authorization: `Bearer ${accessToken}` },
    params: { page, per_page: perPage },
  });
  return res.data;
}

export async function saveRecipe(accessToken: string, recipeId: number) {
  const res = await api.post(`/favorites/${recipeId}/save`, null, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return res.data;
}

export async function unsaveRecipe(accessToken: string, recipeId: number) {
  const res = await api.delete(`/favorites/${recipeId}/save`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return res.data;
}
```
