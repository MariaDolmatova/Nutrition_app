import re
import streamlit as st
import plotly.graph_objects as go
from urllib.parse import quote
from services.groq_chain import generate_recipe_summary, summarize_instructions
from services.personalization import log_cooked, like_recipe, unlike_recipe, is_liked, dislike_recipe, is_disliked

_UNITS = {
    "tablespoon","tablespoons","teaspoon","teaspoons","cup","cups",
    "ounce","ounces","oz","pound","pounds","lb","lbs","gram","grams",
    "g","ml","liter","liters","pinch","pinches","slice","slices",
    "piece","pieces","can","cans","bunch", "chopped","clove","cloves","sprig",
    "sprigs","dash","handful","whole","large","small","medium",
    "fresh","raw","organic","pure","ground","unfiltered",
}
_FRACTIONS = set("½⅓¼¾⅔⅛⅕⅙⅞")


def _ingredient_name(line: str) -> str:
    line = re.sub(r'\([^)]*\)', '', line)  # drop (parentheticals)
    line = line.split(",")[0].strip()       # take before first comma
    tokens = line.split()
    while tokens and (tokens[0][0].isdigit() or tokens[0][0] in _FRACTIONS):
        tokens = tokens[1:]
    while tokens and tokens[0].lower() in _UNITS:
        tokens = tokens[1:]
    name = " ".join(tokens[:3]).strip()
    return name if name else line[:20]



def _fallback_image(name: str) -> str:
    return f"https://source.unsplash.com/200x200/?{quote(name)},food"


def _pill(text: str, color: str = "#4CAF50") -> str:
    return (
        f'<span style="background:{color};color:#fff;padding:2px 8px;'
        f'border-radius:20px;font-size:0.7rem;margin:2px 2px 0 0;'
        f'display:inline-block;font-weight:500;white-space:nowrap">{text}</span>'
    )


_HEALTH_DISPLAY = {
    "Vegan", "Vegetarian", "Gluten-Free", "Keto", "Paleo",
    "Mediterranean", "Low-Carb", "High-Protein", "Balanced",
}


def _diet_icon(diet_labels: list, health_labels: list = None) -> str:
    combined = " ".join((diet_labels or []) + (health_labels or [])).lower()
    if "vegan"          in combined: return "🌱"
    if "vegetarian"     in combined: return "🥦"
    if "keto"           in combined: return "🥑"
    if "paleo"          in combined: return "🍖"
    if "mediterranean"  in combined: return "🫒"
    return "🍽️"


def _visible_labels(recipe: dict) -> list:
    seen, labels = set(), []
    for lbl in recipe.get("diet_labels", []) + [
        h for h in recipe.get("health_labels", []) if h in _HEALTH_DISPLAY
    ]:
        if lbl not in seen:
            seen.add(lbl); labels.append(lbl)
        if len(labels) == 3:
            break
    return labels



def _nutrition_chart(protein: float, carbs: float, fat: float,
                     height: int = 100) -> go.Figure:
    labels = [f"Protein: {round(protein)}g", f"Carbs: {round(carbs)}g", f"Fat: {round(fat)}g"]
    values = [max(protein, 0.01), max(carbs, 0.01), max(fat, 0.01)]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.55,
        marker=dict(colors=["#4ADE80", "#60A5FA", "#FB923C"]),
        hovertemplate="%{label}<extra></extra>",
        textinfo="none",
    ))
    fig.update_layout(
        showlegend=False,
        margin=dict(l=0, r=0, t=0, b=10),
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def nutrition_chart_daily(protein: float, carbs: float, fat: float) -> go.Figure:
    """Larger chart with legend for the daily totals summary."""
    labels = [f"Protein {round(protein)}g", f"Carbs {round(carbs)}g", f"Fat {round(fat)}g"]
    values = [max(protein, 0.01), max(carbs, 0.01), max(fat, 0.01)]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.55,
        marker=dict(colors=["#7B1FA2", "#1565C0", "#E64A19"]),
        hovertemplate="%{label}<extra></extra>",
        textinfo="none",
    ))
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", xanchor="center", x=0.5, y=-0.15, font=dict(size=12)),
        margin=dict(l=10, r=10, t=10, b=70),
        height=480,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


