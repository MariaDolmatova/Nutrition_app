import streamlit as st
import json
from pathlib import Path
from services.personalization import calculate_nutrition_targets

PROFILE_PATH = Path(__file__).parent.parent / "profile.json"

DIET_OPTIONS = [
    {"id": "none",          "label": "Anything",      "icon": "🍽️"},
    {"id": "keto",          "label": "Keto",           "icon": "🥑"},
    {"id": "mediterranean", "label": "Mediterranean",  "icon": "🫒"},
    {"id": "paleo",         "label": "Paleo",          "icon": "🍖"},
    {"id": "vegan",         "label": "Vegan",          "icon": "🌱"},
    {"id": "vegetarian",    "label": "Vegetarian",     "icon": "🥦"},
]

DIET_TO_PREFS = {
    "none": [], "keto": ["Keto"], "mediterranean": ["Mediterranean"],
    "paleo": ["Paleo"], "vegan": ["Vegan"], "vegetarian": ["Vegetarian"],
}

INGREDIENT_CATEGORIES = {
    "🥬 Vegetables":    ["Tomatoes", "Spinach", "Carrots", "Broccoli", "Bell peppers",
                         "Onions", "Garlic", "Zucchini", "Cucumber", "Lettuce",
                         "Mushrooms", "Potatoes", "Sweet potato", "Eggplant",
                         "Kale", "Celery", "Cauliflower", "Asparagus", "Leek",
                         "Corn", "Brussels sprouts", "Scallions", "Jalapeño",
                         "Pumpkin", "Radish", "Artichoke", "Bok choy", "Beets"],
    "🍖 Meat":          ["Chicken breast", "Ground beef", "Pork chops", "Lamb",
                         "Turkey", "Bacon", "Sausage", "Beef steak",
                         "Chicken thighs", "Chicken wings", "Ground turkey",
                         "Ground pork", "Veal", "Duck", "Prosciutto", "Pepperoni",
                         "Deli meat", "Beef ribs", "Pork belly"],
    "🐟 Fish & Seafood": ["Salmon", "Tuna", "Shrimp", "Cod", "Tilapia", "Sardines", "Crab",
                          "Lobster", "Scallops", "Mussels", "Clams", "Halibut",
                          "Sea bass", "Mackerel", "Anchovies", "Squid", "Octopus"],
    "🥛 Dairy & Eggs":  ["Milk", "Cheese", "Yogurt", "Butter", "Cream",
                         "Eggs", "Mozzarella", "Parmesan",
                         "Greek yogurt", "Sour cream", "Ricotta", "Feta",
                         "Cheddar", "Gouda", "Brie", "Heavy cream",
                         "Almond milk", "Oat milk", "Coconut milk"],
    "🌾 Grains":        ["Rice", "Pasta", "Bread", "Oats", "Quinoa",
                         "Couscous", "Tortillas", "Flour",
                         "Brown rice", "Barley", "Farro", "Buckwheat",
                         "Polenta", "Noodles", "Pita bread", "Whole wheat bread",
                         "Breadcrumbs", "Cornmeal", "Rye bread"],
    "🫘 Legumes":       ["Lentils", "Chickpeas", "Black beans", "Kidney beans",
                         "Tofu", "Edamame", "Peas",
                         "Cannellini beans", "Butter beans", "Navy beans",
                         "Split peas", "Tempeh", "Mung beans", "Pinto beans"],
    "🍎 Fruits":        ["Bananas", "Apples", "Berries", "Avocado",
                         "Lemon", "Oranges", "Mango", "Grapes",
                         "Strawberries", "Blueberries", "Raspberries",
                         "Pineapple", "Peaches", "Pears", "Cherries",
                         "Watermelon", "Kiwi", "Pomegranate", "Dates",
                         "Figs", "Plums", "Lime", "Grapefruit"],
    "🫙 Pantry":        ["Olive oil", "Salt", "Black pepper", "Soy sauce",
                         "Honey", "Vinegar", "Canned tomatoes", "Vegetable broth",
                         "Coconut oil", "Sesame oil", "Chicken broth", "Beef broth",
                         "Tomato paste", "Fish sauce", "Worcestershire sauce",
                         "Hot sauce", "Mustard", "Mayonnaise", "Ketchup",
                         "Balsamic vinegar", "Red wine vinegar", "Oyster sauce",
                         "Hoisin sauce", "Tahini", "Peanut butter", "Almond butter",
                         "Maple syrup", "Sugar", "Brown sugar", "Baking powder",
                         "Baking soda", "Vanilla extract", "Cocoa powder",
                         "Breadcrumbs", "Nutritional yeast"],
    "🌿 Herbs & Spices": ["Basil", "Parsley", "Cilantro", "Thyme", "Rosemary",
                          "Oregano", "Mint", "Dill", "Bay leaves",
                          "Cumin", "Paprika", "Turmeric", "Chili powder",
                          "Cinnamon", "Garlic powder", "Onion powder",
                          "Chili flakes", "Curry powder", "Coriander",
                          "Ginger", "Cardamom", "Cloves", "Nutmeg",
                          "Star anise", "Smoked paprika", "Cayenne pepper"],
}

