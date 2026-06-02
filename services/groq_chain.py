import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
_groq_client = None


def _get_client():
    global _groq_client
    if _groq_client is None:
        if not GROQ_API_KEY:
            return None
        try:
            from groq import Groq
            _groq_client = Groq(api_key=GROQ_API_KEY)
        except ImportError:
            st.error("groq package not installed. Run: pip install groq")
            return None
    return _groq_client


def generate_recipe_summary(recipe_name: str, diet_labels: list[str], calories: int) -> str:
    """One-line AI summary for a recipe card."""
    cache_key = f"summary_{recipe_name}"
    if cache_key in st.session_state.get("recipe_summaries", {}):
        return st.session_state["recipe_summaries"][cache_key]

    client = _get_client()
    if client is None:
        summary = f"A delicious {recipe_name.lower()} recipe."
        _cache_summary(cache_key, summary)
        return summary

    try:
        prompt = (
            f"Write a single enticing sentence (max 15 words) describing this recipe: "
            f"{recipe_name}. Diet: {', '.join(diet_labels) or 'balanced'}. Calories: {calories}."
        )
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=40,
            temperature=0.7,
        )
        summary = resp.choices[0].message.content.strip().strip('"')
    except Exception:
        summary = f"A delicious {recipe_name.lower()} recipe."

    _cache_summary(cache_key, summary)
    return summary


def _cache_summary(key: str, value: str):
    if "recipe_summaries" not in st.session_state:
        st.session_state["recipe_summaries"] = {}
    st.session_state["recipe_summaries"][key] = value


def summarize_instructions(recipe_name: str, ingredient_lines: list[str]) -> str:
    """Generate step-by-step instructions when Edamam doesn't provide them."""
    client = _get_client()
    if client is None:
        return "Instructions not available. Please visit the original recipe link."

    try:
        ingredients_text = "\n".join(ingredient_lines[:10])
        prompt = (
            f"Write ONLY the cooking steps (4-6 numbered steps) for: {recipe_name}.\n"
            f"Ingredients available: {ingredients_text}\n"
            f"Do NOT list the ingredients again. Start directly with step 1. Be concise."
        )
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.5,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Instructions unavailable. Visit the original recipe link. ({e})"


def build_chat_chain(user_profile: dict, current_recipes: list[dict]):
    """Return a callable chat function with full context."""
    client = _get_client()

    recipe_names = [r["name"] for r in current_recipes]
    recipe_summaries = [
        st.session_state.get("recipe_summaries", {}).get(f"summary_{r['name']}", r["name"])
        for r in current_recipes
    ]
    recipes_context = "\n".join(
        f"- {name}: {summary}" for name, summary in zip(recipe_names, recipe_summaries)
    )

    system_prompt = f"""You are a friendly nutrition and meal planning assistant.

User profile:
- Age: {user_profile.get('age', 'N/A')}, Gender: {user_profile.get('gender', 'N/A')}
- Weight: {user_profile.get('weight', 'N/A')} kg
- Activity level: {user_profile.get('activity_level', 'N/A')}
- Goal: {user_profile.get('goal', 'N/A')}
- Dietary preferences: {', '.join(user_profile.get('dietary_preferences', [])) or 'None'}
- Available ingredients: {', '.join(user_profile.get('available_ingredients', [])) or 'Not specified'}

Current meal plan recipes:
{recipes_context}

Guidelines:
- Answer nutrition, cooking, and meal planning questions helpfully.
- If asked about specific recipes in the plan, refer to them by name.
- If asked something unrelated to food/nutrition/health, politely redirect.
- Be concise and friendly.
"""

    def chat(history: list[dict], user_message: str) -> str:
        if client is None:
            return "Chat unavailable — please add your GROQ_API_KEY to the .env file."

        messages = [{"role": "system", "content": system_prompt}]
        for turn in history[-10:]:
            messages.append({"role": turn["role"], "content": turn["content"]})
        messages.append({"role": "user", "content": user_message})

        try:
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                max_tokens=400,
                temperature=0.7,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return f"Sorry, I encountered an error: {e}"

    return chat
