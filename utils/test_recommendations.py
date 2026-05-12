"""
test_recommender.py
Run: python test_recommender.py

Tests all endpoints against the current state of the project:
  - No difficulty / prep_time_minutes fields (removed from schema)
  - favorites_count added
  - PyTorch embedding model
  - Seen tracking via user_id
  - Fine-tune endpoint
  - Reset-seen endpoint
  - Updated route paths (/similar/<index>, /fine-tune, /reset-seen)
"""

import requests
import json

BASE_URL = "http://localhost:5000/recommendations"

# ── Helpers ──────────────────────────────────────────────────────────────────

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def post(path, body):
    r = requests.post(f"{BASE_URL}{path}", json=body)
    print(f"POST {BASE_URL}{path}  →  {r.status_code}")
    try:
        data = r.json()
        print(json.dumps(data, indent=2, default=str))
        return data
    except Exception:
        print(r.text)
        return {}

def get(path, params=None):
    r = requests.get(f"{BASE_URL}{path}", params=params)
    print(f"GET  {BASE_URL}{path}  →  {r.status_code}")
    try:
        data = r.json()
        print(json.dumps(data, indent=2, default=str))
        return data
    except Exception:
        print(r.text)
        return {}

# ── Sample Recipes ────────────────────────────────────────────────────────────

