# Setup: React Native Expo (Axios) ↔ Flask Backend

This backend is a Flask app with `url_prefix` blueprints:

- `/auth` (register/login/logout/me)
- `/profiles`
- `/recipes`
- `/favorites`

> Notes on auth: the backend uses **Supabase access tokens** derived from the `Authorization: Bearer <access_token>` header **or** a Flask session (web). For React Native, use the **Authorization header** flow.

---

## 1) Install Axios

```bash
# in your Expo/React Native project
npm i axios
# or
yarn add axios
```

---

## 2) Environment variables (Expo)

In your Expo project, define an API base URL.

```bash
# .env (example)
EXPO_PUBLIC_API_BASE_URL=http://YOUR_BACKEND_HOST:5000
```

Expo convention:

- `EXPO_PUBLIC_...` values are available on the client.

---

## 3) Token storage (React Native)

The backend expects:

- `Authorization: Bearer <access_token>`

So you need to persist the Supabase access token from `/auth/login`.

Example using `@react-native-async-storage/async-storage`:

```bash
npm i @react-native-async-storage/async-storage
```

Token helper:

```ts
// storage/authStorage.ts
import AsyncStorage from "@react-native-async-storage/async-storage";

const TOKEN_KEY = "access_token";

export const authStorage = {
  async getAccessToken(): Promise<string | null> {
    return AsyncStorage.getItem(TOKEN_KEY);
  },
  async setAccessToken(token: string) {
    return AsyncStorage.setItem(TOKEN_KEY, token);
  },
  async clearAccessToken() {
    return AsyncStorage.removeItem(TOKEN_KEY);
  },
};
```

---

## 4) Reusable Axios instance + interceptors

```ts
// services.ts
import axios from "axios";
import { authStorage } from "../storage/authStorage";

export const api = axios.create({
  baseURL: process.env.EXPO_PUBLIC_API_BASE_URL,
  timeout: 15000,
});

// Inject Bearer token into each request (if available)
api.interceptors.request.use(async (config) => {
  const token = await authStorage.getAccessToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Centralized error handling pattern
api.interceptors.response.use(
  (res) => res,
  (error) => {
    // Axios error shape
    const status = error.response?.status;
    const data = error.response?.data;

    // Example: normalize error into a consistent shape
    return Promise.reject({
      status,
      data,
      message:
        data?.error || data?.message || error.message || "Request failed",
    });
  },
);
```

---

## 5) Example service layer structure

Suggested folder layout (scalable):

```
services/
  api.ts
  authService.ts
  profilesService.ts
  recipesService.ts
  favoritesService.ts
```

---

## 6) Copy-paste Axios base example

```ts
// Example: public request (no auth required)
import { api } from ".";

export const listProfiles = async () => {
  const res = await api.get("/profiles/");
  return res.data;
};
```

Authentication-required requests will automatically include the Bearer token via the interceptor.
