import json
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).parent.parent / "db.json"


def _load_db() -> dict:
    if not DB_PATH.exists():
        return {"history": [], "likes": []}
    try:
        with open(DB_PATH) as f:
            data = json.load(f)
        data.setdefault("likes", [])
        return data
    except Exception:
        return {"history": [], "likes": []}


def _save_db(data: dict):
    with open(DB_PATH, "w") as f:
        json.dump(data, f, indent=2)


def load_history() -> list[dict]:
    return _load_db().get("history", [])


def log_cooked(recipe_id: str, recipe_name: str, diet_labels: list[str]):
    data = _load_db()
    data["history"].append({
        "recipe_id": recipe_id,
        "recipe_name": recipe_name,
        "diet_labels": diet_labels,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    _save_db(data)


def like_recipe(recipe: dict):
    data = _load_db()
    recipe_id = recipe.get("id", "")
    if not any(l.get("id") == recipe_id for l in data["likes"]):
        data["likes"].append({
            "id": recipe_id,
            "name": recipe.get("name", ""),
            "data": recipe,
        })
    _save_db(data)


def unlike_recipe(recipe_id: str):
    data = _load_db()
    data["likes"] = [l for l in data["likes"] if l.get("id") != recipe_id]
    _save_db(data)


def is_liked(recipe_id: str) -> bool:
    return any(l.get("id") == recipe_id for l in _load_db().get("likes", []))


def dislike_recipe(recipe: dict):
    data = _load_db()
    recipe_id = recipe.get("id", "")
    data.setdefault("dislikes", [])
    if not any(d.get("id") == recipe_id for d in data["dislikes"]):
        data["dislikes"].append({
            "id": recipe_id,
            "name": recipe.get("name", ""),
            "data": recipe,
        })
    # Remove from likes if it was there
    data["likes"] = [l for l in data.get("likes", []) if l.get("id") != recipe_id]
    _save_db(data)


def undislike_recipe(recipe_id: str):
    data = _load_db()
    data["dislikes"] = [d for d in data.get("dislikes", []) if d.get("id") != recipe_id]
    _save_db(data)


def is_disliked(recipe_id: str) -> bool:
    return any(d.get("id") == recipe_id for d in _load_db().get("dislikes", []))


def get_disliked_recipes() -> list[dict]:
    return [d["data"] for d in _load_db().get("dislikes", []) if d.get("data")]


def get_liked_recipes() -> list[dict]:
    return [l["data"] for l in _load_db().get("likes", []) if l.get("data")]


def calculate_nutrition_targets(profile: dict) -> dict:
    weight = float(profile.get("weight", 70))
    height = float(profile.get("height", 170))
    age = int(profile.get("age", 25))
    gender = profile.get("gender", "Male")
    activity = profile.get("activity_level", "Moderate")
    goal = profile.get("goal", "Maintain weight")

    if "male" in gender.lower():
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161

    multipliers = {"Sedentary": 1.2, "Light": 1.375, "Moderate": 1.55, "Very active": 1.725}
    tdee = bmr * multipliers.get(activity, 1.55)

    if goal == "Lose weight":
        calories = tdee - 300
    elif goal == "Gain weight":
        calories = tdee + 300
    else:
        calories = tdee

    return {
        "calories": round(calories),
        "protein": round((calories * 0.25) / 4),
        "carbs": round((calories * 0.50) / 4),
        "fat": round((calories * 0.25) / 9),
    }


def score_recipe(recipe: dict, user_profile: dict) -> float:
    score = 1.0
    history = load_history()

    pref_diets = set(d.lower() for d in user_profile.get("dietary_preferences", []))
    recipe_diets = set(d.lower() for d in recipe.get("diet_labels", []))
    if pref_diets and pref_diets & recipe_diets:
        score += 0.3

    cook_time = recipe.get("total_time", 0)
    max_cook = user_profile.get("max_cook_time", "No limit")
    if max_cook == "Up to 30 min" and 0 < cook_time <= 30:
        score += 0.2
    elif max_cook == "Up to 1 hour" and 0 < cook_time <= 60:
        score += 0.1

    goal = user_profile.get("goal", "Maintain weight")
    calories = recipe.get("calories", 500)
    if goal == "Lose weight" and calories < 400:
        score += 0.2
    elif goal == "Gain weight" and calories > 600:
        score += 0.2
    elif goal == "Maintain weight" and 350 <= calories <= 650:
        score += 0.1

    if history:
        cooked_diets: dict[str, int] = {}
        for entry in history:
            for dl in entry.get("diet_labels", []):
                cooked_diets[dl.lower()] = cooked_diets.get(dl.lower(), 0) + 1
        for dl in recipe.get("diet_labels", []):
            if dl.lower() in cooked_diets:
                score += 0.1 * min(cooked_diets[dl.lower()], 3)

    return round(score, 3)


def best_pick_score(recipe: dict, user_profile: dict) -> float:
    """Score a recipe as a 'best pick': 60% nutrition-norm fit + 40% preference."""
    targets = calculate_nutrition_targets(user_profile)
    per_meal = {k: max(v / 3, 1) for k, v in targets.items()}

    def closeness(actual, target):
        return max(0.0, 1.0 - abs(actual - target) / target)

    nutrition = (
        closeness(recipe.get("calories", 0), per_meal["calories"]) * 0.4 +
        closeness(recipe.get("protein",   0), per_meal["protein"])  * 0.2 +
        closeness(recipe.get("carbs",     0), per_meal["carbs"])    * 0.2 +
        closeness(recipe.get("fat",       0), per_meal["fat"])      * 0.2
    )
    pref = min(recipe.get("_score", 1.0) / 2.0, 1.0)
    return round(0.6 * nutrition + 0.4 * pref, 4)


def rank_recipes(recipes: list[dict], user_profile: dict) -> list[dict]:
    from services.ml_ranking import build_taste_profile, ml_score

    disliked_ids = {d.get("id") for d in _load_db().get("dislikes", [])}
    recipes = [r for r in recipes if r.get("id") not in disliked_ids]

    liked    = get_liked_recipes()
    disliked = get_disliked_recipes()
    targets  = calculate_nutrition_targets(user_profile)
    taste_profile = build_taste_profile(liked, targets, disliked)

    if taste_profile is None:
        scored = sorted(recipes, key=lambda r: score_recipe(r, user_profile), reverse=True)
    else:
        ml_weight = min(0.4 + (len(liked) - 3) * 0.05, 0.8)

        def _combined(r):
            return (
                ml_weight * ml_score(r, taste_profile, targets)
                + (1 - ml_weight) * score_recipe(r, user_profile) / 2.0
            )

        scored = sorted(recipes, key=_combined, reverse=True)

    for r in scored:
        r["_score"] = score_recipe(r, user_profile)
    return scored
