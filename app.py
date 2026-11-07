import hashlib
import json
import math
import os
import re
import time
import unicodedata
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
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
- Reprends la zone exacte indiquée pour chaque extrait (par exemple « dans le Delta » ou « dans la Moyenne Vallée »). Ne dis jamais que cela vaut pour un village précis ou pour la parcelle de l'utilisateur.
- Indique l'année du document quand elle change le sens (pratiques ou chiffres anciens).
- Ne donne jamais de dose de semences, d'engrais ou de produit chimique. Pour une question de dose, ne dis pas « Je n'ai pas de source » : explique que tu ne donnes pas de dose parce qu'elle dépend de la parcelle et qu'une erreur peut abîmer la récolte. Si un extrait mentionne l'application RiceAdvice, indique qu'AfricaRice la recommande pour adapter les quantités, et conseille aussi un technicien de la SAED.
- Ne pose pas de diagnostic définitif sur une parcelle et ne promets aucun rendement.
- Réponds de façon courte et claire, adaptée à la lecture sur téléphone.
- Ne dis « bonjour » qu'au premier message.
- Utilise des formulations prudentes (« AfricaRice propose », « le document suggère », « il est possible de ») plutôt que des ordres (« vous devez »).
- Quand tu cites des dates ou un calendrier, précise qu'ils sont indicatifs et qu'ils varient selon le périmètre et l'eau disponible : à confirmer auprès de la SAED.
- Ne liste pas les sources dans ta réponse : l'application les affiche.
- Termine TOUJOURS par une dernière ligne séparée, de la forme « UTILISÉS : 1, 3 » avec les numéros de tous les extraits dont tu as utilisé une information, même une seule phrase (y compris une brochure vers laquelle tu renvoies), ou « UTILISÉS : aucun »."""

AFFICHAGE = {
    "fiche_africarice_brief05": ("Delta du fleuve Sénégal", "décembre 2022"),
    "fiche_africarice_brief06": ("Delta et vallée du fleuve Sénégal", "décembre 2022"),
    "fiche_fao_krupnik": ("Moyenne Vallée, département de Podor (pas le Delta)", "2012"),
    "fiche_jica_2019": ("Départements de Dagana et de Podor", "2019"),
    "fiche_saed_echo_ppri": ("Dagana et Podor", "octobre 2025 à mars 2026"),
    "fiche_wopereis": ("Delta (Thiagar, Gorom) et Moyenne Vallée (Podor)", "1998, mesures de 1993 à 1996"),
}

DETAILS = {
    "fiche_africarice_brief05": {
        "organisme": "AfricaRice",
        "theme": "Pratiques de culture dans le Delta (calendrier, semis, eau, récolte)",
        "pourquoi": "Guide de bonnes pratiques propre au Delta du fleuve Sénégal, avec un calendrier, "
                    "des variétés et des conseils sur l'eau et la récolte.",
    },
    "fiche_africarice_brief06": {
        "organisme": "AfricaRice",
        "theme": "Salinité des sols",
        "pourquoi": "Présente des options agronomiques face au sel, avec des résultats de terrain "
                    "et une limite d'emploi claire.",
    },
    "fiche_fao_krupnik": {
        "organisme": "FAO, avec AfricaRice et la SAED",
        "theme": "Pratiques des producteurs, désherbage, gestion de l'eau",
        "pourquoi": "Essais menés avec des producteurs, en français. Il montre pourquoi les pratiques "
                    "changent selon les périmètres.",
    },
    "fiche_jica_2019": {
        "organisme": "JICA",
        "theme": "Contexte de Dagana et Podor (périmètres, saisons, contraintes)",
        "pourquoi": "Décrit les périmètres irrigués, les saisons et les grandes contraintes "
                    "dans la zone de Dagana.",
    },
    "fiche_saed_echo_ppri": {
        "organisme": "SAED (projet PPRI, financé par la JICA)",
        "theme": "Actualité des travaux à Dagana",
        "pourquoi": "Donne la situation récente (2025-2026) : réhabilitation de périmètres, "
                    "stockage, drainage.",
    },
    "fiche_wopereis": {
        "organisme": "WARDA, ORSTOM, SAED (article scientifique)",
        "theme": "Salinité des sols du Delta",
        "pourquoi": "Mesures de salinité dans le Delta. Explique l'origine du sel et le rôle de l'eau. "
                    "Document ancien : à lire avec prudence.",
    },
}

THEMES = {
    "Tous les thèmes": "",
    "Semis et calendrier": "semis semer calendrier saison",
    "Eau et irrigation": "eau irrigation drainage",
    "Salinité des sols": "salinité sel",
    "Variétés": "variétés",
    "Récolte": "récolte",
    "Contexte de Dagana": "Dagana Podor périmètres",
}
STADES = ["Je ne sais pas", "Avant le semis", "Semis", "Croissance", "Floraison",
          "Maturité et récolte"]
PAGES = ["💬 Assistant", "📚 Sources agricoles", "ℹ️ À propos"]
AUTEURE = "Aminetou Kane"
AVATARS = {"user": "🧑‍🌾", "assistant": "🌾"}

MOTS_VIDES = {
    "les", "des", "une", "est", "que", "qui", "quoi", "dans", "pour", "par", "sur", "avec",
    "sans", "aux", "ces", "ses", "son", "sa", "ses", "mon", "ma", "mes", "ton", "ta", "tes",
    "nos", "vos", "leur", "leurs", "elle", "elles", "ils", "nous", "vous", "plus", "moins",
    "comment", "quand", "quel", "quelle", "quels", "quelles", "faire", "fait", "faut", "peut",
    "peux", "dois", "doit", "etre", "avoir", "sont", "ont", "cette", "cet", "tout", "tous",
    "pas", "mais", "ou", "donc", "selon", "entre", "apres", "avant", "puis", "aussi", "afin",
    "tres", "bien", "etc", "ainsi", "lors", "chez", "vers", "ici", "faut", "dit", "dire",
}


MOTS_GENERAUX = {"riz", "rizic", "rizie", "cultu", "irrig", "augme", "reduc", "dimin"}


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

    cle = fichier.stem
    for prefixe, (zone_aff, date_aff) in AFFICHAGE.items():
        if fichier.stem.startswith(prefixe):
            niveau = zone_aff
            date = date_aff
            cle = prefixe

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
        etiquette = re.match(r"\*\*([^*]+)\*\*", e["texte"])
        e["etiquette"] = set(mots_cles(etiquette.group(1))) if etiquette else set()
        e["titre"] = titre
        e["cle"] = cle
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
            poids = 0.3 if mot in MOTS_GENERAUX else 1.0
            score += poids * math.log(1 + n / frequence[mot])
        if score > 0:
            score += 2.5 * len(mots_question & e["etiquette"])
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
    return genai.Client(api_key=cle, http_options=types.HttpOptions(timeout=60000))


def construire_contenu(historique, question, trouves, contexte=""):
    bloc = ""
    for i, e in enumerate(trouves, start=1):
        bloc += "[" + str(i) + "] Document : " + e["titre"] + "\n"
        bloc += "Zone : " + e["niveau"] + "\n"
        bloc += "Date : " + e["date"] + "\n"
        bloc += e["texte"] + "\n\n"
    message = "CONTEXTE : " + contexte + "\n\nEXTRAITS :\n" + bloc + "QUESTION : " + question

    contenu = []
    for m in historique[-6:]:
        role = "user" if m["role"] == "user" else "model"
        if not contenu and role == "model":
            continue
        contenu.append(types.Content(role=role, parts=[types.Part(text=m["content"])]))
    contenu.append(types.Content(role="user", parts=[types.Part(text=message)]))
    return contenu


def flux_gemini(client, contenu, etat):
    for modele in MODELES:
        for essai in range(2):
            commence = False
            try:
                flux = client.models.generate_content_stream(
                    model=modele,
                    contents=contenu,
                    config=types.GenerateContentConfig(system_instruction=CONSIGNES),
                )
                for morceau in flux:
                    if morceau.text:
                        if not commence:
                            etat["premier"] = time.perf_counter()
                        commence = True
                        yield morceau.text
                if commence:
                    etat["modele"] = modele
                    return
                etat["erreur"] = modele + " : réponse vide"
            except Exception as e:
                etat["erreur"] = modele + " : " + str(e)[:200]
                print("Erreur Gemini avec", etat["erreur"])
                if commence:
                    return
                if "404" in str(e) or "NOT_FOUND" in str(e):
                    break
            if essai == 0:
                time.sleep(2)


def message_erreur(detail):
    d = detail.upper()
    if "429" in d or "RESOURCE_EXHAUSTED" in d or "QUOTA" in d:
        return ("La limite gratuite du service d'IA est atteinte pour le moment. "
                "Réessayez dans quelques minutes.")
    if "503" in d or "UNAVAILABLE" in d or "OVERLOAD" in d:
        return "Le service d'IA est très sollicité en ce moment. Réessayez dans un instant."
    if "TIMEOUT" in d or "TIMED OUT" in d or "CONNECT" in d or "GETADDRINFO" in d or "NETWORK" in d:
        return ("Je n'arrive pas à joindre le service d'IA. Vérifiez votre connexion Internet, "
                "puis réessayez.")
    return "Une erreur s'est produite. Réessayez dans un instant."


def masquer_marqueur(texte):
    m = re.search(r"\n[\s*_]*UTILIS", texte, re.IGNORECASE)
    return texte[:m.start()] if m else texte


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


def transcrire(client, donnees, type_mime):
    consigne = ("Transcris fidèlement cet enregistrement en français. "
                "Réponds uniquement avec le texte entendu, sans commentaire. "
                "Si tu ne comprends pas ou s'il n'y a pas de parole, réponds exactement : INCOMPRIS")
    for modele in MODELES:
        try:
            reponse = client.models.generate_content(
                model=modele,
                contents=[types.Part.from_bytes(data=donnees, mime_type=type_mime), consigne],
            )
            texte = (reponse.text or "").strip()
            if not texte or "INCOMPRIS" in texte.upper():
                return ""
            return texte
        except Exception as e:
            print("Erreur transcription avec", modele, ":", str(e)[:200])
    return ""


def texte_pour_lecture(texte):
    texte = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", texte)
    texte = texte.replace("*", "").replace("#", "").replace("`", "")
    texte = re.sub(r"\s+", " ", texte)
    return texte.strip()


def bouton_ecouter(texte):
    propre = texte_pour_lecture(texte).replace("</", "<\\/")
    html = """
    <button onclick="lire()" style="font-size:18px;padding:10px 18px;border:none;border-radius:10px;
    background:#2e7d32;color:white;cursor:pointer;">🔊 Écouter la réponse</button>
    <button onclick="window.speechSynthesis.cancel()" title="Arrêter la lecture" style="font-size:18px;
    padding:10px 14px;border:none;border-radius:10px;background:#9e9e9e;color:white;cursor:pointer;">⏹</button>
    <script>
    function lire() {
        window.speechSynthesis.cancel();
        var u = new SpeechSynthesisUtterance(__TEXTE__);
        u.lang = "fr-FR";
        u.rate = 0.9;
        window.speechSynthesis.speak(u);
    }
    </script>
    """.replace("__TEXTE__", json.dumps(propre))
    if hasattr(st, "iframe"):
        st.iframe(html, height=60)
    else:
        components.html(html, height=60)


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


AVERTISSEMENT = ("AgriConseil Walo est une IA et peut se tromper. Elle ne remplace pas un technicien "
                 "agricole et ne donne pas de doses d'engrais ou de produits.")

STYLE = """<style>
.accueil {text-align: center; margin-top: 16vh; margin-bottom: 1.5rem;}
.accueil .logo {font-size: 3.2rem;}
.accueil h1 {font-size: clamp(1.6rem, 5vw, 2.2rem); font-weight: 500; padding: 0.4rem 0 0.2rem 0; text-wrap: balance;}
.accueil p {opacity: 0.65; font-size: 0.92rem;}
</style>"""


def liste_documents(extraits):
    vus = {}
    for e in extraits:
        if e["titre"] not in vus:
            vus[e["titre"]] = e
    return list(vus.values())


def page_sources(extraits):
    st.markdown("#### 📚 Sources agricoles")
    st.write("Voici les documents sur lesquels l'assistant s'appuie, et pourquoi ils ont été retenus.")
    for e in liste_documents(extraits):
        d = DETAILS.get(e["cle"], {})
        with st.container(border=True):
            st.markdown("**" + e["titre"] + "**")
            st.caption("Organisme : " + d.get("organisme", "non précisé") + " · Date : "
                       + e["date"] + " · Zone : " + e["niveau"])
            if d.get("theme"):
                st.write("Thème : " + d["theme"])
            if d.get("pourquoi"):
                st.write("Pourquoi ce document : " + d["pourquoi"])
            if e["lien"]:
                st.markdown("[Ouvrir le document](" + e["lien"] + ")")
            else:
                st.caption("Lien du document à ajouter.")
    st.info("Les documents anciens ou d'une autre zone sont signalés dans les réponses. "
            "L'assistant ne donne pas de doses d'engrais ni de produits.")


def page_a_propos(extraits):
    documents = liste_documents(extraits)
    st.markdown("#### ℹ️ À propos d'AgriConseil Walo")
    st.markdown("**Le problème.** Les informations utiles sur la riziculture irriguée existent, mais "
                "elles sont dispersées dans des documents techniques longs, souvent en anglais, "
                "et difficiles à consulter sur un téléphone.")
    st.markdown("**Le public visé.** Les producteurs de riz de la vallée du fleuve Sénégal, les relais "
                "qui les accompagnent (techniciens, responsables de groupements, jeunes) et les "
                "étudiants. Le projet couvre le département de Dagana, dans le Delta du fleuve Sénégal.")
    st.markdown("**Les sources.** L'assistant s'appuie sur " + str(len(documents)) + " documents :")
    for e in documents:
        st.markdown("- " + e["titre"])
    st.markdown("**Comment ça marche.**")
    st.markdown("1. Vous posez votre question, par écrit ou à voix haute.\n"
                "2. L'application cherche les passages utiles dans les documents.\n"
                "3. Un modèle d'IA (Gemini) rédige une réponse à partir de ces seuls passages.\n"
                "4. Les sources sont affichées sous la réponse. S'il n'y a aucun passage utile, "
                "l'assistant le dit.")
    st.markdown("**Les limites.**")
    st.markdown("- Cet assistant ne remplace pas un technicien agricole.\n"
                "- Il ne donne pas de doses d'engrais, de semences ou de produits : elles dépendent "
                "de chaque parcelle.\n"
                "- Il n'a pas de données propres à un village précis : ses sources parlent du Delta "
                "et de la vallée du fleuve Sénégal.\n"
                "- Certaines sources sont anciennes (jusqu'à 1998) : les pratiques ont pu changer.\n"
                "- Il ne connaît que ses documents : pour le reste, il répond qu'il n'a pas de source.\n"
                "- La transcription de la voix peut se tromper.\n"
                "- Vos questions sont envoyées au service Gemini de Google pour produire la réponse : "
                "n'y mettez pas d'informations personnelles.\n"
                "- Les conversations ne sont pas enregistrées par l'application : elles disparaissent "
                "quand vous fermez la page.\n"
                "- Le wolof n'est pas encore disponible.\n"
                "- L'IA peut faire des erreurs : vérifiez avec un technicien.")
    st.markdown("**Les outils.** Python et Streamlit pour l'application ; Gemini (Google AI Studio) "
                "pour rédiger les réponses et transcrire la voix ; des fiches documentaires en "
                "fichiers texte ; GitHub pour le code ; la voix du navigateur pour lire les réponses.")
    st.markdown("**Transparence.** Projet réalisé par " + AUTEURE + ", étudiante en L3 Informatique à "
                "l'Université Gaston Berger, pour le hackathon Build Your First AI App 2026. "
                "Outil d'IA utilisé pendant le développement : Claude (Anthropic), pour aider à écrire "
                "le code et les fiches documentaires. Les fiches s'appuient sur les documents publics "
                "cités ci-dessus.")


def choisir_contexte():
    with st.sidebar.expander("🌱 Contexte de ma question"):
        st.selectbox("Thème", list(THEMES), key="theme")
        st.selectbox("Stade de la culture", STADES, key="stade")
        st.caption("Zone couverte : département de Dagana (Delta et vallée du fleuve "
                   "Sénégal). L'application n'a pas de données propres à un village précis.")


def nouvelle_conversation():
    st.session_state.page = PAGES[0]
    st.session_state.conv_id = None
    st.session_state.messages = []
    st.session_state.en_attente = False


def ouvrir_conversation(cid):
    st.session_state.page = PAGES[0]
    st.session_state.conv_id = cid
    st.session_state.messages = st.session_state.conversations[cid]["messages"]
    st.session_state.en_attente = False


def effacer_conversations():
    st.session_state.conversations = {}
    nouvelle_conversation()


def afficher_historique():
    st.sidebar.button("Nouvelle conversation", icon="➕", on_click=nouvelle_conversation)
    choisir_contexte()
    conversations = st.session_state.conversations
    if conversations:
        st.sidebar.caption("Vos conversations")
        for cid in sorted(conversations, reverse=True):
            titre = conversations[cid]["titre"]
            actuelle = cid == st.session_state.conv_id
            st.sidebar.button(titre, key="conv" + str(cid), on_click=ouvrir_conversation,
                              args=(cid,), type="primary" if actuelle else "secondary")
        st.sidebar.button("Effacer les conversations", icon="🗑️", on_click=effacer_conversations)
        st.sidebar.caption("Les conversations restent seulement dans votre navigateur, "
                           "le temps de votre visite.")


def afficher_accueil():
    st.markdown(
        '<div class="accueil"><div class="logo">🌾</div>'
        "<h1>Que voulez-vous savoir sur votre riz ?</h1>"
        "<p>AgriConseil Walo · riziculture irriguée dans le Delta et la vallée du fleuve "
        "Sénégal (Dagana)</p></div>",
        unsafe_allow_html=True)


def saisir_question():
    try:
        return st.chat_input("Posez votre question...", accept_audio=True)
    except TypeError:
        return st.chat_input("Posez votre question...")


def lire_saisie(valeur):
    if not valeur:
        return "", None
    if isinstance(valeur, str):
        return valeur.strip(), None
    texte = valeur.get("text") if hasattr(valeur, "get") else getattr(valeur, "text", "")
    audio = valeur.get("audio") if hasattr(valeur, "get") else getattr(valeur, "audio", None)
    return (texte or "").strip(), audio


def main():
    st.set_page_config(page_title="AgriConseil Walo", page_icon="🌾",
                       initial_sidebar_state="auto")
    st.markdown(STYLE, unsafe_allow_html=True)

    extraits = charger_extraits()
    titres = sorted(set(e["titre"] for e in extraits))
    if not extraits:
        st.error("Aucune fiche trouvée dans le dossier data/sources.")
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "conversations" not in st.session_state:
        st.session_state.conversations = {}
        st.session_state.conv_id = None
        st.session_state.prochain_id = 1

    st.sidebar.markdown("### 🌾 AgriConseil Walo")
    afficher_historique()
    st.sidebar.divider()
    page = st.sidebar.radio("Pages", PAGES, key="page", label_visibility="collapsed")
    with st.sidebar.expander("Détails techniques"):
        st.caption(str(len(titres)) + " documents chargés")
        zone_temps = st.empty()
        if st.session_state.get("temps"):
            zone_temps.caption(st.session_state.temps)

    if page == PAGES[1]:
        page_sources(extraits)
        return
    if page == PAGES[2]:
        page_a_propos(extraits)
        return

    accueil = len(st.session_state.messages) == 0
    en_attente = st.session_state.get("en_attente", False) and not accueil
    question = None
    depuis_voix = False
    duree_transcription = 0.0

    if accueil:
        zone_accueil = st.empty()
        with zone_accueil.container():
            afficher_accueil()
        with st.container():
            valeur = saisir_question()
        zone_avertissement = st.empty()
        zone_avertissement.caption(AVERTISSEMENT)
    else:
        for m in st.session_state.messages:
            with st.chat_message(m["role"], avatar=AVATARS[m["role"]]):
                st.write(m["content"])
                if m.get("voix"):
                    st.caption("🎙️ Question entendue à voix haute")
                if m["role"] == "assistant":
                    bouton_ecouter(m["content"])
                afficher_sources(m.get("sources"))
        valeur = saisir_question()
        with st.bottom:
            st.caption(AVERTISSEMENT)

    if en_attente:
        repondre(extraits, zone_temps)
        return

    texte_saisi, audio = lire_saisie(valeur)
    if texte_saisi:
        question = texte_saisi
    elif audio is not None:
        client_audio = creer_client()
        if client_audio is None:
            st.warning("La clé du service d'IA n'est pas configurée.")
        else:
            debut = time.perf_counter()
            with st.spinner("J'écoute votre question..."):
                entendu = transcrire(client_audio, audio.getvalue(),
                                     getattr(audio, "type", None) or "audio/wav")
            duree_transcription = time.perf_counter() - debut
            print("Transcription :", round(duree_transcription, 1), "s")
            if entendu:
                question = entendu
                depuis_voix = True
            else:
                st.warning("Je n'ai pas bien compris l'enregistrement. "
                           "Réessayez ou écrivez votre question.")

    if question:
        st.session_state.messages.append({"role": "user", "content": question,
                                          "voix": depuis_voix,
                                          "theme": st.session_state.get("theme", "Tous les thèmes"),
                                          "stade": st.session_state.get("stade", STADES[0])})
        if st.session_state.conv_id is None:
            cid = st.session_state.prochain_id
            st.session_state.prochain_id = cid + 1
            titre = question if len(question) <= 36 else question[:35] + "…"
            st.session_state.conversations[cid] = {"titre": titre,
                                                   "messages": st.session_state.messages}
            st.session_state.conv_id = cid
        st.session_state.en_attente = True
        st.session_state.duree_transcription = duree_transcription
        st.rerun()


def repondre(extraits, zone_temps):
    st.session_state.en_attente = False
    question = st.session_state.messages[-1]["content"]
    theme = st.session_state.messages[-1].get("theme", "Tous les thèmes")
    stade = st.session_state.messages[-1].get("stade", STADES[0])
    historique = st.session_state.messages[:-1]
    contexte = ("Zone couverte : département de Dagana, Delta du fleuve Sénégal (aucune donnée "
                "propre à un village précis). "
                "Thème choisi : " + theme + ". Stade de la culture : " + stade
                + " (ne rien en déduire d'autre sur la parcelle).")

    trouves = chercher(question + " " + THEMES.get(theme, ""), extraits)
    if est_question_dose(question):
        riceadvice = [e for e in extraits if "RiceAdvice" in e["texte"]][:1]
        trouves = riceadvice + [e for e in trouves if e not in riceadvice]

    sources = []
    debut = time.perf_counter()
    etat = {}
    with st.chat_message("assistant", avatar=AVATARS["assistant"]):
        if est_salutation(question):
            texte = ("Bonjour ! Posez-moi une question sur la culture du riz irrigué "
                     "dans le Delta du fleuve Sénégal : semis, eau, variétés, salinité, récolte.")
            st.write(texte)
        elif not trouves:
            texte = ("Je n'ai pas de document fiable sur ce point, et je préfère ne pas inventer "
                     "de réponse. Mes sources couvrent le calendrier de semis, la préparation du "
                     "terrain, l'eau, les variétés, la salinité, la récolte et le contexte de Dagana. "
                     "Pouvez-vous préciser votre question dans l'un de ces domaines ? Pour évaluer "
                     "votre parcelle, demandez conseil à un technicien de la SAED.")
            st.write(texte)
        else:
            client = creer_client()
            if client is None:
                texte = "La clé du service d'IA n'est pas configurée."
                st.write(texte)
            else:
                zone = st.empty()
                zone.markdown("⏳ Recherche dans les documents...")
                accumule = ""
                contenu = construire_contenu(historique, question, trouves, contexte)
                for morceau in flux_gemini(client, contenu, etat):
                    accumule += morceau
                    zone.markdown(masquer_marqueur(accumule) + " ▌")
                if not accumule:
                    texte = message_erreur(etat.get("erreur", ""))
                    zone.markdown(texte)
                    st.caption("Détail technique : " + etat.get("erreur", ""))
                else:
                    texte, utilises = separer_utilises(accumule, trouves)
                    sources = sources_uniques(utilises)
                    zone.markdown(texte)
        bouton_ecouter(texte)
        afficher_sources(sources)

    fin = time.perf_counter()
    premier = etat.get("premier")
    resume = "⏱ Dernière réponse : "
    if st.session_state.get("duree_transcription"):
        resume += "transcription " + str(round(st.session_state.duree_transcription, 1)) + " s, "
    if premier:
        resume += "premiers mots après " + str(round(premier - debut, 1)) + " s, "
    resume += "total " + str(round(fin - debut, 1)) + " s"
    print(resume)
    st.session_state.temps = resume
    zone_temps.caption(resume)

    st.session_state.messages.append({"role": "assistant", "content": texte, "sources": sources})


if __name__ == "__main__":
    main()
