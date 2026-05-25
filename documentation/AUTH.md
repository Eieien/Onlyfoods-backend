# Auth API

All endpoints are mounted under:

- `{{API_BASE_URL}}/auth/...`

Auth (mobile):

- `Authorization: Bearer <access_token>`

---

## Endpoint Summary

| Method | Path                      | Description                        | Auth         |
| ------ | ------------------------- | ---------------------------------- | ------------ |
| POST   | `/register`               | Register a new user                | No           |
| POST   | `/login`                  | Log in and receive tokens          | No           |
| POST   | `/logout`                 | Log out the current user           | Yes (Bearer) |
| POST   | `/refresh`                | Refresh access token               | Yes (Bearer) |
| POST   | `/reset-password`         | Request a password reset email     | No           |
| POST   | `/reset-password/confirm` | Set a new password via reset token | Yes (Bearer) |

---

## Common Error Responses

| Status | Body                                                              |
| ------ | ----------------------------------------------------------------- |
| `400`  | `{ "error": "..." }` — missing or invalid fields                  |
| `401`  | `{ "error": "..." }` — not authenticated or invalid/expired token |
| `500`  | `{ "error": "...", "details": "..." }` — server or database error |

---

## POST `/auth/register`

### Purpose

Register a new user account. Creates a Supabase auth user and a matching profile row.

### Request Body

```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

### Responses

- `201` `{ "data": { ... }, "message": "User registered successfully" }`
- `400` `{ "error": "Email and password are required" }`
- `409` `{ "error": "User already exists" }`
- `500` `{ "error": "Registration failed", "details": "..." }`

---

## POST `/auth/login` _(updated)_

> Now blocks login for deactivated accounts.

### Purpose

Authenticate a user with email and password. Returns a bearer token and refresh token. Rejects login if the account's `is_active` flag is `false`.

### Request body

```json
{
  "email": "user@example.com",
  "password": "yourpassword"
}
```

### Responses

- `200`

```json
{
  "message": "Login successful",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "metadata": {}
  },
  "access_token": "<token>",
  "refresh_token": "<token>"
}
```

- `400` `{ "error": "Email and password are required" }`
- `400` `{ "error": "Already logged in, please logout first" }`
- `403` `{ "error": "This account has been deactivated" }` — credentials valid but account is inactive; no token issued
- `401` invalid credentials

### Behavior notes

- After Supabase credential check passes, queries `profiles.is_active`
- If `false`, the fresh session is immediately revoked via `sign_out()` and a `403` is returned — client never receives a token

### Axios example

```ts
export async function login(email: string, password: string) {
  const res = await api.post("/auth/login", { email, password });
  return res.data;
}
```

## POST `/auth/refresh`

### Purpose

Exchange a refresh token for a new access token.

### Headers

- `Authorization: Bearer <refresh_token>`

### Request Body

- None

### Responses

- `200`

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ..."
}
```

- `401` `{ "error": "Invalid or expired refresh token" }`
- `500` `{ "error": "Token refresh failed", "details": "..." }`

---

## POST `/auth/reset-password`

### Purpose

Send a password reset email to the user. Always returns `200` regardless of
whether the email exists — this prevents user enumeration attacks.

### Request Body

```json
{
  "email": "user@example.com"
}
```

### Responses

- `200` `{ "message": "Password reset email sent" }`
- `400` `{ "error": "Email is required" }`
- `500` `{ "error": "Failed to send reset email", "details": "..." }`

> After calling this, Supabase emails the user a reset link. The link redirects
> to your app's deep link or web URL with a short-lived token in the URL.
> That token is used as the `Bearer` token in the confirm step below.

---

## POST `/auth/reset-password/confirm`

### Purpose

Set a new password for the user after they have clicked the reset link from
their email. The token from the reset link must be passed as the Bearer token.

### Headers

- `Authorization: Bearer <token_from_reset_email>`

### Request Body

```json
{
  "password": "newpassword123",
  "confirm_password": "newpassword123"
}
```

| Field              | Type   | Required | Description                     |
| ------------------ | ------ | -------- | ------------------------------- |
| `password`         | string | ✅       | New password (min 8 characters) |
| `confirm_password` | string | ✅       | Must match `password`           |

### Responses

- `200` `{ "message": "Password updated successfully" }`
- `400` `{ "error": "password and confirm_password are required" }`
- `400` `{ "error": "Passwords do not match" }`
- `400` `{ "error": "Password must be at least 8 characters" }`
- `401` `{ "error": "Missing or invalid authorization token" }`
- `500` `{ "error": "Failed to update password", "details": "..." }`

---

## Reset Password Flow

```
1. User taps "Forgot Password" in app
         ↓
2. App calls POST /auth/reset-password with user's email
         ↓
3. Supabase sends reset email to user
         ↓
4. User taps link in email
         ↓
5. App receives token via deep link (yourapp://reset-password?token=...)
         ↓
6. App calls POST /auth/reset-password/confirm
   with token as Bearer + new password in body
         ↓
7. Password updated — user can now log in
```

> Make sure your redirect URL is whitelisted in:
> **Supabase Dashboard → Authentication → URL Configuration → Redirect URLs**

---

## Axios (Mobile) Examples

```ts
export async function register(email: string, password: string) {
  const res = await api.post("/auth/register", { email, password });
  return res.data;
}

export async function login(email: string, password: string) {
  const res = await api.post("/auth/login", { email, password });
  return res.data;
}

export async function logout(accessToken: string) {
  const res = await api.post("/auth/logout", null, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return res.data;
}

export async function refreshToken(refreshToken: string) {
  const res = await api.post("/auth/refresh", null, {
    headers: { Authorization: `Bearer ${refreshToken}` },
  });
  return res.data;
}

export async function requestPasswordReset(email: string) {
  const res = await api.post("/auth/reset-password", { email });
  return res.data;
}

export async function confirmPasswordReset(
  resetToken: string,
  password: string,
  confirmPassword: string,
) {
  const res = await api.post(
    "/auth/reset-password/confirm",
    { password, confirm_password: confirmPassword },
    { headers: { Authorization: `Bearer ${resetToken}` } },
  );
  return res.data;
}
```
