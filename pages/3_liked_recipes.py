import streamlit as st
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.personalization import get_liked_recipes
from components.recipe_card import recipe_card

if not st.session_state.get("user_profile"):
    profile_path = Path(__file__).parent.parent / "profile.json"
    if profile_path.exists():
        with open(profile_path) as f:
            st.session_state.user_profile = json.load(f)

st.title("❤️ Liked Recipes")

liked = get_liked_recipes()

if not liked:
    st.info(
        "You haven't liked any recipes yet. "
        "Head to the Meal Plan and tap 🤍 on any recipe card to save it here."
    )
    st.page_link("pages/2_meal_plan.py", label="Go to Meal Plan →", icon="🍽️")
else:
    st.caption(f"{len(liked)} saved recipe{'s' if len(liked) != 1 else ''}")
    cols = st.columns(3)
    for i, recipe in enumerate(liked):
        with cols[i % 3]:
            recipe_card(recipe, "liked", f"liked_{i}_{recipe.get('id', i)}")
