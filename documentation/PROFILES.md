# Profiles API (Mobile)

All endpoints are mounted under:

- `{{API_BASE_URL}}/api/profiles/...`

Authentication (mobile):

- `Authorization: Bearer <access_token>`

---

## Endpoint summary

| Method | Path         | Description                                | Auth         |
| ------ | ------------ | ------------------------------------------ | ------------ |
| GET    | `/`          | List all profiles                          | No           |
| GET    | `/<user_id>` | Get profile by user id                     | No           |
| GET    | `/me`        | Get current user profile                   | Yes (Bearer) |
| PUT    | `/me`        | Update current user profile                | Yes (Bearer) |
| POST   | `/me/avatar` | Upload avatar file and update `avatar_url` | Yes (Bearer) |

---

## Common error responses

- `400`/`401`/`403`/`404`/`500`

Typical shapes:

```json
{ "error": "Database error", "details": "..." }
```

```json
{ "error": "Validation failed", "details": { ... } }
```

---

## GET `/profiles/`

### Purpose

Get all profiles.

### Responses

- `200` `{ "data": [ ... ], "message": "Profiles retrieved successfully" }`
- `500` `{ "error": "Database error", "details": "..." }`

---

## GET `/profiles/<user_id>`

### Purpose

Get a single profile by Supabase user id.

### URL param

- `user_id` (string)

### Responses

- `200` `{ "data": { ... }, "message": "Profile retrieved successfully" }`
- `404` `{ "error": "Profile not found" }`
- `500` `{ "error": "Database error", "details": "..." }`

---

## GET `/profiles/me`

### Auth

- Requires `Authorization: Bearer <access_token>`

### Responses

- `200` `{ "data": { ... }, "message": "Profile retrieved successfully" }`
- `401` `{ "error": "Not authenticated" }` OR `{ "error": "Invalid or expired token", "details": "..." }`
- `404` `{ "error": "Profile not found" }`
- `500` `{ "error": "Database error", "details": "..." }`

---

## PUT `/profiles/me`

### Purpose

Update profile fields.

### Headers

- `Content-Type: application/json`
- `Authorization: Bearer <access_token>`

### Request body

Validated by `ProfileUpdateSchema`:

```json
{
  "name": "string (min 1, max 100)",
  "avatar_url": "string URL"
}
```

### Responses

- `200` `{ "data": { ... }, "message": "Profile updated successfully" }`
- `400` `{ "error": "Validation failed", "details": { ... } }`
- `401` `{ "error": "Not authenticated" }` / invalid token variants
- `500` `{ "error": "Database error", "details": "..." }`

---

## POST `/profiles/me/avatar`

### Purpose

Upload an avatar file (owner only via token), store it in Supabase Storage `avatars/` and update `profiles.avatar_url`.

### Headers

- `Authorization: Bearer <access_token>`
- `Content-Type: multipart/form-data`

### Form-data

- `file` (required): image file

The server enforces:

- Allowed types: `image/jpeg`, `image/png`, `image/webp`, `image/gif`
- Max size: `5MB`

### Responses

- `200` `{ "data": { "avatar_url": "https://..." }, "message": "Avatar uploaded successfully" }`
- `400` `{ "error": "No file provided" }`
- `401` not authenticated / invalid token
- `413` `{ "error": "File too large. Maximum size is 5MB" }`
- `415` `{ "error": "Unsupported file type" }`
- `500` `{ "error": "Upload failed", "details": "..." }`

---

## Axios (mobile) examples

### GET profile me

```ts
import { api } from "./api";

export async function getMyProfile(accessToken: string) {
  const res = await api.get("/api/profiles/me", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return res.data;
}
```

### Update profile

```ts
export async function updateMyProfile(
  accessToken: string,
  payload: { name: string; avatar_url?: string },
) {
  const res = await api.put("/api/profiles/me", payload, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return res.data;
}
```

### Upload avatar (multipart)

```ts
import { api } from "./api";
import { FormData } from "react-native";

export async function uploadAvatar(
  accessToken: string,
  file: { uri: string; name: string; type: string },
) {
  const form = new FormData();

  // RN FormData expects { uri, name, type }
  form.append("file", {
    uri: file.uri,
    name: file.name,
    type: file.type,
  } as any);

  const res = await api.post("/api/profiles/me/avatar", form, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "multipart/form-data",
    },
  });

  return res.data;
}
```

## PATCH `/profiles/deactivate` _(new)_

### Purpose

Deactivates the authenticated user's account. Sets `is_active = false`, immediately revokes the Supabase bearer token, and clears the server-side session in one sequence. The account is blocked from logging in again until manually restored.

### Headers

- `Authorization: Bearer <access_token>`

### Request body

- None

### Responses

- `200` `{ "message": "Account deactivated successfully" }`
- `401` not authenticated / invalid token
- `404` `{ "error": "Profile not found" }`
- `500` `{ "error": "Database error", "details": "..." }`

### Behavior notes

Runs in this exact order:

1. Sets `is_active = false` on the `profiles` table
2. Calls `sign_out()` on the authenticated Supabase client — bearer token invalidated server-side
3. Calls `session.clear()` — server-side session cookie wiped

After this call, discard the stored `access_token` and `refresh_token` on the client and redirect to login.

### Axios example

```ts
export async function deactivateAccount(accessToken: string) {
  const res = await api.patch("/api/profiles/deactivate", null, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return res.data;
}
```
