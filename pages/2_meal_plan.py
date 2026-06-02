import streamlit as st
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.edamam import search_recipes, COOK_TIME_MAP
from services.personalization import rank_recipes, best_pick_score, calculate_nutrition_targets
from components.meal_row import meal_row
from components.recipe_card import recipe_card, nutrition_chart_daily
from components.chat_assistant import chat_assistant
from components.profile_editor import profile_editor_dialog
from components.survey_dialog import survey_dialog

# ── Load / guard profile ───────────────────────────────────────────────────────
if not st.session_state.get("user_profile"):
    profile_path = Path(__file__).parent.parent / "profile.json"
    if profile_path.exists():
        with open(profile_path) as f:
            st.session_state.user_profile = json.load(f)

if not st.session_state.get("user_profile"):
    st.info("Welcome! Complete the quick survey to get your personalised meal plan.")
    survey_dialog()
    st.stop()

profile  = st.session_state.user_profile
hide_cal = profile.get("hide_calories", False)

if "recipe_page" not in st.session_state:
    st.session_state.recipe_page = 0

# ── CSS: horizontal scroll + uniform card size ─────────────────────────────────
st.markdown("""
<style>
/* ── Kill horizontal scroll everywhere by default ─────────────── */
[data-testid="stHorizontalBlock"] {
    overflow: hidden !important;
}

/* ── Only enable scroll on rows with 4+ cards (actual meal rows) ─
   Best Picks = 3 cols, summary = 2 cols → neither matches        */
[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(4)) {
    overflow-x: auto !important;
    flex-wrap: nowrap !important;
    -webkit-overflow-scrolling: touch;
    gap: 1rem;
    padding-bottom: 14px;
    scrollbar-width: thin;
    scrollbar-color: #ced4da transparent;
}
[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(4)) > div[data-testid="stColumn"] {
    flex: 0 0 480px !important;
}

/* ── All nested blocks: no scroll ─────────────────────────────── */
[data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] {
    overflow: hidden !important;
    flex-wrap: nowrap !important;
    gap: 0 !important;
    padding-bottom: 0 !important;
}
[data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
    min-width: 0 !important;
    max-width: none !important;
    flex: 1 1 auto !important;
}
/* Nested 4-col blocks (button rows, metrics) — specificity [0,4,1]
   beats outer :has rule [0,3,1] so this wins                       */
[data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(4)) {
    overflow: hidden !important;
    scrollbar-width: none !important;
    flex: 1 1 auto !important;
}
[data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(4)) > div[data-testid="stColumn"] {
    flex: 1 1 auto !important;
    min-width: 0 !important;
}

/* ── Card appearance ─────────────────────────────────────────── */
[data-testid="stHorizontalBlock"] [data-testid="stVerticalBlockBorderWrapper"] {
    min-height: 150px;
    height: 100%;
    background-color: #f3f4f6 !important;
    border-radius: 10px !important;
    border: 1px solid #e5e7eb !important;
}
[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(4)) [data-testid="stImage"] img {
    height: 150px !important;
    width: 100% !important;
    object-fit: cover !important;
    border-radius: 6px 6px 0 0;
}
[data-testid="stHorizontalBlock"] .stPlotlyChart {
    margin-top: 10px !important;
}
</style>
""", unsafe_allow_html=True)

_PAGE_SIZE = 8  # cards shown per "page" in each meal row

@st.cache_data(ttl=3600, show_spinner=False)
def fetch(slot, query, diets, ingr, max_t):
    return search_recipes(
        query=query, meal_type=slot, diet_labels=list(diets),
        ingredients=list(ingr), max_time=max_t, count=40,
    )


