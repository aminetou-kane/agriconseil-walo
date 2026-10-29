from google import genai

client = genai.Client()

response = client.models.generate_content(
    model="gemini-flash-latest",
    contents="Explique en 3 phrases simples ce qu'est la riziculture irriguée.",
)

print(response.text)