import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MinMaxScaler, LabelEncoder
from sklearn.neighbors import NearestNeighbors
from scipy.sparse import hstack, csr_matrix
import pickle

class RecipeRecommender:
    def __init__(self):
        self.tfidf_ingredients = TfidfVectorizer()
        self.tfidf_description = TfidfVectorizer(max_features=100)
        self.scaler = MinMaxScaler()
        self.cuisine_encoder = LabelEncoder()
        self.difficulty_encoder = LabelEncoder()
        self.knn = NearestNeighbors(n_neighbors=10, metric='cosine')
        self.recipes = []       # store raw recipe dicts
        self.fitted = False


    def _build_features(self, recipes, fit=False):
        """
        Turn recipe dicts into a single feature matrix.
        fit=True during training, fit=False during inference.
        """

        ingredient_texts = [" ".join(r["ingredients"]) for r in recipes]

        descriptions = [r.get("description", "") for r in recipes]

        numeric = np.array([[
            r["prep_time_minutes"],
            r["cook_time_minutes"],
            r["prep_time_minutes"] + r["cook_time_minutes"],  # total time
            r["servings"]
        ] for r in recipes], dtype=float)

        cuisines    = [r["cuisine_type"].lower() for r in recipes]
        difficulties = [r["difficulty"].lower() for r in recipes]

        if fit:
            ing_matrix   = self.tfidf_ingredients.fit_transform(ingredient_texts)
            desc_matrix  = self.tfidf_description.fit_transform(descriptions)
            numeric_scaled = self.scaler.fit_transform(numeric)

            self.cuisine_encoder.fit(cuisines + ["unknown"])
            self.difficulty_encoder.fit(difficulties + ["unknown"])
        else:
            ing_matrix     = self.tfidf_ingredients.transform(ingredient_texts)
            desc_matrix    = self.tfidf_description.transform(descriptions)
            numeric_scaled = self.scaler.transform(numeric)

        cuisine_encoded    = self.cuisine_encoder.transform(
            [c if c in self.cuisine_encoder.classes_ else "unknown" for c in cuisines]
        ).reshape(-1, 1)
        difficulty_encoded = self.difficulty_encoder.transform(
            [d if d in self.difficulty_encoder.classes_ else "unknown" for d in difficulties]
        ).reshape(-1, 1)

        weighted_ingredients = ing_matrix * 2

        feature_matrix = hstack([
            weighted_ingredients,              
            desc_matrix,                        
            csr_matrix(numeric_scaled),         
            csr_matrix(cuisine_encoded),        
            csr_matrix(difficulty_encoded),     
        ])

        return feature_matrix


    def fit(self, recipes: list[dict]):
        """
        recipes: list of recipe dicts matching RecipeCreateSchema
        """
        published = [r for r in recipes if r.get("is_published", True)]
        if len(published) < 2:
            raise ValueError("Need at least 2 published recipes to fit")

        self.recipes = published
        feature_matrix = self._build_features(published, fit=True)
        self.knn.fit(feature_matrix)
        self.fitted = True
        print(f"Fitted on {len(published)} recipes, "
              f"feature dim: {feature_matrix.shape[1]}")


    def recommend_by_index(self, recipe_index: int, n: int = 5) -> list[dict]:
        """Find recipes similar to recipes[recipe_index]"""
        if not self.fitted:
            raise RuntimeError("Call fit() first")

        feature_matrix = self._build_features(self.recipes, fit=False)
        query_vec = feature_matrix[recipe_index]

        distances, indices = self.knn.kneighbors(query_vec, n_neighbors=n + 1)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == recipe_index:
                continue    
            results.append({
                "recipe":     self.recipes[idx],
                "similarity": round(1 - float(dist), 4)   
            })

        return results[:n]


    def recommend_by_recipe(self, recipe: dict, n: int = 5) -> list[dict]:
        """Find recipes similar to an arbitrary recipe dict"""
        if not self.fitted:
            raise RuntimeError("Call fit() first")

        query_matrix = self._build_features([recipe], fit=False)
        distances, indices = self.knn.kneighbors(query_matrix, n_neighbors=n)

        return [{
            "recipe":     self.recipes[idx],
            "similarity": round(1 - float(dist), 4)
        } for dist, idx in zip(distances[0], indices[0])]


    def recommend_by_filters(
        self,
        cuisine_type: str = None,
        difficulty: str = None,
        max_total_time: int = None,
        n: int = 5
    ) -> list[dict]:
        """
        Returns top recipes matching given filters,
        ranked by how well they match each other (cluster quality).
        """
        candidates = self.recipes

        if cuisine_type:
            candidates = [r for r in candidates
                          if r["cuisine_type"].lower() == cuisine_type.lower()]
        if difficulty:
            candidates = [r for r in candidates
                          if r["difficulty"].lower() == difficulty.lower()]
        if max_total_time:
            candidates = [r for r in candidates
                          if r["prep_time_minutes"] + r["cook_time_minutes"] <= max_total_time]

        candidates.sort(key=lambda r: r["prep_time_minutes"] + r["cook_time_minutes"])
        return [{"recipe": r, "similarity": None} for r in candidates[:n]]


    def save(self, path="recipe_recommender.pkl"):
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load(path="recipe_recommender.pkl"):
        with open(path, "rb") as f:
            return pickle.load(f)