SAMPLE_RECIPES = [
    # ── Italian ──────────────────────────────────────────────────────────────
    {
        "title": "Spaghetti Carbonara",
        "description": "Classic Roman pasta with eggs, cheese, pancetta and pepper.",
        "ingredients": ["spaghetti", "eggs", "pecorino romano", "pancetta", "black pepper"],
        "steps": ["Boil pasta", "Fry pancetta", "Mix eggs and cheese", "Combine off heat"],
        "cuisine_type": "italian",
        "cook_time_minutes": 20,
        "servings": 2,
        "is_published": True,
        "favorites_count": 142
    },
    {
        "title": "Margherita Pizza",
        "description": "Neapolitan pizza with tomato, mozzarella and basil.",
        "ingredients": ["pizza dough", "tomato sauce", "mozzarella", "basil", "olive oil"],
        "steps": ["Stretch dough", "Spread sauce", "Add cheese", "Bake at 250 C", "Top with basil"],
        "cuisine_type": "italian",
        "cook_time_minutes": 15,
        "servings": 4,
        "is_published": True,
        "favorites_count": 198
    },
    {
        "title": "Risotto ai Funghi",
        "description": "Creamy mushroom risotto with parmesan and white wine.",
        "ingredients": ["arborio rice", "mushrooms", "parmesan", "white wine", "onion", "butter", "vegetable stock"],
        "steps": ["Saute onion", "Toast rice", "Add wine", "Ladle stock gradually", "Finish with butter and parmesan"],
        "cuisine_type": "italian",
        "cook_time_minutes": 35,
        "servings": 4,
        "is_published": True,
        "favorites_count": 87
    },
    {
        "title": "Bruschetta al Pomodoro",
        "description": "Toasted bread topped with fresh tomatoes, garlic and basil.",
        "ingredients": ["sourdough bread", "tomatoes", "garlic", "basil", "olive oil", "salt"],
        "steps": ["Toast bread", "Rub with garlic", "Mix tomatoes with oil and basil", "Top and serve"],
        "cuisine_type": "italian",
        "cook_time_minutes": 5,
        "servings": 4,
        "is_published": True,
        "favorites_count": 54
    },

    # ── Mexican ───────────────────────────────────────────────────────────────
    {
        "title": "Chicken Tacos",
        "description": "Juicy grilled chicken in corn tortillas with salsa and avocado.",
        "ingredients": ["chicken breast", "corn tortillas", "avocado", "salsa", "lime", "cilantro", "cumin"],
        "steps": ["Marinate chicken", "Grill chicken", "Warm tortillas", "Assemble tacos"],
        "cuisine_type": "mexican",
        "cook_time_minutes": 15,
        "servings": 4,
        "is_published": True,
        "favorites_count": 231
    },
    {
        "title": "Black Bean Enchiladas",
        "description": "Cheesy enchiladas stuffed with spiced black beans.",
        "ingredients": ["flour tortillas", "black beans", "enchilada sauce", "cheddar", "onion", "cumin", "chili powder"],
        "steps": ["Cook beans with spices", "Fill tortillas", "Roll and place in dish", "Top with sauce and cheese", "Bake"],
        "cuisine_type": "mexican",
        "cook_time_minutes": 30,
        "servings": 6,
        "is_published": True,
        "favorites_count": 76
    },
    {
        "title": "Guacamole",
        "description": "Fresh, chunky guacamole ready in minutes.",
        "ingredients": ["avocado", "lime juice", "onion", "cilantro", "jalapeno", "salt"],
        "steps": ["Mash avocado", "Mix in remaining ingredients", "Season and serve"],
        "cuisine_type": "mexican",
        "cook_time_minutes": 0,
        "servings": 4,
        "is_published": True,
        "favorites_count": 163
    },

    # ── Japanese ──────────────────────────────────────────────────────────────
    {
        "title": "Chicken Ramen",
        "description": "Rich chicken broth ramen with soft-boiled eggs and noodles.",
        "ingredients": ["ramen noodles", "chicken broth", "chicken thigh", "soft-boiled eggs", "nori", "green onion", "soy sauce", "mirin"],
        "steps": ["Simmer broth", "Cook chicken", "Boil noodles", "Assemble bowls", "Top with egg and nori"],
        "cuisine_type": "japanese",
        "cook_time_minutes": 90,
        "servings": 2,
        "is_published": True,
        "favorites_count": 311
    },
    {
        "title": "Salmon Sushi Rolls",
        "description": "Fresh salmon and cucumber maki rolls with pickled ginger.",
        "ingredients": ["sushi rice", "nori", "salmon", "cucumber", "rice vinegar", "soy sauce", "pickled ginger", "wasabi"],
        "steps": ["Cook and season rice", "Layer nori and rice", "Add fillings", "Roll tightly", "Slice"],
        "cuisine_type": "japanese",
        "cook_time_minutes": 20,
        "servings": 4,
        "is_published": True,
        "favorites_count": 278
    },
    {
        "title": "Miso Soup",
        "description": "Simple warming miso soup with tofu and wakame.",
        "ingredients": ["white miso paste", "dashi stock", "silken tofu", "wakame seaweed", "green onion"],
        "steps": ["Heat dashi", "Dissolve miso", "Add tofu and wakame", "Garnish and serve"],
        "cuisine_type": "japanese",
        "cook_time_minutes": 10,
        "servings": 2,
        "is_published": True,
        "favorites_count": 95
    },

    # ── Indian ────────────────────────────────────────────────────────────────
    {
        "title": "Butter Chicken",
        "description": "Tender chicken in a rich, creamy tomato and butter sauce.",
        "ingredients": ["chicken thigh", "butter", "tomatoes", "heavy cream", "garlic", "ginger", "garam masala", "cumin", "coriander"],
        "steps": ["Marinate chicken", "Grill chicken", "Make sauce", "Simmer chicken in sauce", "Finish with cream"],
        "cuisine_type": "indian",
        "cook_time_minutes": 40,
        "servings": 4,
        "is_published": True,
        "favorites_count": 389
    },
    {
        "title": "Dal Tadka",
        "description": "Yellow lentils tempered with cumin, garlic and chili.",
        "ingredients": ["yellow lentils", "onion", "tomatoes", "garlic", "ginger", "cumin seeds", "turmeric", "ghee", "green chili"],
        "steps": ["Boil lentils", "Fry onion tomato and spices", "Combine", "Make tadka with ghee and cumin", "Pour over dal"],
        "cuisine_type": "indian",
        "cook_time_minutes": 30,
        "servings": 4,
        "is_published": True,
        "favorites_count": 112
    },
    {
        "title": "Palak Paneer",
        "description": "Fresh spinach curry with cubes of soft paneer cheese.",
        "ingredients": ["spinach", "paneer", "onion", "tomatoes", "garlic", "ginger", "cream", "garam masala", "cumin"],
        "steps": ["Blanch spinach", "Puree spinach", "Cook masala base", "Add spinach puree", "Add paneer and cream"],
        "cuisine_type": "indian",
        "cook_time_minutes": 25,
        "servings": 4,
        "is_published": True,
        "favorites_count": 145
    },

    # ── American ──────────────────────────────────────────────────────────────
    {
        "title": "Classic Cheeseburger",
        "description": "Juicy beef patty with cheddar, lettuce and all the fixings.",
        "ingredients": ["ground beef", "cheddar", "brioche bun", "lettuce", "tomato", "onion", "pickles", "ketchup", "mustard"],
        "steps": ["Form patties", "Season and grill", "Add cheese to melt", "Toast buns", "Assemble"],
        "cuisine_type": "american",
        "cook_time_minutes": 15,
        "servings": 4,
        "is_published": True,
        "favorites_count": 267
    },
    {
        "title": "BBQ Pulled Pork",
        "description": "Slow-cooked pork shoulder in smoky BBQ sauce.",
        "ingredients": ["pork shoulder", "BBQ sauce", "apple cider vinegar", "brown sugar", "smoked paprika", "garlic powder", "onion powder"],
        "steps": ["Rub pork with spices", "Slow cook 8 hours", "Shred meat", "Mix with BBQ sauce"],
        "cuisine_type": "american",
        "cook_time_minutes": 480,
        "servings": 8,
        "is_published": True,
        "favorites_count": 183
    },
    {
        "title": "Mac and Cheese",
        "description": "Ultra-creamy baked mac and cheese with breadcrumb topping.",
        "ingredients": ["macaroni", "cheddar", "gruyere", "butter", "flour", "milk", "breadcrumbs", "mustard powder"],
        "steps": ["Boil pasta", "Make roux", "Add milk and cheese", "Combine with pasta", "Top with breadcrumbs", "Bake"],
        "cuisine_type": "american",
        "cook_time_minutes": 35,
        "servings": 6,
        "is_published": True,
        "favorites_count": 224
    },

    # ── Thai ──────────────────────────────────────────────────────────────────
    {
        "title": "Pad Thai",
        "description": "Stir-fried rice noodles with shrimp, peanuts and tamarind.",
        "ingredients": ["rice noodles", "shrimp", "eggs", "bean sprouts", "peanuts", "tamarind paste", "fish sauce", "lime", "green onion"],
        "steps": ["Soak noodles", "Stir-fry shrimp", "Add noodles and sauce", "Scramble in eggs", "Toss with sprouts", "Garnish"],
        "cuisine_type": "thai",
        "cook_time_minutes": 15,
        "servings": 2,
        "is_published": True,
        "favorites_count": 302
    },
    {
        "title": "Green Curry",
        "description": "Fragrant coconut green curry with chicken and vegetables.",
        "ingredients": ["green curry paste", "coconut milk", "chicken breast", "zucchini", "bell pepper", "fish sauce", "lime leaves", "basil"],
        "steps": ["Fry curry paste", "Add coconut milk", "Add chicken", "Add vegetables", "Finish with fish sauce and basil"],
        "cuisine_type": "thai",
        "cook_time_minutes": 20,
        "servings": 4,
        "is_published": True,
        "favorites_count": 256
    },
    {
        "title": "Mango Sticky Rice",
        "description": "Sweet glutinous rice with fresh mango and coconut cream.",
        "ingredients": ["glutinous rice", "coconut milk", "sugar", "salt", "fresh mango", "sesame seeds"],
        "steps": ["Soak rice overnight", "Steam rice", "Heat coconut milk with sugar", "Combine rice and coconut milk", "Serve with mango"],
        "cuisine_type": "thai",
        "cook_time_minutes": 30,
        "servings": 4,
        "is_published": True,
        "favorites_count": 178
    },
    {
        "title": "Tom Yum Soup",
        "description": "Hot and sour Thai soup with shrimp, lemongrass and mushrooms.",
        "ingredients": ["shrimp", "lemongrass", "kaffir lime leaves", "galangal", "mushrooms", "fish sauce", "lime juice", "chili", "chicken stock"],
        "steps": ["Simmer aromatics in stock", "Add mushrooms", "Add shrimp", "Season with fish sauce and lime", "Garnish with cilantro"],
        "cuisine_type": "thai",
        "cook_time_minutes": 20,
        "servings": 4,
        "is_published": True,
        "favorites_count": 219
    }
]

