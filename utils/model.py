import random
import pickle
import numpy as np
import torch
import torch.nn as nn
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import MinMaxScaler


# ── PyTorch Embedding Model ──────────────────────────────────────────────────

class RecipeEmbeddingModel(nn.Module):
    def __init__(self, vocab_size, cuisine_count, embedding_dim=64):
        super().__init__()

        # Replaces TF-IDF — learns which ingredients matter together
        self.ingredient_embedding = nn.EmbeddingBag(
            vocab_size, embedding_dim, mode="mean", padding_idx=0
        )

        # Replaces LabelEncoder — learns cuisine relationships
        self.cuisine_embedding = nn.Embedding(cuisine_count, 16, padding_idx=0)

        # Numeric: cook_time, servings, favorites_count
        self.numeric_layer = nn.Sequential(
            nn.Linear(3, 16),
            nn.ReLU()
        )

        # Fuse all features into one compact recipe vector
        self.fusion = nn.Sequential(
            nn.Linear(embedding_dim + 16 + 16, 128),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(128, 64)  # final vector fed into KNN
        )

    def forward(self, ingredient_ids, cuisine_id, numerics):
        ing_emb = self.ingredient_embedding(ingredient_ids)
        cui_emb = self.cuisine_embedding(cuisine_id).squeeze(1)
        num_emb = self.numeric_layer(numerics)
        fused   = torch.cat([ing_emb, cui_emb, num_emb], dim=-1)
        return self.fusion(fused)


# ── Swipe Loss (Triplet) ─────────────────────────────────────────────────────

class SwipeLoss(nn.Module):
    def __init__(self, margin=0.5):
        super().__init__()
        self.loss = nn.TripletMarginLoss(margin=margin, p=2)

    def forward(self, anchor, positive, negative):
        return self.loss(anchor, positive, negative)


# ── Main Recommender ─────────────────────────────────────────────────────────

