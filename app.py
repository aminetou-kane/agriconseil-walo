import math
import os
import re
import time
import unicodedata
from pathlib import Path

import streamlit as st
from google import genai
from google.genai import types

MODELES = ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-3.5-flash"]
DOSSIER_SOURCES = Path(__file__).parent / "data" / "sources"

CONSIGNES = """Tu es AgriConseil Walo, un assistant qui explique la riziculture irriguée
dans le Delta et la vallée du fleuve Sénégal, en français simple. Tu vouvoies toujours l'utilisateur.

Tu reçois des EXTRAITS de documents vérifiés, puis une QUESTION.
Règles :
- Réponds uniquement avec les informations contenues dans les extraits. N'ajoute aucun fait, chiffre ou date qui n'y figure pas.
- Si les extraits ne répondent pas à la question, dis : « Je n'ai pas de source sur ce point. » et conseille de demander à un technicien de la SAED.
- Reprends la zone exacte indiquée pour chaque extrait (par exemple « dans le Delta » ou « dans la Moyenne Vallée »). Ne dis jamais que cela vaut pour Ndiatène ou pour la parcelle de l'utilisateur.
- Indique l'année du document quand elle change le sens (pratiques ou chiffres anciens).
- Ne donne jamais de dose de semences, d'engrais ou de produit chimique. Pour une question de dose, ne dis pas « Je n'ai pas de source » : explique que tu ne donnes pas de dose parce qu'elle dépend de la parcelle et qu'une erreur peut abîmer la récolte. Si un extrait mentionne l'application RiceAdvice, indique qu'AfricaRice la recommande pour adapter les quantités, et conseille aussi un technicien de la SAED.
- Ne pose pas de diagnostic définitif sur une parcelle et ne promets aucun rendement.
- Réponds de façon courte et claire, adaptée à la lecture sur téléphone.
- Ne dis « bonjour » qu'au premier message.
- Utilise des formulations prudentes (« AfricaRice propose », « le document suggère », « il est possible de ») plutôt que des ordres (« vous devez »).
- Quand tu cites des dates ou un calendrier, précise qu'ils sont indicatifs et qu'ils varient selon le périmètre et l'eau disponible : à confirmer auprès de la SAED.
- Ne liste pas les sources dans ta réponse : l'application les affiche.
- Termine TOUJOURS par une dernière ligne séparée, de la forme « UTILISÉS : 1, 3 » avec les numéros des seuls extraits que tu as réellement utilisés (y compris une brochure vers laquelle tu renvoies), ou « UTILISÉS : aucun »."""

AFFICHAGE = {
    "fiche_africarice_brief05": ("Delta du fleuve Sénégal", "décembre 2022"),
    "fiche_africarice_brief06": ("Delta et vallée du fleuve Sénégal", "décembre 2022"),
    "fiche_fao_krupnik": ("Moyenne Vallée, département de Podor (pas le Delta)", "2012"),
    "fiche_jica_2019": ("Départements de Dagana et de Podor", "2019"),
    "fiche_saed_echo_ppri": ("Dagana et Podor", "octobre 2025 à mars 2026"),
    "fiche_wopereis": ("Delta (Thiagar, Gorom) et Moyenne Vallée (Podor)", "1998, mesures de 1993 à 1996"),
}

MOTS_VIDES = {
    "les", "des", "une", "est", "que", "qui", "quoi", "dans", "pour", "par", "sur", "avec",
    "sans", "aux", "ces", "ses", "son", "sa", "ses", "mon", "ma", "mes", "ton", "ta", "tes",
    "nos", "vos", "leur", "leurs", "elle", "elles", "ils", "nous", "vous", "plus", "moins",
    "comment", "quand", "quel", "quelle", "quels", "quelles", "faire", "fait", "faut", "peut",
    "peux", "dois", "doit", "etre", "avoir", "sont", "ont", "cette", "cet", "tout", "tous",
    "pas", "mais", "ou", "donc", "selon", "entre", "apres", "avant", "puis", "aussi", "afin",
    "tres", "bien", "etc", "ainsi", "lors", "chez", "vers", "ici", "faut", "dit", "dire",
}


def normaliser(texte):
    texte = unicodedata.normalize("NFD", texte.lower())
    return "".join(c for c in texte if unicodedata.category(c) != "Mn")