@st.dialog("Recipe Details", width="large")
def recipe_modal(recipe: dict):
    # Constrain the large dialog to a medium width via CSS
    st.markdown(
        '<style>[data-testid="stModal"] > div { max-width: 460px !important; }</style>',
        unsafe_allow_html=True,
    )
    hide_cal    = (st.session_state.get("user_profile") or {}).get("hide_calories", False)
    name        = recipe["name"]
    image       = recipe.get("image") or _fallback_image(name)
    recipe_id   = recipe.get("id", "")
    diet_labels = recipe.get("diet_labels", [])

    st.subheader(name)

    top_left, top_right = st.columns([42, 58])

    with top_left:
        if hide_cal:
            st.metric("Protein",  f"{recipe.get('protein', 0)}g")
            st.metric("Carbs",    f"{recipe.get('carbs', 0)}g")
            st.metric("Fat",      f"{recipe.get('fat', 0)}g")
        else:
            st.metric("Calories", f"{recipe.get('calories', 0)} kcal")
            st.metric("Protein",  f"{recipe.get('protein', 0)}g")
            st.metric("Carbs",    f"{recipe.get('carbs', 0)}g")
            st.metric("Fat",      f"{recipe.get('fat', 0)}g")

        if recipe.get("total_time"):
            st.caption(f"⏱ Cook time: {recipe['total_time']} min")

    with top_right:
        st.markdown(
            f'<div style="display:flex;justify-content:flex-end;margin-top:-12px"><img src="{image}" style="width:92%;border-radius:8px;object-fit:cover;"/></div>',
            unsafe_allow_html=True,
        )

    visible = _visible_labels(recipe)
    if visible:
        st.markdown("".join(_pill(d, "#1565C0") for d in visible), unsafe_allow_html=True)

    st.markdown("### Ingredients")
    for line in recipe.get("ingredient_lines", []):
        st.caption(f"• {line}")

    st.markdown('<hr style="border:none;border-top:1px solid #2e7d32;width:70%;margin:8px 0"/>', unsafe_allow_html=True)

    st.markdown("### Instructions")
    instructions = recipe.get("instructions", "")
    if not instructions:
        with st.spinner("Generating instructions…"):
            instructions = summarize_instructions(name, recipe.get("ingredient_lines", []))
    st.write(instructions)

    if recipe.get("url") and recipe["url"] != "#":
        st.link_button("View Original Recipe", recipe["url"])

    if st.button("✅ I cooked this!", key=f"cooked_modal_{recipe_id}"):
        log_cooked(recipe_id, name, diet_labels)
        st.success("Logged! Great job cooking!")