# ── Sample swipe history ──────────────────────────────────────────────────────

SAMPLE_SWIPES = {
    "user_123": {
        "liked":    ["Spaghetti Carbonara", "Margherita Pizza", "Risotto ai Funghi"],
        "disliked": ["Mango Sticky Rice", "Guacamole"],
    },
    "user_456": {
        "liked":    ["Butter Chicken", "Dal Tadka", "Palak Paneer"],
        "disliked": ["Classic Cheeseburger"],
    },
    "user_789": {
        "liked":    ["Pad Thai", "Green Curry", "Tom Yum Soup"],
        "disliked": [],
    },
}

# Swipe triplets for fine-tuning
SWIPE_TRIPLETS = [
    {
        "anchor":   SAMPLE_RECIPES[0],   # Spaghetti Carbonara
        "liked":    SAMPLE_RECIPES[1],   # Margherita Pizza
        "disliked": SAMPLE_RECIPES[7],   # Chicken Ramen
    },
    {
        "anchor":   SAMPLE_RECIPES[10],  # Butter Chicken
        "liked":    SAMPLE_RECIPES[12],  # Palak Paneer
        "disliked": SAMPLE_RECIPES[13],  # Classic Cheeseburger
    },
    {
        "anchor":   SAMPLE_RECIPES[16],  # Pad Thai
        "liked":    SAMPLE_RECIPES[17],  # Green Curry
        "disliked": SAMPLE_RECIPES[3],   # Bruschetta
    },
    {
        "anchor":   SAMPLE_RECIPES[8],   # Salmon Sushi
        "liked":    SAMPLE_RECIPES[7],   # Chicken Ramen
        "disliked": SAMPLE_RECIPES[14],  # BBQ Pulled Pork
    },
    {
        "anchor":   SAMPLE_RECIPES[4],   # Chicken Tacos
        "liked":    SAMPLE_RECIPES[5],   # Black Bean Enchiladas
        "disliked": SAMPLE_RECIPES[19],  # Tom Yum Soup
    },
]

