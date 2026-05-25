# Archives API (Mobile)

All endpoints are mounted under:

- `{{API_BASE_URL}}/api/archives/...`

Auth (mobile):

- `Authorization: Bearer <access_token>`

---

## Endpoint summary

| Method | Path            | Description                              | Auth         |
| ------ | --------------- | ---------------------------------------- | ------------ |
| GET    | `/`             | List all archived recipes for the user   | Yes (Bearer) |
| GET    | `/<archive_id>` | Get a single archive with recipe + media | Yes (Bearer) |

---

## Common error responses

- `401` not authenticated / invalid token
- `404` `{ "error": "Archive not found" }`
- `500` `{ "error": "Database error", "details": "..." }`

---

## GET `/archives/`

### Purpose

Returns a paginated list of the authenticated user's archived recipes, each enriched with the full recipe row and its media.

### Headers

- `Authorization: Bearer <access_token>`

### Query params

- `page` (int, default `1`)
- `per_page` (int, default `10`, clamped to max `50`)

### Responses

- `200`

```json
{
  "archives": [
    {
      "id": 1,
      "recipe_id": 42,
      "author_id": "uuid",
      "archived_at": "2024-01-01T00:00:00Z",
      "reason": null,
      "recipe": { "..." },
      "media": [ { "..." } ]
    }
  ],
  "page": 1,
  "per_page": 10,
  "total": 3
}
```

- `401` not authenticated / invalid token
- `500` `{ "error": "Database error", "details": "..." }`

---

## GET `/archives/<archive_id>`

### Purpose

Returns a single archive record belonging to the authenticated user, with the full recipe and all associated media.

### URL param

- `archive_id` (int)

### Headers

- `Authorization: Bearer <access_token>`

### Request body

- None

### Responses

- `200`

```json
{
  "id": 1,
  "recipe_id": 42,
  "author_id": "uuid",
  "archived_at": "2024-01-01T00:00:00Z",
  "reason": null,
  "recipe": { "..." },
  "media": [ { "..." } ]
}
```

- `401` not authenticated / invalid token
- `404` `{ "error": "Archive not found" }` — does not exist or does not belong to the user
- `500` `{ "error": "Database error", "details": "..." }`

### Behavior notes

- Ownership is enforced at both the RLS (Supabase) and application level
- A non-owner requesting another user's archive receives `404`, not `403` — avoids leaking that the record exists

### Axios examples

```ts
export async function getArchives(accessToken: string, page = 1, perPage = 10) {
  const res = await api.get("/api/archives/", {
    headers: { Authorization: `Bearer ${accessToken}` },
    params: { page, per_page: perPage },
  });
  return res.data;
}

export async function getArchive(accessToken: string, archiveId: number) {
  const res = await api.get(`/api/archives/${archiveId}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return res.data;
}
```
