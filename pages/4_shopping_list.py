import re
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.personalization import get_liked_recipes

# ── Ingredient name parser (same logic as recipe_card._ingredient_name) ────────
_UNITS = {
    "tablespoon","tablespoons","teaspoon","teaspoons","cup","cups",
    "ounce","ounces","oz","pound","pounds","lb","lbs","gram","grams",
    "g","ml","liter","liters","pinch","pinches","slice","slices",
    "piece","pieces","can","cans","bunch","chopped","clove","cloves",
    "sprig","sprigs","dash","handful","whole","large","small","medium",
    "fresh","raw","organic","pure","ground","unfiltered",
}
_FRACTIONS = set("½⅓¼¾⅔⅛⅕⅙⅞")


def _parse_name(line: str) -> str:
    line = re.sub(r'\([^)]*\)', '', line)
    line = line.split(",")[0].strip()
    tokens = line.split()
    while tokens and (tokens[0][0].isdigit() or tokens[0][0] in _FRACTIONS):
        tokens = tokens[1:]
    while tokens and tokens[0].lower() in _UNITS:
        tokens = tokens[1:]
    name = " ".join(tokens).strip()
    return (name if name else line[:40]).lower()


def _in_fridge(fridge: list, ingredient: str) -> bool:
    """True if any fridge item covers this ingredient (substring + de-plural matching)."""
    ing = ingredient.lower()
    for item in fridge:
        it = item.lower()
        if it in ing or ing in it:
            return True
        # simple singular forms
        for suffix in ("es", "s"):
            if it.endswith(suffix) and it[:-len(suffix)] in ing:
                return True
    return False


# ── Page ───────────────────────────────────────────────────────────────────────
st.title("🛒 Shopping List")

profile = st.session_state.get("user_profile") or {}
fridge: list = profile.get("available_ingredients", [])
liked = get_liked_recipes()

if not liked:
    st.info("No liked recipes yet — heart a recipe on the Meal Plan page first.")
    st.stop()

# ── Recipe selector ────────────────────────────────────────────────────────────
recipe_names = [r["name"] for r in liked]
selected_names = st.multiselect(
    "Include recipes:",
    options=recipe_names,
    default=recipe_names,
    placeholder="Choose recipes…",
)
chosen = [r for r in liked if r["name"] in selected_names]

if not chosen:
    st.warning("Select at least one recipe above.")
    st.stop()

st.caption(f"Based on {len(chosen)} recipe{'s' if len(chosen) != 1 else ''}.")

# ── Build ingredient lists ─────────────────────────────────────────────────────
# to_buy: {parsed_name: {"raw": first seen raw line, "recipes": set of recipe names}}
to_buy: dict = {}
have: dict = {}

for recipe in chosen:
    for line in recipe.get("ingredient_lines", []):
        if not line.strip():
            continue
        name = _parse_name(line)
        if not name:
            continue
        target = have if _in_fridge(fridge, name) else to_buy
        if name not in target:
            target[name] = {"raw": line.strip(), "recipes": set()}
        target[name]["recipes"].add(recipe["name"])

# ── To buy section ─────────────────────────────────────────────────────────────
st.divider()

if to_buy:
    st.markdown(f"### 🧾 {len(to_buy)} items to buy")
    if not fridge:
        st.caption("Tip: add ingredients to My Fridge and they'll be ticked off automatically.")

    checked_keys = []
    for name, info in sorted(to_buy.items()):
        recipe_tags = ", ".join(sorted(info["recipes"]))
        label = f"**{name.title()}** — *{recipe_tags}*"
        if st.checkbox(label, key=f"buy_{name}"):
            checked_keys.append(name)
else:
    st.success("Your fridge already covers all ingredients in these recipes!")

# ── Already have section ───────────────────────────────────────────────────────
if have:
    with st.expander(f"✅ Already in your fridge ({len(have)} items)", expanded=False):
        for name in sorted(have):
            recipe_tags = ", ".join(sorted(have[name]["recipes"]))
            st.markdown(f"- ~~{name.title()}~~ — *{recipe_tags}*")

# ── Download ───────────────────────────────────────────────────────────────────
if to_buy:
    st.divider()
    lines = ["Shopping List\n", "=" * 30]
    for name, info in sorted(to_buy.items()):
        recipe_tags = ", ".join(sorted(info["recipes"]))
        lines.append(f"[ ] {name.title()}  ({recipe_tags})")
    lines += ["", "Already in fridge:", "-" * 20]
    for name in sorted(have):
        lines.append(f"[x] {name.title()}")

    st.download_button(
        "⬇️ Download shopping list",
        data="\n".join(lines),
        file_name="shopping_list.txt",
        mime="text/plain",
    )
