# Auth API (Mobile)

All endpoints are mounted under:

- `{{API_BASE_URL}}/api/auth/...`

This backend supports **mobile-style auth** via:

- `Authorization: Bearer <access_token>`

It also uses a web session internally, but the docs below focus on the **Authorization header** flow.

---

## Common JSON error responses

Most endpoints return one of these shapes:

- `400`/`401`/`403`/`404`/`409`/`500`

Example:

```json
{
  "error": "Unauthorized"
}
```

Some endpoints include an additional field such as `details`.

---

## Endpoint summary

| Method | Path        | Description               | Auth         |
| ------ | ----------- | ------------------------- | ------------ |
| POST   | `/register` | Create a user             | No           |
| POST   | `/login`    | Sign in and return tokens | No           |
| POST   | `/logout`   | Sign out                  | No (session) |
| GET    | `/me`       | Get current user          | Yes (Bearer) |

---

## POST `/auth/register`

### Purpose

Register a new user in Supabase.

### Headers

- `Content-Type: application/json`

### Request body

```json
{
  "email": "string (required)",
  "password": "string (required, min 8 chars)",
  "username": "string (required)"
}
```

### Responses

- `201`

```json
{
  "message": "User registered successfully. Please check your email to confirm.",
  "user": {
    "id": "<uuid>",
    "email": "<email>"
  }
}
```

### Error responses

- `400` `{"error": "Already logged in, please logout first"}` (if already in session)
- `400` `{"error": "Email, password and username are required"}`
- `400` `{"error": "Password is too short"}`
- `409` `{"error": "Email already exists"}`
- `409` `{"error": "Registration failed"}`
- `409` `{"error": "<exception string>"}`

---

## POST `/auth/login`

### Purpose

Sign in with email/password and return tokens.

### Headers

- `Content-Type: application/json`

### Request body

```json
{
  "email": "string (required)",
  "password": "string (required)"
}
```

### Responses

- `200`

```json
{
  "message": "Login successful",
  "user": {
    "id": "<uuid>",
    "email": "<email>",
    "metadata": { "...": "..." }
  },
  "access_token": "<supabase access token>",
  "refresh_token": "<supabase refresh token>"
}
```

### Error responses

- `400` `{"error": "Already logged in, please logout first"}` (if already in session)
- `400` `{"error": "Email and password are required"}`
- `401` `{"error": "<exception string>"}`

---

## POST `/auth/logout`

### Purpose

Logout and clear the server session.

### Headers

- `Content-Type` not required.

### Responses

- `200`

```json
{ "message": "Logged out" }
```

### Error responses

- `400`

```json
{ "error": "User not logged in" }
```

---

## GET `/auth/me`

### Purpose

Get the currently authenticated user.

### Headers (mobile)

- `Authorization: Bearer <access_token>`

### Responses

- `200`

```json
{
  "user": {
    "id": "<uuid>",
    "email": "<email>",
    "metadata": { "...": "..." },
    "access_token": "<token>",
    "refresh_token": "<token>"
  },
  "message": "User data retrieved successfully"
}
```

### Error responses

- `401` `{"error": "Not authenticated"}`
- `401` `{"error": "Invalid or expired token", "details": "<...>"}` (when Authorization is present but invalid)

---

## Axios (mobile) examples

> Note: The backend uses **only `Authorization: Bearer ...`** for mobile auth.

```ts
import axios from "axios";

const apiBase = process.env.EXPO_PUBLIC_API_BASE_URL; // e.g. http://10.0.2.2:5000
const api = axios.create({ baseURL: apiBase });

export async function register(
  email: string,
  password: string,
  username: string,
) {
  const res = await api.post("/api/auth/register", {
    email,
    password,
    username,
  });
  return res.data;
}

export async function login(email: string, password: string) {
  const res = await api.post("/api/auth/login", { email, password });
  // res.data.access_token is what you use for Bearer auth
  return res.data;
}

export async function me(accessToken: string) {
  const res = await api.get("/api/auth/me", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return res.data;
}
```
