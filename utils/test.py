"""
test_recommender.py
Run this directly: python test_recommender.py
Tests the RecipeRecommender model before wiring it into Flask.
"""

import requests
import json

BASE_URL = "http://localhost:5000"   # change if your Flask port differs

# ---------------------------------------------------------------------------
# 1.  Sample recipe data (20 recipes across cuisines / difficulties)
# ---------------------------------------------------------------------------

SAMPLE_RECIPES = [
    # ── Italian ─────────────────────────────────────────────────────────────
    {
        "title": "Spaghetti Carbonara",
        "description": "Classic Roman pasta with eggs, cheese, pancetta and pepper.",
        "ingredients": ["spaghetti", "eggs", "pecorino romano", "pancetta", "black pepper"],
        "steps": ["Boil pasta", "Fry pancetta", "Mix eggs and cheese", "Combine off heat"],
        "cuisine_type": "italian",
        "difficulty": "medium",
        "prep_time_minutes": 10,
        "cook_time_minutes": 20,
        "servings": 2,
        "is_published": True,
    },
    {
        "title": "Margherita Pizza",
        "description": "Neapolitan pizza with tomato, mozzarella and basil.",
        "ingredients": ["pizza dough", "tomato sauce", "mozzarella", "basil", "olive oil"],
        "steps": ["Stretch dough", "Spread sauce", "Add cheese", "Bake at 250 C", "Top with basil"],
        "cuisine_type": "italian",
        "difficulty": "medium",
        "prep_time_minutes": 20,
        "cook_time_minutes": 15,
        "servings": 4,
        "is_published": True,
    },
    {
        "title": "Risotto ai Funghi",
        "description": "Creamy mushroom risotto with parmesan and white wine.",
        "ingredients": ["arborio rice", "mushrooms", "parmesan", "white wine", "onion", "butter", "vegetable stock"],
        "steps": ["Saute onion", "Toast rice", "Add wine", "Ladle stock gradually", "Finish with butter and parmesan"],
        "cuisine_type": "italian",
        "difficulty": "hard",
        "prep_time_minutes": 15,
        "cook_time_minutes": 35,
        "servings": 4,
        "is_published": True,
    },
    {
        "title": "Bruschetta al Pomodoro",
        "description": "Toasted bread topped with fresh tomatoes, garlic and basil.",
        "ingredients": ["sourdough bread", "tomatoes", "garlic", "basil", "olive oil", "salt"],
        "steps": ["Toast bread", "Rub with garlic", "Mix tomatoes with oil and basil", "Top and serve"],
        "cuisine_type": "italian",
        "difficulty": "easy",
        "prep_time_minutes": 10,
        "cook_time_minutes": 5,
        "servings": 4,
        "is_published": True,
    },

    # ── Mexican ──────────────────────────────────────────────────────────────
    {
        "title": "Chicken Tacos",
        "description": "Juicy grilled chicken in corn tortillas with salsa and avocado.",
        "ingredients": ["chicken breast", "corn tortillas", "avocado", "salsa", "lime", "cilantro", "cumin"],
        "steps": ["Marinate chicken", "Grill chicken", "Warm tortillas", "Assemble tacos"],
        "cuisine_type": "mexican",
        "difficulty": "easy",
        "prep_time_minutes": 15,
        "cook_time_minutes": 15,
        "servings": 4,
        "is_published": True,
    },
    {
        "title": "Black Bean Enchiladas",
        "description": "Cheesy enchiladas stuffed with spiced black beans.",
        "ingredients": ["flour tortillas", "black beans", "enchilada sauce", "cheddar", "onion", "cumin", "chili powder"],
        "steps": ["Cook beans with spices", "Fill tortillas", "Roll and place in dish", "Top with sauce and cheese", "Bake"],
        "cuisine_type": "mexican",
        "difficulty": "medium",
        "prep_time_minutes": 20,
        "cook_time_minutes": 30,
        "servings": 6,
        "is_published": True,
    },
    {
        "title": "Guacamole",
        "description": "Fresh, chunky guacamole ready in minutes.",
        "ingredients": ["avocado", "lime juice", "onion", "cilantro", "jalapeño", "salt"],
        "steps": ["Mash avocado", "Mix in remaining ingredients", "Season and serve"],
        "cuisine_type": "mexican",
        "difficulty": "easy",
        "prep_time_minutes": 10,
        "cook_time_minutes": 0,
        "servings": 4,
        "is_published": True,
    },

    # ── Japanese ─────────────────────────────────────────────────────────────
    {
        "title": "Chicken Ramen",
        "description": "Rich chicken broth ramen with soft-boiled eggs and noodles.",
        "ingredients": ["ramen noodles", "chicken broth", "chicken thigh", "soft-boiled eggs", "nori", "green onion", "soy sauce", "mirin"],
        "steps": ["Simmer broth", "Cook chicken", "Boil noodles", "Assemble bowls", "Top with egg and nori"],
        "cuisine_type": "japanese",
        "difficulty": "hard",
        "prep_time_minutes": 20,
        "cook_time_minutes": 90,
        "servings": 2,
        "is_published": True,
    },
    {
        "title": "Salmon Sushi Rolls",
        "description": "Fresh salmon and cucumber maki rolls with pickled ginger.",
        "ingredients": ["sushi rice", "nori", "salmon", "cucumber", "rice vinegar", "soy sauce", "pickled ginger", "wasabi"],
        "steps": ["Cook and season rice", "Layer nori and rice", "Add fillings", "Roll tightly", "Slice"],
        "cuisine_type": "japanese",
        "difficulty": "hard",
        "prep_time_minutes": 30,
        "cook_time_minutes": 20,
        "servings": 4,
        "is_published": True,
    },
    {
        "title": "Miso Soup",
        "description": "Simple warming miso soup with tofu and wakame.",
        "ingredients": ["white miso paste", "dashi stock", "silken tofu", "wakame seaweed", "green onion"],
        "steps": ["Heat dashi", "Dissolve miso", "Add tofu and wakame", "Garnish and serve"],
        "cuisine_type": "japanese",
        "difficulty": "easy",
        "prep_time_minutes": 5,
        "cook_time_minutes": 10,
        "servings": 2,
        "is_published": True,
    },

    # ── Indian ───────────────────────────────────────────────────────────────
    {
        "title": "Butter Chicken",
        "description": "Tender chicken in a rich, creamy tomato and butter sauce.",
        "ingredients": ["chicken thigh", "butter", "tomatoes", "heavy cream", "garlic", "ginger", "garam masala", "cumin", "coriander"],
        "steps": ["Marinate chicken", "Grill chicken", "Make sauce", "Simmer chicken in sauce", "Finish with cream"],
        "cuisine_type": "indian",
        "difficulty": "medium",
        "prep_time_minutes": 30,
        "cook_time_minutes": 40,
        "servings": 4,
        "is_published": True,
    },
    {
        "title": "Dal Tadka",
        "description": "Yellow lentils tempered with cumin, garlic and chili.",
        "ingredients": ["yellow lentils", "onion", "tomatoes", "garlic", "ginger", "cumin seeds", "turmeric", "ghee", "green chili"],
        "steps": ["Boil lentils", "Fry onion, tomato and spices", "Combine", "Make tadka with ghee and cumin", "Pour over dal"],
        "cuisine_type": "indian",
        "difficulty": "easy",
        "prep_time_minutes": 10,
        "cook_time_minutes": 30,
        "servings": 4,
        "is_published": True,
    },
    {
        "title": "Palak Paneer",
        "description": "Fresh spinach curry with cubes of soft paneer cheese.",
        "ingredients": ["spinach", "paneer", "onion", "tomatoes", "garlic", "ginger", "cream", "garam masala", "cumin"],
        "steps": ["Blanch spinach", "Puree spinach", "Cook masala base", "Add spinach puree", "Add paneer and cream"],
        "cuisine_type": "indian",
        "difficulty": "medium",
        "prep_time_minutes": 15,
        "cook_time_minutes": 25,
        "servings": 4,
        "is_published": True,
    },

    # ── American ─────────────────────────────────────────────────────────────
    {
        "title": "Classic Cheeseburger",
        "description": "Juicy beef patty with cheddar, lettuce and all the fixings.",
        "ingredients": ["ground beef", "cheddar", "brioche bun", "lettuce", "tomato", "onion", "pickles", "ketchup", "mustard"],
        "steps": ["Form patties", "Season and grill", "Add cheese to melt", "Toast buns", "Assemble"],
        "cuisine_type": "american",
        "difficulty": "easy",
        "prep_time_minutes": 10,
        "cook_time_minutes": 15,
        "servings": 4,
        "is_published": True,
    },
    {
        "title": "BBQ Pulled Pork",
        "description": "Slow-cooked pork shoulder in smoky BBQ sauce.",
        "ingredients": ["pork shoulder", "BBQ sauce", "apple cider vinegar", "brown sugar", "smoked paprika", "garlic powder", "onion powder"],
        "steps": ["Rub pork with spices", "Slow cook 8 hours", "Shred meat", "Mix with BBQ sauce"],
        "cuisine_type": "american",
        "difficulty": "medium",
        "prep_time_minutes": 20,
        "cook_time_minutes": 480,
        "servings": 8,
        "is_published": True,
    },
    {
        "title": "Mac and Cheese",
        "description": "Ultra-creamy baked mac and cheese with breadcrumb topping.",
        "ingredients": ["macaroni", "cheddar", "gruyere", "butter", "flour", "milk", "breadcrumbs", "mustard powder"],
        "steps": ["Boil pasta", "Make roux", "Add milk and cheese", "Combine with pasta", "Top with breadcrumbs", "Bake"],
        "cuisine_type": "american",
        "difficulty": "medium",
        "prep_time_minutes": 15,
        "cook_time_minutes": 35,
        "servings": 6,
        "is_published": True,
    },

    # ── Thai ─────────────────────────────────────────────────────────────────
    {
        "title": "Pad Thai",
        "description": "Stir-fried rice noodles with shrimp, peanuts and tamarind.",
        "ingredients": ["rice noodles", "shrimp", "eggs", "bean sprouts", "peanuts", "tamarind paste", "fish sauce", "lime", "green onion"],
        "steps": ["Soak noodles", "Stir-fry shrimp", "Add noodles and sauce", "Scramble in eggs", "Toss with sprouts", "Garnish"],
        "cuisine_type": "thai",
        "difficulty": "medium",
        "prep_time_minutes": 20,
        "cook_time_minutes": 15,
        "servings": 2,
        "is_published": True,
    },
    {
        "title": "Green Curry",
        "description": "Fragrant coconut green curry with chicken and vegetables.",
        "ingredients": ["green curry paste", "coconut milk", "chicken breast", "zucchini", "bell pepper", "fish sauce", "lime leaves", "basil"],
        "steps": ["Fry curry paste", "Add coconut milk", "Add chicken", "Add vegetables", "Finish with fish sauce and basil"],
        "cuisine_type": "thai",
        "difficulty": "medium",
        "prep_time_minutes": 15,
        "cook_time_minutes": 20,
        "servings": 4,
        "is_published": True,
    },
    {
        "title": "Mango Sticky Rice",
        "description": "Sweet glutinous rice with fresh mango and coconut cream.",
        "ingredients": ["glutinous rice", "coconut milk", "sugar", "salt", "fresh mango", "sesame seeds"],
        "steps": ["Soak rice overnight", "Steam rice", "Heat coconut milk with sugar", "Combine rice and coconut milk", "Serve with mango"],
        "cuisine_type": "thai",
        "difficulty": "easy",
        "prep_time_minutes": 480,
        "cook_time_minutes": 30,
        "servings": 4,
        "is_published": True,
    },
    {
        "title": "Tom Yum Soup",
        "description": "Hot and sour Thai soup with shrimp, lemongrass and mushrooms.",
        "ingredients": ["shrimp", "lemongrass", "kaffir lime leaves", "galangal", "mushrooms", "fish sauce", "lime juice", "chili", "chicken stock"],
        "steps": ["Simmer aromatics in stock", "Add mushrooms", "Add shrimp", "Season with fish sauce and lime", "Garnish with cilantro"],
        "cuisine_type": "thai",
        "difficulty": "medium",
        "prep_time_minutes": 15,
        "cook_time_minutes": 20,
        "servings": 4,
        "is_published": True,
    },
]

