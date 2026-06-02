import streamlit as st
import json
from pathlib import Path

st.set_page_config(
    page_title="Nutrition & Meal Planner",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded",
)

PROFILE_PATH = Path(__file__).parent / "profile.json"


def _load_profile():
    if PROFILE_PATH.exists():
        try:
            with open(PROFILE_PATH) as f:
                return json.load(f)
        except Exception:
            return None
    return None


# Bootstrap session state — runs on every page navigation
if "user_profile" not in st.session_state:
    st.session_state.user_profile = _load_profile()

for _key, _default in [
    ("chat_history", []),
    ("selected_meals", {"breakfast": [], "lunch": [], "dinner": []}),
    ("recipe_summaries", {}),
    ("survey_step", 1),
    ("survey_data", {}),
    ("show_nutrition_summary", False),
]:
    if _key not in st.session_state:
        st.session_state[_key] = _default

# st.navigation replaces Streamlit's auto-sidebar — no "App" entry appears
pg = st.navigation([
    st.Page("pages/2_meal_plan.py",       title="Meal Plan",         icon="🍽️", default=True),
    st.Page("pages/3_my_fridge.py",       title="My Fridge",         icon="🥬"),
    st.Page("pages/3_liked_recipes.py",   title="Liked Recipes",     icon="❤️"),
    st.Page("pages/4_shopping_list.py",   title="Shopping List",     icon="🛒"),
    st.Page("pages/5_disliked_recipes.py",title="Disliked Recipes",  icon="👎"),
])
pg.run()