def _window(recipes: list, page: int) -> list:
    """Return a _PAGE_SIZE slice of recipes, wrapping around the ranked list."""
    if not recipes:
        return []
    n     = len(recipes)
    start = (page * _PAGE_SIZE) % n
    end   = start + _PAGE_SIZE
    return (recipes + recipes)[start:end]  # wrap-around via doubling


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 Filters")
    cook_time_filter = st.radio(
        "Cooking time", ["Up to 30 min", "Up to 1 hour", "Any"], index=2,
    )
    diet_filter = st.multiselect(
        "Diet labels",
        ["Vegan", "Vegetarian", "Gluten-free", "Keto", "Paleo", "Balanced"],
        default=profile.get("dietary_preferences", []),
    )
    ingredient_filter = st.text_input("Must include ingredient", placeholder="e.g. chicken")

    fridge_ingredients = profile.get("available_ingredients", [])
    use_fridge = False
    if fridge_ingredients:
        use_fridge = st.toggle(
            f"🥬 From my fridge only ({len(fridge_ingredients)} items)",
            value=False,
        )

    if st.button("Reset filters", width='stretch'):
        st.rerun()
    if st.button("🔄 New recipes", width='stretch'):
        st.session_state.recipe_page += 1
        st.rerun()
    if st.button("✕ Deselect all dishes", width='stretch'):
        st.session_state.selected_meals = {"breakfast": [], "lunch": [], "dinner": []}
        st.rerun()

    st.divider()
    st.markdown(f"**Goal:** {profile.get('goal', 'N/A')}")
    st.markdown(f"**Activity:** {profile.get('activity_level', 'N/A')}")
    if profile.get("dietary_preferences"):
        st.markdown(f"**Diet:** {', '.join(profile['dietary_preferences'])}")
    if st.button("✏️ Edit profile", width='stretch'):
        profile_editor_dialog()

# ── Build query ────────────────────────────────────────────────────────────────
max_minutes = COOK_TIME_MAP.get(cook_time_filter, (0, 9999))[1]

if use_fridge and fridge_ingredients:
    ingredients = fridge_ingredients[:5]
elif ingredient_filter:
    ingredients = [i.strip() for i in ingredient_filter.split(",") if i.strip()]
else:
    ingredients = []

goal_query = {
    "Lose weight":    "healthy low calorie",
    "Maintain weight": "balanced healthy",
    "Gain weight":    "high protein",
}.get(profile.get("goal", "Maintain weight"), "healthy")

_page = st.session_state.recipe_page

with st.spinner("Loading your personalised meal plan…"):
    br = fetch("breakfast", f"{goal_query} breakfast", tuple(diet_filter), tuple(ingredients), max_minutes)
    lu = fetch("lunch",     f"{goal_query} lunch",     tuple(diet_filter), tuple(ingredients), max_minutes)
    di = fetch("dinner",    f"{goal_query} dinner",    tuple(diet_filter), tuple(ingredients), max_minutes)

breakfast_ranked = rank_recipes(br, profile) if br else []
lunch_ranked     = rank_recipes(lu, profile) if lu else []
dinner_ranked    = rank_recipes(di, profile) if di else []
all_recipes      = breakfast_ranked + lunch_ranked + dinner_ranked

breakfast_page = _window(breakfast_ranked, _page)
lunch_page     = _window(lunch_ranked,     _page)
dinner_page    = _window(dinner_ranked,    _page)

# ── Header ─────────────────────────────────────────────────────────────────────
st.title("🍽️ Your Meal Plan")

# ── Best picks — ranked by nutrition-norm fit (60%) + preference (40%) ─────────
st.subheader("⭐ Best Picks for You")
bp1, bp2, bp3 = st.columns(3)
for slot, ranked, col in [
    ("breakfast", breakfast_ranked, bp1),
    ("lunch",     lunch_ranked,     bp2),
    ("dinner",    dinner_ranked,    bp3),
]:
    with col:
        if ranked:
            best = max(ranked, key=lambda r: best_pick_score(r, profile))
            st.markdown(f"**{slot.title()} Pick**")
            recipe_card(best, slot, f"best_{slot}")
        else:
            st.info(f"No {slot} pick available.")

st.divider()

# ── Meal rows ──────────────────────────────────────────────────────────────────
meal_row("breakfast", breakfast_page)
meal_row("lunch",     lunch_page)
meal_row("dinner",    dinner_page)

