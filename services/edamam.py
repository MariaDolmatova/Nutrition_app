import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

BASE_URL = "https://api.edamam.com/api/recipes/v2"

MEAL_TYPE_MAP = {
    "breakfast": "breakfast",
    "lunch": "lunch",
    "dinner": "dinner",
}

HEALTH_LABEL_MAP = {
    "Vegan": "vegan",
    "Vegetarian": "vegetarian",
    "Gluten-free": "gluten-free",
    "Keto": "keto",
    "Paleo": "paleo",
}

COOK_TIME_MAP = {
    "Up to 30 min": (0, 30),
    "Up to 1 hour": (0, 60),
    "No limit": (0, 9999),
    "Any": (0, 9999),
}


def search_recipes(
    query: str,
    meal_type: str = "",
    diet_labels: list[str] | None = None,
    ingredients: list[str] | None = None,
    max_time: int = 9999,
    count: int = 8,
    from_idx: int = 0,
) -> list[dict]:
    load_dotenv(override=True)
    APP_ID = os.getenv("EDAMAM_APP_ID", "")
    APP_KEY = os.getenv("EDAMAM_APP_KEY", "")
    if not APP_ID or not APP_KEY:
        print("Edamam API keys not configured. Add EDAMAM_APP_ID and EDAMAM_APP_KEY to your .env file.")
        return _mock_recipes(query, meal_type, count, from_idx)

    EDAMAM_USER_ID = "default_user"

    q = query
    if ingredients:
        q = query + " " + " ".join(ingredients)

    params: dict = {
        "type": "public",
        "app_id": APP_ID,
        "app_key": APP_KEY,
        "q": q,
        "from": from_idx,
        "to": from_idx + count,
    }

    if meal_type and meal_type in MEAL_TYPE_MAP:
        params["mealType"] = MEAL_TYPE_MAP[meal_type]

    if diet_labels:
        health_values = [HEALTH_LABEL_MAP[d] for d in diet_labels if d in HEALTH_LABEL_MAP]
        if health_values:
            params["health"] = health_values[0]

    if max_time < 9999:
        params["time"] = f"1-{max_time}"

    headers = {}
    if EDAMAM_USER_ID:
        headers["Edamam-Account-User"] = EDAMAM_USER_ID

    try:
        resp = requests.get(BASE_URL, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "error":
            print(f"Edamam error: {data.get('message', 'Unknown error')}")
            return []
        hits = data.get("hits", [])
        return [_parse_hit(h) for h in hits]
    except requests.exceptions.HTTPError as e:
        print(f"Edamam HTTP error: {e}")
        return []
    except requests.exceptions.ConnectionError:
        print("Could not reach Edamam. Falling back to mock data.")
        return _mock_recipes(query, meal_type, count, from_idx)
    except Exception as e:
        print(f"Unexpected error fetching recipes: {e}")
        return []


def _parse_hit(hit: dict) -> dict:
    r         = hit.get("recipe", {})
    recipe_id = hit.get("_links", {}).get("self", {}).get("href", "") or r.get("uri", "")
    nutrients = r.get("totalNutrients", {})
    servings  = max(r.get("yield", 1) or 1, 1)

    def nut(key):
        return round(nutrients.get(key, {}).get("quantity", 0) / servings, 1)

    return {
        "id": recipe_id,
        "name": r.get("label", "Unknown Recipe"),
        "image": r.get("image", ""),
        "url": r.get("url", ""),
        "source": r.get("source", ""),
        "diet_labels": r.get("dietLabels", []),
        "health_labels": r.get("healthLabels", []),
        "ingredient_lines": r.get("ingredientLines", []),
        "calories": round(r.get("calories", 0) / servings),
        "protein": nut("PROCNT"),
        "carbs": nut("CHOCDF"),
        "fat": nut("FAT"),
        "total_time": r.get("totalTime", 0),
        "cuisine_type": r.get("cuisineType", []),
        "meal_type": r.get("mealType", []),
        "yield": servings,
    }


_MOCK_TEMPLATES = [
    # name, diet_labels, health_labels, kcal, prot, carbs, fat, time
    ("Grilled Chicken Salad",       ["Balanced", "High-Protein"], ["Gluten-Free"],    420, 38, 18,  14, 20),
    ("Avocado Toast",               ["Balanced"],                 ["Vegetarian"],     310, 10, 32,  16, 10),
    ("Oatmeal with Berries",        ["Balanced"],                 ["Vegan", "Vegetarian"], 290, 9, 54, 5, 10),
    ("Pasta Primavera",             ["Balanced"],                 ["Vegetarian"],     480, 14, 72,  12, 25),
    ("Lentil Soup",                 ["High-Fiber"],               ["Vegan", "Vegetarian"], 340, 18, 52, 6, 35),
    ("Stir-Fried Tofu",             ["Balanced"],                 ["Vegan", "Vegetarian"], 380, 22, 28, 18, 20),
    ("Banana Smoothie Bowl",        ["Balanced"],                 ["Vegan", "Vegetarian"], 310, 8, 62,  5, 5),
    ("Turkey Wrap",                 ["Balanced", "High-Protein"], [],                 390, 32, 38,  10, 15),
    ("Quinoa Buddha Bowl",          ["Balanced", "High-Protein"], ["Vegan", "Vegetarian"], 440, 18, 58, 14, 30),
    ("Egg Fried Rice",              ["Balanced"],                 ["Vegetarian"],     420, 14, 62,  12, 20),
    ("Greek Salad",                 ["Low-Carb"],                 ["Vegetarian", "Gluten-Free"], 280, 8, 16, 20, 10),
    ("Black Bean Tacos",            ["Balanced", "High-Fiber"],   ["Vegetarian"],     410, 16, 58,  10, 20),
    ("Salmon with Roasted Veg",     ["Balanced", "High-Protein"], ["Gluten-Free"],    460, 42, 22,  20, 30),
    ("Mushroom Risotto",            ["Balanced"],                 ["Vegetarian"],     520, 14, 74,  16, 40),
    ("Peanut Noodles",              ["Balanced"],                 ["Vegan", "Vegetarian"], 490, 16, 68, 16, 20),
    ("Chickpea Curry",              ["Balanced", "High-Fiber"],   ["Vegan", "Vegetarian"], 400, 14, 56, 12, 30),
    ("Veggie Omelette",             ["Balanced", "High-Protein"], ["Vegetarian", "Gluten-Free"], 320, 24, 8, 20, 15),
    ("Beef Stir Fry",               ["Balanced", "High-Protein"], ["Gluten-Free"],    430, 36, 24,  16, 20),
    ("Sweet Potato Soup",           ["Balanced"],                 ["Vegan", "Vegetarian"], 320, 6, 58,  8, 30),
    ("Tuna Nicoise",                ["Balanced", "High-Protein"], ["Gluten-Free"],    380, 34, 18,  18, 15),
    ("Shakshuka",                   ["Balanced"],                 ["Vegetarian", "Gluten-Free"], 340, 18, 22, 18, 25),
    ("Cauliflower Fried Rice",      ["Low-Carb"],                 ["Vegan", "Vegetarian", "Gluten-Free"], 260, 10, 18, 14, 20),
    ("Shrimp Tacos",                ["Balanced", "High-Protein"], [],                 380, 28, 42,  10, 20),
    ("Pesto Pasta",                 ["Balanced"],                 ["Vegetarian"],     560, 18, 70,  20, 20),
    ("Miso Glazed Tofu",            ["Balanced"],                 ["Vegan", "Vegetarian"], 360, 20, 30, 16, 25),
    ("Lamb Kofta",                  ["Balanced", "High-Protein"], ["Gluten-Free"],    440, 34, 12,  26, 30),
    ("Beet Hummus Bowl",            ["Balanced"],                 ["Vegan", "Vegetarian"], 380, 12, 48, 14, 20),
    ("Coconut Lentil Dal",          ["Balanced", "High-Fiber"],   ["Vegan", "Vegetarian"], 420, 16, 60, 12, 35),
    ("Zucchini Pasta",              ["Low-Carb"],                 ["Vegan", "Vegetarian", "Gluten-Free"], 280, 10, 20, 16, 20),
    ("Breakfast Burrito",           ["Balanced"],                 ["Vegetarian"],     490, 22, 54,  18, 20),
    ("Soba Noodle Salad",           ["Balanced"],                 ["Vegan", "Vegetarian"], 400, 14, 62, 10, 15),
    ("Stuffed Bell Peppers",        ["Balanced"],                 ["Vegetarian", "Gluten-Free"], 380, 16, 44, 12, 40),
    ("Butternut Squash Soup",       ["Balanced"],                 ["Vegan", "Vegetarian"], 290, 6, 50,  8, 35),
    ("Teriyaki Salmon",             ["Balanced", "High-Protein"], [],                 460, 40, 28,  18, 25),
    ("White Bean Stew",             ["Balanced", "High-Fiber"],   ["Vegan", "Vegetarian"], 360, 18, 52, 6, 35),
    ("Acai Smoothie Bowl",          ["Balanced"],                 ["Vegan", "Vegetarian"], 340, 8, 64,  6, 5),
    ("Pad Thai",                    ["Balanced"],                 [],                 520, 22, 68,  16, 25),
    ("Caprese Salad",               ["Low-Carb"],                 ["Vegetarian", "Gluten-Free"], 300, 16, 10, 22, 10),
    ("Turkey Meatballs",            ["Balanced", "High-Protein"], ["Gluten-Free"],    400, 36, 18,  18, 30),
    ("Falafel Bowl",                ["Balanced", "High-Fiber"],   ["Vegan", "Vegetarian"], 480, 18, 60, 16, 30),
    ("Eggplant Parmigiana",         ["Balanced"],                 ["Vegetarian"],     480, 18, 44,  22, 45),
    ("Spinach Lentil Soup",         ["Balanced", "High-Fiber"],   ["Vegan", "Vegetarian"], 310, 16, 48, 6, 30),
    ("Veggie Burger",               ["Balanced"],                 ["Vegan", "Vegetarian"], 420, 20, 52, 12, 20),
    ("Roasted Veggie Tray Bake",    ["Balanced"],                 ["Vegan", "Vegetarian", "Gluten-Free"], 320, 8, 46, 12, 40),
    ("Mushroom Tacos",              ["Balanced"],                 ["Vegan", "Vegetarian"], 380, 10, 52, 14, 20),
    ("Pumpkin Gnocchi",             ["Balanced"],                 ["Vegetarian"],     500, 14, 72,  16, 35),
    ("Broccoli Cheddar Soup",       ["Balanced"],                 ["Vegetarian"],     360, 16, 28,  20, 25),
    ("Tofu Tikka Masala",           ["Balanced"],                 ["Vegan", "Vegetarian"], 420, 20, 40, 18, 30),
    ("Vegetable Tagine",            ["Balanced", "High-Fiber"],   ["Vegan", "Vegetarian"], 380, 12, 62, 8, 45),
    ("Spinach Ricotta Cannelloni",  ["Balanced"],                 ["Vegetarian"],     520, 24, 58,  20, 40),
    ("Tomato Basil Soup",           ["Balanced"],                 ["Vegan", "Vegetarian"], 240, 6, 36,  8, 25),
    ("Black Bean Soup",             ["Balanced", "High-Fiber"],   ["Vegan", "Vegetarian"], 320, 16, 50, 6, 30),
    ("Aubergine Moussaka",          ["Balanced"],                 ["Vegetarian"],     480, 20, 42,  22, 50),
    ("Paneer Tikka",                ["Balanced", "High-Protein"], ["Vegetarian", "Gluten-Free"], 440, 26, 18, 28, 30),
    ("Veggie Chilli",               ["Balanced", "High-Fiber"],   ["Vegan", "Vegetarian"], 360, 14, 56, 8, 35),
    ("Cheese Quesadilla",           ["Balanced"],                 ["Vegetarian"],     420, 18, 46,  18, 15),
    ("Spring Rolls",                ["Balanced"],                 ["Vegan", "Vegetarian"], 340, 8, 54,  10, 25),
    ("Noodle Veggie Stir Fry",      ["Balanced"],                 ["Vegan", "Vegetarian"], 400, 12, 60, 12, 20),
    ("Caprese Stuffed Avocado",     ["Low-Carb"],                 ["Vegetarian", "Gluten-Free"], 320, 10, 12, 26, 10),
    ("Lentil Bolognese",            ["Balanced", "High-Fiber"],   ["Vegan", "Vegetarian"], 460, 20, 66, 8, 35),
    ("Mediterranean Bowl",          ["Mediterranean"],            ["Vegetarian"],     440, 16, 54,  16, 20),
    ("Grilled Halloumi Salad",      ["Balanced"],                 ["Vegetarian", "Gluten-Free"], 380, 20, 16, 26, 15),
]


def _mock_recipes(query: str, meal_type: str, count: int, from_idx: int = 0) -> list[dict]:
    n     = len(_MOCK_TEMPLATES)
    start = from_idx % n
    pool  = (_MOCK_TEMPLATES * 2)[start:start + count]
    results = []
    for i, t in enumerate(pool):
        name, diet_labels, health_labels, kcal, prot, carbs, fat, time = t
        results.append({
            "id": f"mock_{from_idx}_{i}_{meal_type}",
            "name": name,
            "image": "",
            "url": "#",
            "source": "Mock",
            "diet_labels": diet_labels,
            "health_labels": health_labels,
            "ingredient_lines": ["1 cup ingredient A", "2 tbsp ingredient B"],
            "calories": kcal,
            "protein": float(prot),
            "carbs": float(carbs),
            "fat": float(fat),
            "total_time": time,
            "cuisine_type": ["international"],
            "meal_type": [meal_type or "lunch"],
            "yield": 1,
        })
    return results