class RecipeRecommender:
    def __init__(self):
        self.embedding_model = None
        self.knn             = NearestNeighbors(n_neighbors=10, metric='cosine')
        self.scaler          = MinMaxScaler()

        # Vocab built at fit time
        self.vocab       = {}   # ingredient word → index
        self.cuisine_map = {}   # cuisine string   → index

        self.recipes = []
        self.fitted  = False

        # Per-user seen tracking: { user_id: set of recipe titles }
        self._seen_store: dict = {}

    # ── Encoding helpers ─────────────────────────────────────────────────────

    def _encode_recipe(self, recipe):
        """Convert one recipe dict into three tensors."""
        ing_ids = [self.vocab.get(w.lower(), 0) for w in recipe["ingredients"]]
        if not ing_ids:
            ing_ids = [0]

        ing_tensor     = torch.tensor([ing_ids], dtype=torch.long)
        cuisine_tensor = torch.tensor(
            [self.cuisine_map.get(recipe["cuisine_type"].lower(), 0)],
            dtype=torch.long
        )
        numeric_tensor = torch.tensor([[
            recipe.get("cook_time_minutes", 0),
            recipe.get("servings", 1),
            recipe.get("favorites_count", 0),
        ]], dtype=torch.float)

        return ing_tensor, cuisine_tensor, numeric_tensor

    def _build_features(self, recipes):
        """Run recipes through embedding model → numpy matrix for KNN."""
        self.embedding_model.eval()
        vectors = []
        with torch.no_grad():
            for r in recipes:
                ing, cui, num = self._encode_recipe(r)
                vec = self.embedding_model(ing, cui, num)
                vectors.append(vec.squeeze().numpy())
        return np.array(vectors)

    # ── Fit ──────────────────────────────────────────────────────────────────

    def fit(self, recipes: list[dict]):
        published = [r for r in recipes if r.get("is_published", True) and r.get("active", True)]
        if len(published) < 2:
            raise ValueError("Need at least 2 published recipes to fit")

        # Build ingredient vocab
        all_words  = [w.lower() for r in published for w in r["ingredients"]]
        self.vocab = {w: i + 1 for i, w in enumerate(set(all_words))}  # 0 = padding

        # Build cuisine map
        cuisines        = list(set(r["cuisine_type"].lower() for r in published))
        self.cuisine_map = {c: i + 1 for i, c in enumerate(cuisines)}  # 0 = padding

        # Init embedding model
        self.embedding_model = RecipeEmbeddingModel(
            vocab_size    = len(self.vocab) + 1,
            cuisine_count = len(self.cuisine_map) + 1,
        )

        self.recipes = published
        feature_matrix = self._build_features(published)
        self.knn.fit(feature_matrix)
        self.fitted = True
        print(f"[RecipeRecommender] Fitted on {len(published)} recipes, "
              f"embedding dim: {feature_matrix.shape[1]}")

    # ── Fine-tune on swipes ──────────────────────────────────────────────────

    def fine_tune_on_swipes(self, swipe_history: list[dict], epochs=5, lr=1e-3):
        """
        swipe_history: list of:
          { "anchor": <recipe>, "liked": <recipe>, "disliked": <recipe> }
        Pulls liked recipes closer to anchor, pushes disliked ones away.
        Re-indexes KNN after training so recommendations update immediately.
        """
        if not self.fitted:
            raise RuntimeError("Call fit() first")
        if len(swipe_history) < 3:
            raise ValueError("Need at least 3 swipe triplets to fine-tune")

        optimizer = torch.optim.Adam(self.embedding_model.parameters(), lr=lr)
        loss_fn   = SwipeLoss()

        self.embedding_model.train()
        for epoch in range(epochs):
            total_loss = 0.0
            for entry in swipe_history:
                anchor_vec   = self.embedding_model(*self._encode_recipe(entry["anchor"]))
                positive_vec = self.embedding_model(*self._encode_recipe(entry["liked"]))
                negative_vec = self.embedding_model(*self._encode_recipe(entry["disliked"]))

                loss = loss_fn(anchor_vec, positive_vec, negative_vec)
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                total_loss += loss.item()

            print(f"[fine_tune] Epoch {epoch + 1}/{epochs}  loss: {total_loss:.4f}")

        # Re-index KNN with updated embeddings so next recommend() reflects learning
        feature_matrix = self._build_features(self.recipes)
        self.knn.fit(feature_matrix)
        print("[fine_tune] KNN re-indexed.")

    # ── Recommend by recipe ──────────────────────────────────────────────────

    def recommend_by_recipe(
        self,
        recipe: dict,
        n: int = 5,
        user_id: str = None,
        diversity: float = 0.3,
    ) -> list[dict]:
        """
        Returns n recommendations for a given recipe.
        - Skips recipes the user has already seen (if user_id provided)
        - Adds diversity so the same query doesn't always return identical results
        """
        if not self.fitted:
            raise RuntimeError("Call fit() first")

        seen = self._seen_store.get(user_id, set()) if user_id else set()

        # Fetch a large pool so we have room to filter + diversify
        pool_size    = min(len(self.recipes), n * 4)
        query_matrix = self._build_features([recipe])
        distances, indices = self.knn.kneighbors(query_matrix, n_neighbors=pool_size)

        candidates = []
        for dist, idx in zip(distances[0], indices[0]):
            r = self.recipes[idx]
            if not r.get("active", True):       # ← skip inactive
                continue
            if r["title"] == recipe.get("title"):
                continue
            if r["title"] in seen:
                continue
            candidates.append({"recipe": r, "similarity": round(1 - float(dist), 4)})

        # Diversify: keep top half by similarity, shuffle the rest
        split      = max(1, int(len(candidates) * (1 - diversity)))
        top_half   = candidates[:split]
        rest       = candidates[split:]
        random.shuffle(rest)
        results    = (top_half + rest)[:n]

        # Mark shown
        if user_id:
            seen.update(r["recipe"]["title"] for r in results)
            self._seen_store[user_id] = seen

        return results

    # ── Recommend by index ───────────────────────────────────────────────────

    def recommend_by_index(
        self,
        recipe_index: int,
        n: int = 5,
        user_id: str = None,
    ) -> list[dict]:
        if not self.fitted:
            raise RuntimeError("Call fit() first")

        recipe = self.recipes[recipe_index]
        return self.recommend_by_recipe(recipe, n=n, user_id=user_id)

    def recommend_by_filters(
        self,
        cuisine_types: list[str] = None,   # was: cuisine_type (single string)
        max_cook_time: int = None,
        min_cook_time: int = None,         # new
        min_servings: int = None,          # new
        max_servings: int = None,          # new
        n: int = 5,
        user_id: str = None,
    ) -> list[dict]:
        seen       = self._seen_store.get(user_id, set()) if user_id else set()
        candidates = [r for r in self.recipes if r.get("active", True)]

        if cuisine_types:
            cuisine_types_lower = [c.lower() for c in cuisine_types if isinstance(c, str)]
            candidates = [r for r in candidates
                        if isinstance(r.get("cuisine_type"), str) and 
                        r["cuisine_type"].lower() in cuisine_types_lower]
        if min_cook_time is not None:
            candidates = [r for r in candidates
                        if r["cook_time_minutes"] >= min_cook_time]
        if max_cook_time is not None:
            candidates = [r for r in candidates
                        if r["cook_time_minutes"] <= max_cook_time]

        if min_servings is not None:
            candidates = [r for r in candidates
                        if r.get("servings", 1) >= min_servings]
        if max_servings is not None:
            candidates = [r for r in candidates
                        if r.get("servings", 1) <= max_servings]

        candidates = [r for r in candidates if r["title"] not in seen]
        candidates.sort(key=lambda r: r.get("favorites_count", 0), reverse=True)

        results = [{"recipe": r, "similarity": None} for r in candidates[:n]]

        if user_id:
            seen.update(r["recipe"]["title"] for r in results)
            self._seen_store[user_id] = seen

        return results

    # ── Personalized (centroid of liked recipes) ─────────────────────────────

    def recommend_personalized(
        self,
        liked_recipes: list[dict],
        disliked_titles: list[str] = None,
        n: int = 5,
        user_id: str = None,
    ) -> list[dict]:
        if not self.fitted:
            raise RuntimeError("Call fit() first")

        disliked_titles = set(disliked_titles or [])
        seen            = self._seen_store.get(user_id, set()) if user_id else set()

        if not liked_recipes:
            return self.recommend_by_filters(n=n, user_id=user_id)

        # Average embeddings of liked recipes → taste centroid
        self.embedding_model.eval()
        with torch.no_grad():
            vecs     = [self.embedding_model(*self._encode_recipe(r)) for r in liked_recipes]
            centroid = torch.stack(vecs).mean(dim=0).numpy()

        distances, indices = self.knn.kneighbors(
            centroid.reshape(1, -1),
            n_neighbors=min(len(self.recipes), n * 4)
        )

        liked_titles = {r["title"] for r in liked_recipes}
        excluded     = liked_titles | disliked_titles | seen

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            r = self.recipes[idx]
            if not r.get("active", True):       # ← skip inactive
                continue
            if r["title"] in excluded:
                continue
            results.append({
                "recipe":     r,
                "similarity": round(1 - float(dist), 4),
            })
            if len(results) >= n:
                break

        if user_id:
            seen.update(r["recipe"]["title"] for r in results)
            self._seen_store[user_id] = seen

        return results

    # ── Recommend by ingredients ─────────────────────────────────────────────

    def recommend_by_ingredients(
        self,
        ingredients: list[str],
        n: int = 10,
        user_id: str = None,
        diversity: float = 0.5,
    ) -> list[dict]:
        if not self.fitted:
            raise RuntimeError("Call fit() first")

        query = [w.lower() for w in ingredients]
        seen  = self._seen_store.get(user_id, set()) if user_id else set()

        candidates = []
        for r in self.recipes:
            if not r.get("active", True):
                continue
            if r["title"] in seen:
                continue

            recipe_ingredients = [w.lower() for w in r["ingredients"]]

            # Check if ALL queried terms appear anywhere inside any ingredient string
            # e.g. "chicken" matches "500g chicken breast" or "diced chicken"
            def ingredient_matches(query_term: str) -> bool:
                return any(query_term in ing for ing in recipe_ingredients)

            if not all(ingredient_matches(q) for q in query):
                continue

            # Score by how many recipe ingredients contain any of the queried terms
            overlap_score = sum(
                1 for ing in recipe_ingredients
                if any(q in ing for q in query)
            )

            candidates.append({
                "recipe":        r,
                "overlap_score": overlap_score,
                "similarity":    None,
            })

        if not candidates:
            return []

        candidates.sort(key=lambda x: x["overlap_score"], reverse=True)

        split    = max(1, int(len(candidates) * (1 - diversity)))
        top_half = candidates[:split]
        rest     = candidates[split:]
        random.shuffle(rest)

        results = (top_half + rest)[:n]

        for r in results:
            r.pop("overlap_score")

        if user_id:
            seen.update(r["recipe"]["title"] for r in results)
            self._seen_store[user_id] = seen

        return results

    # ── Reset seen for a user ────────────────────────────────────────────────

    def reset_seen(self, user_id: str):
        self._seen_store.pop(user_id, None)

    # ── Persist ──────────────────────────────────────────────────────────────

    def save(self, path="recipe_recommender.pkl"):
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load(path="recipe_recommender.pkl"):
        with open(path, "rb") as f:
            return pickle.load(f)