def recipe_card(recipe: dict, meal_slot: str, card_key: str):
    if "emoji_btn_css" not in st.session_state:
        st.markdown("""
<style>
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] > div:nth-child(3) button,
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] > div:nth-child(4) button {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    font-size: 1.2rem !important;
    padding: 0.15rem 0.3rem !important;
    min-height: unset !important;
    width: auto !important;
}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] > div:nth-child(3) button:hover,
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] > div:nth-child(4) button:hover {
    background: rgba(0,0,0,0.06) !important;
    border-radius: 6px !important;
}
</style>""", unsafe_allow_html=True)
        st.session_state.emoji_btn_css = True

    hide_cal  = (st.session_state.get("user_profile") or {}).get("hide_calories", False)
    name      = recipe["name"]
    image     = recipe.get("image") or _fallback_image(name)
    recipe_id = recipe.get("id", card_key)
    liked     = is_liked(recipe_id)
    protein   = recipe.get("protein", 0)
    carbs     = recipe.get("carbs", 0)
    fat       = recipe.get("fat", 0)

    # AI summary — load or generate (no truncation for short text)
    if "recipe_summaries" not in st.session_state:
        st.session_state.recipe_summaries = {}
    summary_key = f"summary_{name}"
    if summary_key not in st.session_state.recipe_summaries:
        summary = generate_recipe_summary(name, recipe.get("diet_labels", []), recipe.get("calories", 0))
        st.session_state.recipe_summaries[summary_key] = summary
    else:
        summary = st.session_state.recipe_summaries[summary_key]

    ingr = recipe.get("ingredient_lines", [])
    icon = _diet_icon(recipe.get("diet_labels", []), recipe.get("health_labels", []))

    # Tag colors matching reference card style
    _label_colors = {
        "Balanced": "#F59E0B", "High-Fiber": "#A855F7", "High-Protein": "#6D28D9",
        "Vegan": "#16A34A", "Vegetarian": "#16A34A", "Keto": "#EF4444",
        "Mediterranean": "#3B82F6", "Paleo": "#92400E", "Gluten-Free": "#0EA5E9",
        "Low-Carb": "#DC2626", "Low-Sodium": "#0891B2",
    }

    with st.container(border=True):
        left, right = st.columns([65, 35])

        with left:
            # Large name with diet icon — matching reference heading style
            st.markdown(
                f'<p style="font-size:1.05rem;font-weight:500;margin:0 0 4px 0">'
                f'{icon}&nbsp;&nbsp;{name}</p>',
                unsafe_allow_html=True,
            )
            st.caption(summary)
            st.markdown('<hr style="border:none;border-top:1px solid #e0e0e0;width:40%;margin:6px 0"/>', unsafe_allow_html=True)
            if ingr:
                names = [_ingredient_name(i) for i in ingr if i.strip()]
                st.caption(" · ".join(names))
        with right:
            st.image(image, width='stretch')
            if protein + carbs + fat > 0:
                st.plotly_chart(
                    _nutrition_chart(protein, carbs, fat, height=100),
                    width='stretch',
                    config={"displayModeBar": False},
                    key=f"chart_{card_key}",
                    height=120,
                )

        # Bottom row: clock + time + diet pills + protein — full width
        bottom = []
        if recipe.get("total_time"):
            bottom.append(
                f'<span style="color:#555;font-size:0.85rem;margin-right:8px">'
                f'🕐 {int(recipe["total_time"])} min.</span>'
            )
        for dl in _visible_labels(recipe):
            bottom.append(_pill(dl, _label_colors.get(dl, "#6B7280")))
        if not hide_cal and protein:
            bottom.append(_pill(f"{int(protein)}g protein", "#6D28D9"))
        if bottom:
            st.markdown("".join(bottom), unsafe_allow_html=True)

        st.markdown('<div style="margin-top:6px"></div>', unsafe_allow_html=True)
        b1, b2, b3, b4 = st.columns([4, 4, 1, 1])
        with b1:
            if st.button("📖 Details", key=f"view_{card_key}", width='stretch'):
                recipe_modal(recipe)
        with b2:
            slot_list = (st.session_state.get("selected_meals") or {}).get(meal_slot, [])
            is_sel    = any(r.get("id") == recipe_id for r in slot_list)
            if st.button(
                "✓ Added" if is_sel else "Add",
                key=f"sel_{card_key}",
                width='stretch',
                type="secondary" if is_sel else "primary",
            ):
                meals = st.session_state.setdefault("selected_meals", {})
                current = meals.get(meal_slot, [])
                if is_sel:
                    meals[meal_slot] = [r for r in current if r.get("id") != recipe_id]
                else:
                    meals[meal_slot] = current + [recipe]
                st.rerun()
        with b3:
            heart = "❤️" if liked else "🤍"
            if st.button(heart, key=f"like_{card_key}"):
                unlike_recipe(recipe_id) if liked else like_recipe(recipe)
                st.rerun()
        with b4:
            if st.button("👎", key=f"dislike_{card_key}"):
                dislike_recipe(recipe)
                st.rerun()
