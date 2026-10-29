import os
import time

import streamlit as st
from google import genai
from google.genai import types

MODELE = "gemini-3.1-flash-lite"

CONSIGNES = """Tu es AgriConseil Walo, un assistant qui explique la riziculture irriguée
dans la vallée du fleuve Sénégal, en français simple. Tu vouvoies toujours l'utilisateur.
Règles :
- Ne dis « bonjour » qu'au premier message de la conversation.
- Réponds de façon courte et claire, adaptée à la lecture sur téléphone.
- N'invente jamais de faits, de sources, de chiffres ou de données locales.
- Tu n'as pas encore de documents vérifiés : présente tes réponses comme des informations
  générales, non vérifiées pour la vallée du fleuve Sénégal ou pour Ndiatène.
- Ne donne pas de durées, de dates ou de quantités précises sans source.
- Si la question est trop vague, demande une précision utile (stade de culture, type de sol, etc.).
- Ne donne pas de dose d'engrais ou de pesticide, et ne promets aucun rendement.
- Ne pose pas de diagnostic définitif : conseille de consulter un technicien agricole.
- Réponds seulement aux questions sur la riziculture et l'agriculture."""


def creer_client():
    cle = os.environ.get("GEMINI_API_KEY")
    if not cle:
        try:
            cle = st.secrets["GEMINI_API_KEY"]
        except Exception:
            cle = None
    if not cle:
        return None
    return genai.Client(api_key=cle)


def demander_gemini(client, messages):
    contenu = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        contenu.append(types.Content(role=role, parts=[types.Part(text=m["content"])]))

    for essai in range(3):
        try:
            reponse = client.models.generate_content(
                model=MODELE,
                contents=contenu,
                config=types.GenerateContentConfig(system_instruction=CONSIGNES),
            )
            return reponse.text
        except Exception:
            if essai < 2:
                time.sleep(2 * (essai + 1))
    return None


st.set_page_config(page_title="AgriConseil Walo", page_icon="🌾")
st.title("🌾 AgriConseil Walo")
st.write("Assistant sur la riziculture irriguée dans la vallée du fleuve Sénégal. "
         "Localité pilote : Ndiatène (commune de Ronkh).")
st.warning("L'IA peut se tromper. Cette version n'utilise pas encore de documents "
           "vérifiés et ne remplace pas un technicien agricole.")

if st.sidebar.button("Nouvelle conversation"):
    st.session_state.messages = []

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.write(m["content"])

question = st.chat_input("Posez votre question sur la culture du riz...")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    client = creer_client()
    with st.chat_message("assistant"):
        if client is None:
            texte = "La clé du service d'IA n'est pas configurée."
        else:
            with st.spinner("Réflexion en cours..."):
                texte = demander_gemini(client, st.session_state.messages)
            if texte is None:
                texte = ("Le service d'IA est très sollicité en ce moment. "
                         "Réessayez dans un instant.")
        st.write(texte)
    st.session_state.messages.append({"role": "assistant", "content": texte})