import streamlit as st
import json
from pathlib import Path
from services.personalization import calculate_nutrition_targets

PROFILE_PATH = Path(__file__).parent.parent / "profile.json"

_GOALS  = ["Lose weight", "Maintain weight", "Gain weight"]
_ACTS   = ["Sedentary", "Light", "Moderate", "Very active"]
_TIMES  = ["Up to 30 min", "Up to 1 hour", "No limit"]
_DIETS  = ["Anything", "Keto", "Mediterranean", "Paleo", "Vegan", "Vegetarian"]
_DIET_ID = {"Anything": "none", "Keto": "keto", "Mediterranean": "mediterranean",
             "Paleo": "paleo", "Vegan": "vegan", "Vegetarian": "vegetarian"}
_DIET_PREFS = {"none": [], "keto": ["Keto"], "mediterranean": ["Mediterranean"],
               "paleo": ["Paleo"], "vegan": ["Vegan"], "vegetarian": ["Vegetarian"]}
_DIET_LABEL = {v: k for k, v in _DIET_ID.items()}


@st.dialog("Edit Profile", width="large")
def profile_editor_dialog():
    p = st.session_state.user_profile.copy()

    st.subheader("Basic info")
    c1, c2 = st.columns(2)
    with c1:
        age    = st.number_input("Age", 10, 120, value=int(p.get("age", 25)))
        weight = st.number_input("Weight (kg)", 20.0, 300.0,
                                 value=float(p.get("weight", 70)), step=0.5)
    with c2:
        height = st.number_input("Height (cm)", 100.0, 250.0,
                                 value=float(p.get("height", 170)), step=0.5)
        gender_opts = ["Male", "Female", "Non-binary / prefer not to say"]
        gender = st.selectbox("Gender", gender_opts,
                              index=gender_opts.index(p.get("gender", "Male")))

    st.subheader("Goals")
    activity  = st.selectbox("Activity level", _ACTS,
                              index=_ACTS.index(p.get("activity_level", "Moderate")))
    goal      = st.radio("Primary goal", _GOALS, horizontal=True,
                          index=_GOALS.index(p.get("goal", "Maintain weight")))
    cook_time = st.radio("Max cooking time", _TIMES, horizontal=True,
                          index=_TIMES.index(p.get("max_cook_time", "No limit")))

    st.subheader("Diet & preferences")
    current_diet_label = _DIET_LABEL.get(p.get("diet_id", "none"), "Anything")
    diet_choice = st.selectbox("Diet preference", _DIETS,
                                index=_DIETS.index(current_diet_label))
    hide_cal = st.checkbox("Hide calorie information",
                            value=p.get("hide_calories", False),
                            help="Hides calorie counts throughout the app.")

    st.divider()
    cs, cc = st.columns(2)
    if cs.button("Cancel", width='stretch'):
        st.rerun()
    if cc.button("Save changes", width='stretch', type="primary"):
        new_diet_id = _DIET_ID[diet_choice]
        updated = {
            **p,
            "age": age, "weight": weight, "height": height, "gender": gender,
            "activity_level": activity, "goal": goal, "max_cook_time": cook_time,
            "diet_id": new_diet_id,
            "dietary_preferences": _DIET_PREFS[new_diet_id],
            "hide_calories": hide_cal,
        }
        with open(PROFILE_PATH, "w") as f:
            json.dump(updated, f, indent=2)
        st.session_state.user_profile = updated
        st.session_state.nutrition_targets = calculate_nutrition_targets(updated)
        st.success("Profile updated!")
        st.rerun()
