import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

APP_ID = os.getenv("EDAMAM_APP_ID", "")
APP_KEY = os.getenv("EDAMAM_APP_KEY", "")

url = "https://api.edamam.com/api/recipes/v2"
params = {"type": "public", "app_id": APP_ID, "app_key": APP_KEY, "q": "chicken"}

user_ids_to_try = [
    None,
    "default_user",
    "user001",
    APP_ID,
]

for uid in user_ids_to_try:
    headers = {"Edamam-Account-User": uid} if uid else {}
    resp = requests.get(url, params=params, headers=headers, timeout=10)
    print(f"User-ID={uid!r:30}  →  {resp.status_code}  {resp.text[:120]}")
