# API Routes (Flask) — OnlyFoods Backend

> Base URL for mobile clients: `http://<HOST>:5000`
>
> The backend registers Flask blueprints with these URL prefixes:
>
> - `/auth`
> - `/profiles`
> - `/recipes`
> - `/favorites`
>
> All example paths below are relative to ``.

---

## Error response formats (common)

The app also registers global handlers:

| HTTP | Body                                   |
| ---: | -------------------------------------- |
|  400 | `{ "error": "Bad request" }`           |
|  401 | `{ "error": "Unauthorized" }`          |
|  403 | `{ "error": "Forbidden" }`             |
|  404 | `{ "error": "Not found" }`             |
|  409 | `{ "error": "Conflict" }`              |
|  500 | `{ "error": "Internal server error" }` |

In addition, individual routes return more specific payloads like `{ "error": "...", "details": ... }`.

---

## Auth routes (`/auth`)

See: `documentation/AUTH.md`

---

## Profiles routes (`/profiles`)

See: `documentation/PROFILES.md`

---

## Recipes routes (`/recipes`)

See: `documentation/RECIPES.md`

---

## Favorites routes (`/favorites`)

See: `documentation/FAVORITES.md`
