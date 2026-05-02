# Favorites Route

Viewing your favorite recipe

## Getting Users Favorite Recipe

```tsx
// GET /api/recipes/me/saved
const getSavedRecipes = async (page = 1, perPage = 10) => {
  try {
    const res = await api.get("/recipes/me/saved", {
      params: {
        page,
        per_page: perPage,
      },
    });

    const { data, pagination } = res.data;
    console.log(data); // array of saved recipes
    console.log(pagination); // { page, per_page, total, total_pages }
    return res.data;
  } catch (err) {
    if (err.response?.status === 401) {
      console.error("Not logged in");
    }
  }
};
```

## Saving a Recipe

```tsx
// POST /api/recipes/<recipe_id>/save
const saveRecipe = async (recipeId) => {
  try {
    const res = await api.post(`/recipes/${recipeId}/save`);
    console.log(res.data.message); // "Recipe saved successfully"
    return res.data;
  } catch (err) {
    if (err.response?.status === 409) {
      console.error("Recipe already saved");
    } else if (err.response?.status === 401) {
      console.error("Not logged in");
    } else if (err.response?.status === 404) {
      console.error("Recipe not found");
    }
  }
};
```

## Unsaving a Recipe

```tsx
// DELETE /api/recipes/<recipe_id>/save
const unsaveRecipe = async (recipeId) => {
  try {
    const res = await api.delete(`/recipes/${recipeId}/save`);
    console.log(res.data.message); // "Recipe unsaved successfully"
    return res.data;
  } catch (err) {
    if (err.response?.status === 404) {
      console.error("Recipe not in saved list");
    } else if (err.response?.status === 401) {
      console.error("Not logged in");
    }
  }
};
```