# ---------------------------------------------------------------------------
# 2.  Sample swipe history (for testing the personalized endpoint)
# ---------------------------------------------------------------------------

SAMPLE_SWIPES = {
    "user_123": {
        "liked":    ["Spaghetti Carbonara", "Margherita Pizza", "Risotto ai Funghi"],   # Italian fan
        "disliked": ["Mango Sticky Rice", "Guacamole"],
    },
    "user_456": {
        "liked":    ["Butter Chicken", "Dal Tadka", "Palak Paneer"],                    # Indian fan
        "disliked": ["Classic Cheeseburger"],
    },
    "user_789": {
        "liked":    ["Pad Thai", "Green Curry", "Tom Yum Soup"],                        # Thai fan
        "disliked": [],
    },
}

# ---------------------------------------------------------------------------
# 3.  Test helpers
# ---------------------------------------------------------------------------

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def post(path, body):
    r = requests.post(f"{BASE_URL}{path}", json=body)
    print(f"POST {path}  →  {r.status_code}")
    data = r.json()
    print(json.dumps(data, indent=2, default=str))
    return data

def get(path, params=None):
    r = requests.get(f"{BASE_URL}{path}", params=params)
    print(f"GET  {path}  →  {r.status_code}")
    data = r.json()
    print(json.dumps(data, indent=2, default=str))
    return data