FAVOURITE_DISHES = [
    "Spaghetti Bolognese", "Chicken Caesar Salad", "Avocado Toast",
    "Grilled Salmon", "Vegetable Stir Fry", "Beef Tacos",
    "Greek Salad", "Chicken Tikka Masala", "Overnight Oats",
    "Mushroom Risotto", "Lentil Soup", "Banana Pancakes",
    "Shrimp Fried Rice", "Turkey Sandwich", "Quinoa Buddha Bowl",
    "French Omelette", "BBQ Chicken Wings", "Veggie Burger",
    "Tomato Basil Pasta", "Smoothie Bowl",
]


def _save_profile(profile: dict):
    with open(PROFILE_PATH, "w") as f:
        json.dump(profile, f, indent=2)
    st.session_state.user_profile = profile


@st.dialog("Let's set up your profile", width="large")
def survey_dialog():
    step = st.session_state.get("survey_step", 1)
    total = 5
    st.progress(step / total)
    st.caption(f"Step {step} of {total}")
    data = st.session_state.get("survey_data", {})

    # ── Step 1: Sensitivity + basic info ──────────────────────────────────────
    if step == 1:
        st.subheader("About you")
        hide_cal = st.checkbox(
            "I'd prefer not to see calorie counts",
            value=data.get("hide_calories", False),
            help="We respect eating-disorder sensitivity — calorie info will be hidden throughout the app.",
        )
        c1, c2 = st.columns(2)
        with c1:
            age    = st.number_input("Age", 10, 120, value=int(data.get("age", 25)))
            weight = st.number_input("Weight (kg)", 20.0, 300.0,
                                     value=float(data.get("weight", 70)), step=0.5)
        with c2:
            height = st.number_input("Height (cm)", 100.0, 250.0,
                                     value=float(data.get("height", 170)), step=0.5)
            gender = st.selectbox(
                "Gender",
                ["Male", "Female", "Non-binary / prefer not to say"],
                index=["Male", "Female", "Non-binary / prefer not to say"]
                      .index(data.get("gender", "Male")),
            )
        if st.button("Next →", width='stretch', type="primary"):
            st.session_state.survey_data = {
                **data, "hide_calories": hide_cal,
                "age": age, "weight": weight, "height": height, "gender": gender,
            }
            st.session_state.survey_step = 2
            st.rerun()

    # ── Step 2: Goals & timing ─────────────────────────────────────────────────
    elif step == 2:
        st.subheader("Your goals")
        _goals    = ["Lose weight", "Maintain weight", "Gain weight"]
        _acts     = ["Sedentary", "Light", "Moderate", "Very active"]
        _times    = ["Up to 30 min", "Up to 1 hour", "No limit"]
        activity  = st.selectbox("Activity level", _acts,
                                 index=_acts.index(data.get("activity_level", "Moderate")))
        goal      = st.radio("Primary goal", _goals,
                             index=_goals.index(data.get("goal", "Maintain weight")))
        cook_time = st.radio("Max cooking time per meal", _times,
                             index=_times.index(data.get("max_cook_time", "No limit")))
        cb, cn = st.columns(2)
        if cb.button("← Back", width='stretch'):
            st.session_state.survey_step = 1; st.rerun()
        if cn.button("Next →", width='stretch', type="primary"):
            st.session_state.survey_data = {
                **data, "activity_level": activity,
                "goal": goal, "max_cook_time": cook_time,
            }
            st.session_state.survey_step = 3; st.rerun()

    # ── Step 3: Diet icons ─────────────────────────────────────────────────────
    elif step == 3:
        st.subheader("Preferred Diet")
        current = st.session_state.get("survey_diet_id", data.get("diet_id", "none"))

        cols = st.columns(len(DIET_OPTIONS))
        for opt, col in zip(DIET_OPTIONS, cols):
            with col:
                selected = current == opt["id"]
                border = "#FF6B35" if selected else "#dee2e6"
                bg     = "#fff5f2" if selected else "#ffffff"
                st.markdown(
                    f"""<div style="border:2px solid {border};border-radius:14px;
                        padding:14px 6px;text-align:center;background:{bg};
                        margin-bottom:6px;cursor:pointer;">
                        <div style="font-size:1.9rem">{opt['icon']}</div>
                        <div style="font-size:0.8rem;font-weight:600;margin-top:4px">
                            {opt['label']}</div></div>""",
                    unsafe_allow_html=True,
                )
                if st.button(
                    "✓" if selected else "Select",
                    key=f"diet_btn_{opt['id']}",
                    width='stretch',
                    type="primary" if selected else "secondary",
                ):
                    st.session_state.survey_diet_id = opt["id"]
                    st.rerun()

        cb, cn = st.columns(2)
        if cb.button("← Back", key="s3b", width='stretch'):
            st.session_state.survey_step = 2; st.rerun()
        if cn.button("Next →", key="s3n", width='stretch', type="primary"):
            diet_id = st.session_state.get("survey_diet_id", "none")
            st.session_state.survey_data = {
                **data,
                "diet_id": diet_id,
                "dietary_preferences": DIET_TO_PREFS.get(diet_id, []),
            }
            st.session_state.survey_step = 4; st.rerun()

    # ── Step 4: Ingredients by category ───────────────────────────────────────
    elif step == 4:
        st.subheader("What's in your kitchen?")
        st.caption("Select ingredients you currently have — we'll prioritise matching recipes.")

        for cat, items in INGREDIENT_CATEGORIES.items():
            prev = [i for i in data.get("available_ingredients", []) if i in items]
            with st.expander(cat):
                st.multiselect(
                    "Select:", items, default=prev,
                    key=f"ingr_{cat}", label_visibility="collapsed",
                )

        cb, cn = st.columns(2)
        if cb.button("← Back", key="s4b", width='stretch'):
            st.session_state.survey_step = 3; st.rerun()
        if cn.button("Next →", key="s4n", width='stretch', type="primary"):
            all_ingr = []
            for cat in INGREDIENT_CATEGORIES:
                all_ingr.extend(st.session_state.get(f"ingr_{cat}", []))
            st.session_state.survey_data = {**data, "available_ingredients": all_ingr}
            st.session_state.survey_step = 5; st.rerun()

    # ── Step 5: Favourites + completion ───────────────────────────────────────
    elif step == 5:
        st.subheader("Favourite dishes")
        prev_favs = [f for f in data.get("favourite_dishes", []) if f in FAVOURITE_DISHES]
        favourites = st.multiselect(
            "Pick 3–5 dishes you love",
            FAVOURITE_DISHES,
            default=prev_favs,
            max_selections=5,
        )
        cb, cf = st.columns(2)
        if cb.button("← Back", key="s5b", width='stretch'):
            st.session_state.survey_step = 4; st.rerun()
        if cf.button("Finish ✓", key="s5f", width='stretch', type="primary"):
            if len(favourites) < 3:
                st.warning("Please pick at least 3 favourite dishes.")
            else:
                final = {**data, "favourite_dishes": favourites}
                _save_profile(final)
                targets = calculate_nutrition_targets(final)
                st.session_state.nutrition_targets = targets
                st.session_state.show_nutrition_summary = True
                st.session_state.survey_step = 1
                st.session_state.survey_data = {}
                st.rerun()