# ── Today's Selections ─────────────────────────────────────────────────────────
st.subheader("📋 Today's Selections")
selected    = st.session_state.get("selected_meals", {})
total_cal   = 0
total_prot  = 0.0
total_carbs = 0.0
total_fat   = 0.0

SLOT_ICON = {"breakfast": "🌅", "lunch": "☀️", "dinner": "🌙"}

summary_cols = st.columns(3)
for i, slot in enumerate(["breakfast", "lunch", "dinner"]):
    slot_recipes = selected.get(slot, [])
    with summary_cols[i]:
        icon = SLOT_ICON[slot]
        st.markdown(f"**{icon} {slot.title()}**")
        if slot_recipes:
            for r in slot_recipes:
                name = r["name"]
                st.write(name if len(name) <= 38 else name[:36] + "…")
                if not hide_cal:
                    st.caption(f"{r.get('calories', 0)} kcal · "
                               f"{round(r.get('protein',0))}g P · "
                               f"{round(r.get('carbs',0))}g C · "
                               f"{round(r.get('fat',0))}g F")
                total_cal   += r.get("calories", 0)
                total_prot  += r.get("protein", 0)
                total_carbs += r.get("carbs", 0)
                total_fat   += r.get("fat", 0)
        else:
            st.caption("_Not selected yet_")

# ── Totals + donut  ────────────────────────────────────────────────────────────
metric_col, chart_col = st.columns([3, 2])
with metric_col:
    m_cols = st.columns(4 if not hide_cal else 3)
    if not hide_cal:
        m_cols[0].metric("Calories",  f"{round(total_cal)} kcal")
    m_cols[-3].metric("Protein",  f"{round(total_prot)}g")
    m_cols[-2].metric("Carbs",    f"{round(total_carbs)}g")
    m_cols[-1].metric("Fat",      f"{round(total_fat)}g")

    # Nutrition norm comparison
    targets = calculate_nutrition_targets(profile)

    def _norm_pill(label, actual, target, unit):
        color = "#16a34a" if actual >= target else "#dc2626"
        return (
            f'<span style="margin-right:16px">'
            f'<span style="font-size:0.78rem;color:#666">{label} </span>'
            f'<span style="color:{color};font-weight:600">{round(actual)}{unit}</span>'
            f'<span style="font-size:0.72rem;color:#999">/{target}{unit}</span>'
            f'</span>'
        )

    pills = ""
    if not hide_cal:
        pills += _norm_pill("Cal", total_cal, targets["calories"], "kcal")
    pills += _norm_pill("P", total_prot,  targets["protein"], "g")
    pills += _norm_pill("C", total_carbs, targets["carbs"],   "g")
    pills += _norm_pill("F", total_fat,   targets["fat"],     "g")
    st.markdown(f'<div style="margin-top:8px">{pills}</div>', unsafe_allow_html=True)

    # ── Coverage message ──────────────────────────────────────────────────────
    checks = [
        (total_prot,  targets["protein"]),
        (total_carbs, targets["carbs"]),
        (total_fat,   targets["fat"]),
    ]
    if not hide_cal:
        checks.insert(0, (total_cal, targets["calories"]))

    pct_more = [
        max(0.0, (target - actual) / max(actual, 1) * 100)
        for actual, target in checks
    ]
    avg_more = round(sum(pct_more) / len(pct_more))

    st.markdown("")
    if avg_more == 0:
        st.success("Well done! The norm is covered for today :)")
    else:
        st.warning(
            f"Daily norm not covered. Please add another dish or try to eat "
            f"**{avg_more}% more** on average of each serving."
        )

with chart_col:
    if total_prot + total_carbs + total_fat > 0:
        st.plotly_chart(
            nutrition_chart_daily(total_prot, total_carbs, total_fat),
            width='stretch',
            height=480,
            config={"displayModeBar": False},
            key="daily_nutrition_chart",
        )
    else:
        st.caption("_Pick meals above to see your daily nutrition breakdown_")

# ── Chat ───────────────────────────────────────────────────────────────────────
chat_assistant(profile, all_recipes[:12])