# ── Tests ─────────────────────────────────────────────────────────────────────

def test_train():
    section("1. TRAIN — fit model on 20 recipes")
    return post("/train", {"recipes": SAMPLE_RECIPES})


def test_recommend_by_recipe():
    section("2. RECOMMEND BY RECIPE — Spaghetti Carbonara, first call (user_123)")
    return post("/recommend", {
        "recipe":  SAMPLE_RECIPES[0],
        "n":       5,
        "user_id": "user_123"
    })


def test_recommend_by_recipe_again():
    section("3. RECOMMEND BY RECIPE — same recipe, second call (should differ — seen tracking)")
    return post("/recommend", {
        "recipe":  SAMPLE_RECIPES[0],
        "n":       5,
        "user_id": "user_123"
    })


def test_recommend_by_index():
    section("4. RECOMMEND BY INDEX — index 10 (Butter Chicken), user_456")
    return get("/similar/10", {"n": 4, "user_id": "user_456"})


def test_filter_italian():
    section("5. FILTER — italian cuisine")
    return get("/filter", {"cuisine_type": "italian", "n": 3, "user_id": "user_123"})


def test_filter_quick():
    section("6. FILTER — max 20 min cook time")
    return get("/filter", {"max_cook_time": 20, "n": 5})


def test_swipe_user_123():
    section("7. SWIPE — record likes/dislikes for user_123 (Italian fan)")
    liked_titles    = SAMPLE_SWIPES["user_123"]["liked"]
    disliked_titles = SAMPLE_SWIPES["user_123"]["disliked"]

    liked_recipes    = [r for r in SAMPLE_RECIPES if r["title"] in liked_titles]
    disliked_recipes = [r for r in SAMPLE_RECIPES if r["title"] in disliked_titles]

    for recipe in liked_recipes:
        post("/swipe", {"user_id": "user_123", "recipe": recipe, "direction": "like"})
    for recipe in disliked_recipes:
        post("/swipe", {"user_id": "user_123", "recipe": recipe, "direction": "dislike"})


