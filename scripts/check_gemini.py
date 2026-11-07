
import os

from dotenv import load_dotenv
from google import genai

from pathlib import Path
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

api_key = os.getenv("GEMINI_API_KEY")
model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

if not api_key:
    raise ValueError(
        "Clé Gemini absente : vérifie le fichier .env à la racine."
    )

client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model=model,
    contents="Réponds uniquement par : Connexion Gemini réussie !",
)

print(response.text)
