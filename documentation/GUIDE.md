# Mobile Setup Guide (React Native Expo + Axios)

This guide explains how to connect an Expo (React Native) app to this Flask backend using **Axios only**, with **mobile auth** via `Authorization: Bearer <access_token>`.

---

## 1) Install Axios

```bash
npm i axios
```

No other Axios-related packages are required.

---

## 2) Environment variable for API base URL

In Expo, add an environment variable like:

- `EXPO_PUBLIC_API_BASE_URL`

Example values (depends on where Flask runs):

- Android emulator: `http://10.0.2.2:5000`
- iOS simulator: `http://localhost:5000`
- Physical device: `http://<your-computer-ip>:5000`

Use it as:

- `{{API_BASE_URL}}` = `process.env.EXPO_PUBLIC_API_BASE_URL`

---

## 3) Token storage (access_token)

The backend expects:

- `Authorization: Bearer <access_token>`

Store the access token on device after login (example storage approach):

- `@react-native-async-storage/async-storage` (common)

This repo requirement says “Axios ONLY”; storage library is not Axios, so it’s optional. If you already use a storage solution, plug it into the examples.

---

## 4) Create a reusable Axios instance

Create `services.ts`:

```ts
// services.ts
import axios from "axios";
import { getAccessToken } from "./tokenStorage";

const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL;

export const api = axios.create({
  baseURL: API_BASE_URL,
});

// Inject Authorization header for mobile auth
api.interceptors.request.use(async (config) => {
  const token = await getAccessToken();
  if (token) {
    config.headers = {
      ...config.headers,
      Authorization: `Bearer ${token}`,
    };
  }
  return config;
});

// Standardize error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const data = error.response?.data;

    // Backend errors are usually { error: "...", details?: "..." }
    // You can throw a normalized error object.
    throw {
      status,
      data,
      message: data?.error ?? error.message,
    };
  },
);
```

### Minimal token storage helper (example)

Create `services/tokenStorage.ts`:

```ts
// services/tokenStorage.ts
// Replace with your own storage.
let accessToken: string | null = null;

export async function setAccessToken(token: string) {
  accessToken = token;
}

export async function getAccessToken() {
  return accessToken;
}

export async function clearAccessToken() {
  accessToken = null;
}
```

---

## 5) Service layer structure (recommended)

Example folder structure:

```
src/
  services/
    api.ts
    tokenStorage.ts
    authService.ts
    profilesService.ts
    recipesService.ts
    favoritesService.ts
```

### Example: `authService.ts`

```ts
// services/authService.ts
import { api } from ".";
import { setAccessToken, clearAccessToken } from "./tokenStorage";

export async function login(email: string, password: string) {
  const res = await api.post("/auth/login", { email, password });
  const { access_token } = res.data;
  await setAccessToken(access_token);
  return res.data;
}

export async function register(
  email: string,
  password: string,
  username: string,
) {
  return api.post("/auth/register", { email, password, username });
}

export async function me() {
  return api.get("/auth/me");
}

export async function logout() {
  await clearAccessToken();
  return api.post("/auth/logout");
}
```

---

## 6) Axios usage notes (mobile auth)

- For endpoints that require auth, the backend reads:
  - `Authorization: Bearer <token>`
- With the interceptor approach above, you don’t need to manually set the header every time.
- For multipart uploads (avatar, recipe media), set the `Content-Type: multipart/form-data` and append `file`.

---

## 7) Quick route references

See these docs for per-route examples:

- `documentation/AUTH.md`
- `documentation/PROFILES.md`
- `documentation/RECIPES.md`
- `documentation/FAVORITES.md`