def test_swipe_user_456():
    section("8. SWIPE — record likes/dislikes for user_456 (Indian fan)")
    liked_titles    = SAMPLE_SWIPES["user_456"]["liked"]
    disliked_titles = SAMPLE_SWIPES["user_456"]["disliked"]

    liked_recipes    = [r for r in SAMPLE_RECIPES if r["title"] in liked_titles]
    disliked_recipes = [r for r in SAMPLE_RECIPES if r["title"] in disliked_titles]

    for recipe in liked_recipes:
        post("/swipe", {"user_id": "user_456", "recipe": recipe, "direction": "like"})
    for recipe in disliked_recipes:
        post("/swipe", {"user_id": "user_456", "recipe": recipe, "direction": "dislike"})


def test_personalized_by_user_id():
    section("9. PERSONALIZED — look up from swipe store (user_123)")
    return post("/personalized", {
        "user_id": "user_123",
        "n": 5
    })


def test_personalized_direct():
    section("10. PERSONALIZED — pass liked/disliked directly (user_456 Indian fan)")
    liked_titles  = SAMPLE_SWIPES["user_456"]["liked"]
    liked_recipes = [r for r in SAMPLE_RECIPES if r["title"] in liked_titles]

    return post("/personalized", {
        "liked_recipes":   liked_recipes,
        "disliked_titles": SAMPLE_SWIPES["user_456"]["disliked"],
        "n": 5,
        "user_id": "user_456"
    })


def test_cold_start():
    section("11. COLD START — new user with no swipe history")
    return post("/personalized", {
        "liked_recipes": [],
        "n": 5,
        "user_id": "brand_new_user"
    })


def test_fine_tune():
    section("12. FINE-TUNE — train on swipe triplets (3 epochs)")
    return post("/fine-tune", {
        "swipe_history": SWIPE_TRIPLETS,
        "epochs": 3
    })


def test_recommend_after_fine_tune():
    section("13. RECOMMEND AFTER FINE-TUNE — reset seen, then recommend (should reflect learning)")
    post("/reset-seen", {"user_id": "user_123"})
    return post("/recommend", {
        "recipe":  SAMPLE_RECIPES[0],   # Spaghetti Carbonara
        "n":       5,
        "user_id": "user_123"
    })


def test_reset_seen():
    section("14. RESET SEEN — clear history for user_123")
    return post("/reset-seen", {"user_id": "user_123"})


# ── Run all ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🚀 Starting recommendation system tests...")
    print(f"   Target: {BASE_URL}\n")

    test_train()                      # 1 — must run first
    test_recommend_by_recipe()        # 2 — first call, records seen
    test_recommend_by_recipe_again()  # 3 — should return different results
    test_recommend_by_index()         # 4
    test_filter_italian()             # 5
    test_filter_quick()               # 6
    test_swipe_user_123()             # 7 — populate swipe store
    test_swipe_user_456()             # 8
    test_personalized_by_user_id()    # 9 — reads from swipe store
    test_personalized_direct()        # 10 — pass liked recipes directly
    test_cold_start()                 # 11 — no history, falls back to filter
    test_fine_tune()                  # 12 — fine-tune on triplets
    test_recommend_after_fine_tune()  # 13 — verify fine-tune changed output
    test_reset_seen()                 # 14 — clean up

    print("\n✅  All tests done.")