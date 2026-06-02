from typing import Optional
import numpy as np

# Diet/health flags used as binary features in the recipe vector
_DIET_FLAGS = [
    "vegan", "vegetarian", "keto", "paleo",
    "high-protein", "low-carb", "gluten-free", "balanced",
]


def _feature_vector(recipe: dict, targets: dict) -> np.ndarray:
    """13-dimensional feature vector: 5 nutritional ratios + 8 diet flags."""
    cal_t  = max(targets.get("calories", 500), 1)
    prot_t = max(targets.get("protein",   50),  1)
    carb_t = max(targets.get("carbs",    200),  1)
    fat_t  = max(targets.get("fat",       55),  1)

    features = [
        min(recipe.get("calories",   0) / cal_t,  3.0),
        min(recipe.get("protein",    0) / prot_t, 3.0),
        min(recipe.get("carbs",      0) / carb_t, 3.0),
        min(recipe.get("fat",        0) / fat_t,  3.0),
        min(recipe.get("total_time", 30), 120) / 120.0,
    ]
    combined = " ".join(
        recipe.get("diet_labels", []) + recipe.get("health_labels", [])
    ).lower()
    for flag in _DIET_FLAGS:
        features.append(1.0 if flag in combined else 0.0)

    return np.array(features, dtype=float)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def build_taste_profile(
    liked_recipes: list,
    targets: dict,
    disliked_recipes: Optional[list] = None,
) -> Optional[np.ndarray]:
    """Mean liked vector minus a scaled dislike vector. Returns None on cold start (< 3 likes)."""
    if len(liked_recipes) < 3:
        return None
    profile = np.mean([_feature_vector(r, targets) for r in liked_recipes], axis=0)
    if disliked_recipes:
        dislike_mean = np.mean([_feature_vector(r, targets) for r in disliked_recipes], axis=0)
        profile = profile - 0.3 * dislike_mean
    return profile


def ml_score(recipe: dict, taste_profile: np.ndarray, targets: dict) -> float:
    """Cosine similarity between this recipe and the user's taste profile."""
    return _cosine(_feature_vector(recipe, targets), taste_profile)
