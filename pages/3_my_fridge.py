import streamlit as st
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from components.survey_dialog import INGREDIENT_CATEGORIES

PROFILE_PATH = Path(__file__).parent.parent / "profile.json"

# ── Load profile ───────────────────────────────────────────────────────────────
if not st.session_state.get("user_profile"):
    if PROFILE_PATH.exists():
        with open(PROFILE_PATH) as f:
            st.session_state.user_profile = json.load(f)

profile = st.session_state.get("user_profile") or {}
current = set(profile.get("available_ingredients", []))

st.title("🥬 My Fridge")
st.caption("Keep your ingredient list up to date — recipes can be filtered to match what you have.")

# ── Summary pills ──────────────────────────────────────────────────────────────
if current:
    pills = "".join(
        f'<span style="background:#e8f5e9;color:#2e7d32;padding:3px 10px;'
        f'border-radius:20px;font-size:0.78rem;margin:2px;display:inline-block">'
        f'{i}</span>'
        for i in sorted(current)
    )
    st.markdown(f"**{len(current)} ingredients:** {pills}", unsafe_allow_html=True)
    st.divider()
else:
    st.info("Your fridge is empty. Select ingredients below.")

# ── Category pickers ───────────────────────────────────────────────────────────
for cat, items in INGREDIENT_CATEGORIES.items():
    prev = [i for i in items if i in current]
    with st.expander(f"{cat}  ·  {len(prev)} selected", expanded=bool(prev)):
        st.multiselect(
            "Select ingredients:",
            items,
            default=prev,
            key=f"fridge_{cat}",
            label_visibility="collapsed",
        )

st.divider()

# ── Save / Clear ────────────────────────────────────────────────────────────────
col_save, col_clear, _ = st.columns([1, 1, 3])

if col_save.button("💾 Save changes", type="primary", width='stretch'):
    all_ingredients = []
    for cat in INGREDIENT_CATEGORIES:
        all_ingredients.extend(st.session_state.get(f"fridge_{cat}", []))
    profile["available_ingredients"] = all_ingredients
    with open(PROFILE_PATH, "w") as f:
        json.dump(profile, f, indent=2)
    st.session_state.user_profile = profile
    st.success(f"Fridge updated — {len(all_ingredients)} ingredients saved!")
    st.rerun()

if col_clear.button("🗑 Clear all", width='stretch'):
    for cat in INGREDIENT_CATEGORIES:
        st.session_state[f"fridge_{cat}"] = []
    profile["available_ingredients"] = []
    with open(PROFILE_PATH, "w") as f:
        json.dump(profile, f, indent=2)
    st.session_state.user_profile = profile
    st.rerun()