def mots_cles(texte):
    resultat = []
    for mot in re.findall(r"[a-z0-9]+", normaliser(texte)):
        if len(mot) < 3 or mot in MOTS_VIDES:
            continue
        if mot.startswith("salin") or mot in ("sale", "sales", "salee", "salees", "sel", "sels"):
            mot = "salin"
        elif mot in ("dose", "doses", "dosage", "quantite", "quantites", "combien", "kilos", "kg"):
            mot = "quant"
        resultat.append(mot[:5])
    return resultat


def lire_fiche(fichier):
    texte = fichier.read_text(encoding="utf-8")
    titre = fichier.stem
    m = re.search(r"^# (.+)$", texte, re.MULTILINE)
    if m:
        titre = m.group(1).replace("Fiche documentaire :", "").strip()

    lien = ""
    m = re.search(r"\*\*Lien[^*]*\*\*\s*:\s*(\S+)", texte)
    if m and m.group(1).startswith("http"):
        lien = m.group(1)

    niveau = ""
    m = re.search(r"\*\*Niveau proposé\*\*\s*:\s*(.+)", texte)
    if m:
        niveau = m.group(1).strip()

    date = ""
    m = re.search(r"\*\*Date\*\*\s*:\s*(.+)", texte)
    if m:
        date = m.group(1).strip()

    for prefixe, (zone_aff, date_aff) in AFFICHAGE.items():
        if fichier.stem.startswith(prefixe):
            niveau = zone_aff
            date = date_aff

    extraits = []
    section = ""
    actuel = None
    for ligne in texte.splitlines():
        if ligne.startswith("## "):
            section = ligne[3:].strip()
            actuel = None
        elif section.startswith(("Passages utiles", "Limites")):
            if ligne.startswith("- "):
                extraits.append({"section": section, "texte": ligne[2:].strip()})
                actuel = extraits[-1]
            elif ligne.strip() and actuel is not None:
                actuel["texte"] += " " + ligne.strip().lstrip("- ").strip()

    for e in extraits:
        e["titre"] = titre
        e["lien"] = lien
        e["niveau"] = niveau
        e["date"] = date
        e["mots"] = set(mots_cles(e["texte"]))
    return extraits


@st.cache_data
def charger_extraits():
    extraits = []
    if DOSSIER_SOURCES.exists():
        for fichier in sorted(DOSSIER_SOURCES.glob("*.md")):
            extraits.extend(lire_fiche(fichier))
    return extraits


def chercher(question, extraits, k=4):
    mots_question = set(mots_cles(question))
    if not mots_question or not extraits:
        return []

    n = len(extraits)
    frequence = {}
    for e in extraits:
        for mot in e["mots"]:
            frequence[mot] = frequence.get(mot, 0) + 1

    scores = []
    for e in extraits:
        score = 0.0
        for mot in mots_question & e["mots"]:
            score += math.log(1 + n / frequence[mot])
        if e["section"].startswith("Limites"):
            score *= 0.7
        if score > 0:
            scores.append((score, e))

    if not scores:
        return []
    scores.sort(key=lambda x: x[0], reverse=True)
    meilleur = scores[0][0]
    if meilleur < 1.5:
        return []
    return [e for s, e in scores[:k] if s >= max(1.5, 0.25 * meilleur)]


SALUTATIONS = {"bonjour", "bonsoir", "salut", "salam", "hello", "coucou"}


def est_salutation(question):
    mots = re.findall(r"[a-z]+", normaliser(question))
    return len(mots) > 0 and len(mots) <= 3 and mots[0] in SALUTATIONS


def est_question_dose(question):
    mots = set(mots_cles(question))
    cible = {"engra", "uree", "herbi", "pesti", "semen", "npk", "dap", "gypse", "zinc", "insec", "produ"}
    return "quant" in mots and len(mots & cible) > 0


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


def demander_gemini(client, historique, question, trouves):
    bloc = ""
    for i, e in enumerate(trouves, start=1):
        bloc += "[" + str(i) + "] Document : " + e["titre"] + "\n"
        bloc += "Zone : " + e["niveau"] + "\n"
        bloc += "Date : " + e["date"] + "\n"
        bloc += e["texte"] + "\n\n"
    message = "EXTRAITS :\n" + bloc + "QUESTION : " + question

    contenu = []
    for m in historique[-6:]:
        role = "user" if m["role"] == "user" else "model"
        if not contenu and role == "model":
            continue
        contenu.append(types.Content(role=role, parts=[types.Part(text=m["content"])]))
    contenu.append(types.Content(role="user", parts=[types.Part(text=message)]))

    derniere_erreur = ""
    for modele in MODELES:
        for essai in range(2):
            try:
                reponse = client.models.generate_content(
                    model=modele,
                    contents=contenu,
                    config=types.GenerateContentConfig(system_instruction=CONSIGNES),
                )
                return reponse.text, ""
            except Exception as e:
                derniere_erreur = modele + " : " + str(e)[:200]
                print("Erreur Gemini avec", derniere_erreur)
                if "404" in str(e) or "NOT_FOUND" in str(e):
                    break
                if essai == 0:
                    time.sleep(3)
    return None, derniere_erreur