# ---------------------------------------------------------------------------
# 4.  Tests
# ---------------------------------------------------------------------------

def test_train():
    section("TRAIN  –  fit model on 20 sample recipes")
    return post("/reccomendations/train", {"recipes": SAMPLE_RECIPES})


def test_recommend_by_recipe():
    section("RECOMMEND BY RECIPE  –  similar to Spaghetti Carbonara")
    carbonara = SAMPLE_RECIPES[0]
    return post("/reccomendations/reccomend", {"recipe": carbonara, "n": 4})


def test_recommend_by_index():
    section("RECOMMEND BY INDEX  –  similar to index 0 (Spaghetti Carbonara)")
    return get("/recipes/0/similar", {"n": 4})


def test_filter_italian_easy():
    section("FILTER  –  italian + easy")
    return get("/reccomendations/filter", {"cuisine_type": "italian", "difficulty": "easy"})


def test_filter_quick_thai():
    section("FILTER  –  thai + max 40 min total")
    return get("/reccomendations/filter", {"cuisine_type": "thai", "max_total_time": 40})


def test_cold_start():
    """New user with no swipe history – falls back to filter-based"""
    section("COLD START  –  new user, no swipe history")
    return get("/reccomendations/filter", {"cuisine_type": "italian", "n": 3})


def test_personalized():
    """
    Simulate the personalized endpoint:
    average the feature vectors of liked recipes to build a user profile.
    (You'll need to add the /recommendations/personalized route –- see routes below.)
    """
    section("PERSONALIZED  –  user_123 (Italian fan)")
    liked_titles = SAMPLE_SWIPES["user_123"]["liked"]
    liked_recipes = [r for r in SAMPLE_RECIPES if r["title"] in liked_titles]
    disliked_titles = SAMPLE_SWIPES["user_123"]["disliked"]

    return post("/reccomendations/personalized", {
        "liked_recipes":    liked_recipes,
        "disliked_titles":  disliked_titles,   # exclude these from results
        "n": 4
    })


# ---------------------------------------------------------------------------
# 5.  Run all tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_train()
    test_recommend_by_recipe()
    test_recommend_by_index()
    test_filter_italian_easy()
    test_filter_quick_thai()
    test_cold_start()
    # test_personalized()   # uncomment after adding the /personalized route
    print("\n✅  All tests done.")