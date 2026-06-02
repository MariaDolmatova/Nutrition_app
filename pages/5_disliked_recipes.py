import streamlit as st
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.personalization import get_disliked_recipes, undislike_recipe

if not st.session_state.get("user_profile"):
    profile_path = Path(__file__).parent.parent / "profile.json"
    if profile_path.exists():
        with open(profile_path) as f:
            st.session_state.user_profile = json.load(f)

st.title("👎 Disliked Recipes")
st.caption("These recipes are hidden from your meal plan and influence your recommendations negatively.")

disliked = get_disliked_recipes()

if not disliked:
    st.info("No disliked recipes yet.")
    st.page_link("pages/2_meal_plan.py", label="Go to Meal Plan →", icon="🍽️")
else:
    st.caption(f"{len(disliked)} recipe{'s' if len(disliked) != 1 else ''}")
    cols = st.columns(3)
    for i, recipe in enumerate(disliked):
        with cols[i % 3]:
            with st.container(border=True):
                name      = recipe.get("name", "Unknown")
                image     = recipe.get("image", "")
                recipe_id = recipe.get("id", str(i))

                if image:
                    st.image(image, width='stretch')
                st.markdown(f"**{name}**")
                if recipe.get("calories"):
                    st.caption(f"{recipe['calories']} kcal")
                if st.button("↩️ Remove from disliked", key=f"undislike_{recipe_id}", width='stretch'):
                    undislike_recipe(recipe_id)
                    st.rerun()
