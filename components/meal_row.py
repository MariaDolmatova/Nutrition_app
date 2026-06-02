import streamlit as st
from components.recipe_card import recipe_card
from services.personalization import get_disliked_recipes

SLOT_ICON = {"breakfast": "🌅", "lunch": "☀️", "dinner": "🌙"}


def meal_row(meal_slot: str, recipes: list[dict]):
    disliked_ids = {r.get("id") for r in get_disliked_recipes()}
    recipes = [r for r in recipes if r.get("id") not in disliked_ids]
    icon     = SLOT_ICON.get(meal_slot, "🍽️")
    label    = meal_slot.title()
    selected_list = (st.session_state.get("selected_meals") or {}).get(meal_slot, [])
    hcol, bcol = st.columns([5, 2])
    with hcol:
        st.subheader(f"{icon} {label}")
    with bcol:
        if selected_list:
            first = selected_list[0]["name"]
            badge = (first[:18] + "…") if len(first) > 18 else first
            if len(selected_list) > 1:
                badge += f" +{len(selected_list) - 1}"
            st.success(f"✓ {badge}")

    if not recipes:
        st.info(f"No {label.lower()} recipes found — try adjusting the filters.")
        st.divider()
        return

    # Render all cards in one wide st.columns row — CSS makes it scroll
    cols = st.columns(len(recipes))
    for i, (col, recipe) in enumerate(zip(cols, recipes)):
        with col:
            recipe_card(recipe, meal_slot, f"{meal_slot}_{i}_{recipe.get('id', i)}")

    st.divider()
