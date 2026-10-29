from google import genai

client = genai.Client()

candidats = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.1-flash-lite",
]

for nom in candidats:
    print("Test de :", nom)
    try:
        reponse = client.models.generate_content(
            model=nom,
            contents="Explique en 3 phrases simples ce qu'est la riziculture irriguée.",
        )
        print("OK ->", reponse.text)
    except Exception as e:
        print("Échec ->", str(e)[:150])
    print("-" * 40)