def separer_utilises(texte, trouves):
    lignes = texte.rstrip().splitlines()
    for i in range(len(lignes) - 1, max(len(lignes) - 4, -1), -1):
        brut = normaliser(lignes[i])
        if "utilis" in brut and ":" in brut:
            partie = brut.split(":", 1)[1]
            numeros = [int(x) for x in re.findall(r"\d+", partie)]
            choisis = [trouves[n - 1] for n in numeros if 1 <= n <= len(trouves)]
            propre = "\n".join(lignes[:i]).rstrip()
            return propre, choisis
    return texte.strip(), trouves[:1]


def afficher_sources(sources):
    if not sources:
        return
    with st.expander("Sources utilisées"):
        for s in sources:
            ligne = "**" + s["titre"] + "**"
            if s["date"]:
                ligne += " (" + s["date"] + ")"
            st.markdown(ligne)
            if s["niveau"]:
                st.caption("Zone : " + s["niveau"])
            if s["lien"]:
                st.markdown("[Ouvrir le document](" + s["lien"] + ")")
            else:
                st.caption("Lien du document à ajouter.")


def sources_uniques(trouves):
    vues = set()
    sources = []
    for e in trouves:
        if e["titre"] not in vues:
            vues.add(e["titre"])
            sources.append({"titre": e["titre"], "date": e["date"],
                            "niveau": e["niveau"], "lien": e["lien"]})
    return sources


def main():
    st.set_page_config(page_title="AgriConseil Walo", page_icon="🌾")
    st.title("🌾 AgriConseil Walo")
    st.write("Assistant sur la riziculture irriguée dans le Delta et la vallée du fleuve Sénégal "
             "(département de Dagana). Les réponses viennent d'un petit nombre de documents cités.")
    st.warning("L'IA peut se tromper. Cet assistant ne remplace pas un technicien agricole "
               "et ne donne pas de doses d'engrais ou de produits.")

    extraits = charger_extraits()
    titres = sorted(set(e["titre"] for e in extraits))
    if not extraits:
        st.error("Aucune fiche trouvée dans le dossier data/sources.")
    st.sidebar.write(str(len(titres)) + " documents chargés")
    for t in titres:
        st.sidebar.caption(t)

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if st.sidebar.button("Nouvelle conversation"):
        st.session_state.messages = []

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.write(m["content"])
            afficher_sources(m.get("sources"))

    question = st.chat_input("Posez votre question sur la culture du riz...")
    if not question:
        return

    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    trouves = chercher(question, extraits)
    if est_question_dose(question):
        riceadvice = [e for e in extraits if "RiceAdvice" in e["texte"]][:1]
        trouves = riceadvice + [e for e in trouves if e not in riceadvice]
    sources = []
    with st.chat_message("assistant"):
        if est_salutation(question):
            texte = ("Bonjour ! Posez-moi une question sur la culture du riz irrigué "
                     "dans le Delta du fleuve Sénégal : semis, eau, variétés, salinité, récolte.")
        elif not trouves:
            texte = ("Je n'ai pas de source dans ma base pour répondre à cette question. "
                     "Pour une réponse fiable, demandez conseil à un technicien de la SAED.")
        else:
            client = creer_client()
            if client is None:
                texte = "La clé du service d'IA n'est pas configurée."
            else:
                with st.spinner("Recherche dans les documents..."):
                    texte, erreur = demander_gemini(client, st.session_state.messages[:-1],
                                                    question, trouves)
                if texte is None:
                    texte = ("Le service d'IA est très sollicité en ce moment. "
                             "Réessayez dans un instant.")
                    st.caption("Détail technique : " + erreur)
                else:
                    texte, utilises = separer_utilises(texte, trouves)
                    sources = sources_uniques(utilises)
        st.write(texte)
        afficher_sources(sources)

    st.session_state.messages.append({"role": "assistant", "content": texte, "sources": sources})


if __name__ == "__main__":
    main()
