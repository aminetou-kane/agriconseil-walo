# AgriConseil Walo

[English](README.md) | **Français**

Un assistant en français sur la riziculture irriguée dans le Delta et la vallée du fleuve Sénégal (département de Dagana). On pose une question à l'écrit ou à voix haute ; la réponse est rédigée uniquement à partir d'un petit nombre de documents cités, et les sources sont affichées sous chaque réponse.

- **Démo en ligne :** [à ajouter après la mise en ligne]
- **Vidéo de démonstration :** [à ajouter]
- **Hackathon :** Build Your First AI App 2026 (Devpost)

## Le problème

Les informations utiles sur le riz irrigué existent, mais elles sont dispersées dans de longs rapports techniques, souvent en anglais, et difficiles à lire sur un téléphone. Beaucoup de producteurs, et les conseillers qui les accompagnent, ne peuvent pas obtenir facilement une réponse fiable et sourcée à une question pratique simple, comme « Quand récolter ? ».

## La solution

AgriConseil Walo répond aux questions pratiques en français simple et indique d'où vient chaque réponse. Quand les documents ne contiennent pas de réponse fiable, l'assistant le dit au lieu d'en inventer une. Il ne donne jamais de dose d'engrais, de semences ou de produits, car elle dépend de chaque parcelle et une erreur peut abîmer une récolte.

**Public visé :** les producteurs de riz du Delta et de la vallée du fleuve Sénégal, les conseillers et responsables de groupements qui les accompagnent, et les étudiants.

## Fonctionnalités

- Interface de conversation avec un **micro** dans la zone de saisie (question à voix haute) et un bouton **« Écouter la réponse »** (lecture par la voix du navigateur).
- **Réponses avec sources :** titre du document, date, zone couverte et lien vers le document d'origine.
- **Comportement « pas de source fiable » :** l'assistant explique ce que couvrent les documents et demande de préciser la question.
- **Contexte de la question** (facultatif) : thème et stade de la culture, qui orientent la recherche.
- **Pages « Sources agricoles » et « À propos » :** liste des documents et raisons de leur choix ; problème, public, fonctionnement, limites, outils, transparence.
- **Historique des conversations** dans le menu de gauche, conservé seulement pendant la visite.
- **Messages d'erreur clairs :** limite gratuite atteinte, service surchargé, pas de connexion.
- **Affichage adapté au téléphone** (vérifié dans une fenêtre de navigateur de taille mobile ; les essais sur un vrai téléphone restent à faire).

## Comment ça marche

1. L'utilisateur pose sa question (texte ou voix). La voix est transcrite avec Gemini.
2. L'application cherche dans de courtes **fiches de connaissances** (un fichier Markdown par document, dans `data/sources/`) avec une recherche simple par mots, pondérée par la rareté de chaque mot.
3. Les meilleurs passages, avec le titre, la date et la zone du document, sont envoyés à **Gemini** avec des consignes strictes : utiliser seulement ces passages, dire quand il n'y a pas de source, ne jamais donner de dose, indiquer la zone exacte et l'année, et terminer par les numéros des passages utilisés.
4. La réponse s'affiche au fur et à mesure et les sources réellement utilisées sont listées dessous.
5. Si aucun passage n'est trouvé, Gemini **n'est pas appelé** : l'application répond qu'elle n'a pas de document fiable sur ce point.

C'est une petite architecture de génération augmentée par recherche, construite sans base de données vectorielle pour rester facile à inspecter et à expliquer.

## Mise en œuvre de l'IA

- **Modèle :** Google Gemini via Google AI Studio (`gemini-3.1-flash-lite`, avec repli sur `gemini-3.5-flash-lite` et `gemini-3.5-flash`), utilisé pour rédiger les réponses à partir des passages trouvés et pour transcrire les questions parlées.
- **Recherche :** code écrit dans `app.py` (correspondance de mots, pondération par rareté, bonus quand un mot de la question correspond au titre d'un passage).
- **Lecture à voix haute :** API de synthèse vocale du navigateur (aucun service supplémentaire).
- **Évaluation :** `tests/test_recherche.py` exécute 20 contrôles automatiques de l'étape de recherche (17 questions qui doivent trouver un passage donné et 3 qui ne doivent rien trouver). Il vérifie la recherche seulement, pas la qualité de la rédaction de Gemini. Des grilles de test manuelles se trouvent dans `tests/questions_test.md` et `tests/questions_construites.md` (20 questions réalistes écrites à partir des thèmes des documents ; elles ne viennent pas de vrais producteurs, et un essai avec de vrais utilisateurs reste à faire).

## Documents utilisés

L'application ne garde que de courtes notes reformulées et des liens, pas les documents d'origine. Tous les documents appartiennent à leurs auteurs.

| Document | Zone | Année |
|---|---|---|
| AfricaRice, Innovation Brief 05, bonnes pratiques agricoles pour le riz ([lien](https://www.africarice.org/_files/ugd/0839e4_055dfdaf6efa423abdb63735465956a2.pdf)) | Delta du fleuve Sénégal | 2022 |
| AfricaRice, Innovation Brief 06, options agronomiques pour la salinité ([lien](https://www.africarice.org/_files/ugd/0839e4_8165cf02a7064e4d8bed5f9b4bc115ce.pdf)) | Delta et vallée | 2022 |
| FAO, Krupnik et al., Améliorer la production du riz irrigué dans la vallée du fleuve Sénégal ([lien](https://fao.org/fileadmin/user_upload/ippm/docs/1_Am%C3%A9liorer_du_riz.pdf)) | Moyenne Vallée (Podor) | 2012 |
| JICA, étude préparatoire du projet de production de riz irrigué ([lien](https://openjicareport.jica.go.jp/pdf/12353819.pdf)) | Dagana et Podor | 2019 |
| SAED, bulletins « Écho PPRI » (pas encore de lien en ligne) | Dagana et Podor | oct. 2025 à mars 2026 |
| Wopereis et al., Préserver la qualité des sols sous irrigation dans la vallée du fleuve Sénégal ([lien](https://library.wur.nl/ojs/index.php/njas/article/download/500/214)) | Delta et Moyenne Vallée | 1998 |

## L'essayer sur son ordinateur

Prérequis : Python 3.10 ou plus récent et une clé API gratuite de Google AI Studio.

```
git clone https://github.com/aminetou-kane/agriconseil-walo.git
cd agriconseil-walo
pip install -r requirements.txt
```

Enregistrez votre clé comme variable d'environnement (ne la mettez jamais dans le dépôt) :

- Windows (puis ouvrez un nouveau terminal) : `setx GEMINI_API_KEY "votre_cle_ici"`
- macOS ou Linux : `export GEMINI_API_KEY="votre_cle_ici"`

Lancez l'application et le test de recherche :

```
streamlit run app.py
python tests/test_recherche.py
```

Pour la mise en ligne sur Streamlit Community Cloud, placez la clé dans les secrets de l'application sous le nom `GEMINI_API_KEY`.

## Limites et sécurité

- L'assistant **ne remplace pas un conseiller agricole** et **ne donne aucune dose** d'engrais, de semences ou de produits.
- Il n'a **pas de données propres à un village précis** : ses documents décrivent le Delta et la vallée. Certains sont anciens (l'un date de 1998) et les réponses indiquent l'année et la zone.
- Il ne connaît que ses six documents. Pour tout le reste, il répond qu'il n'a pas de source.
- La transcription de la voix peut se tromper, et la voix de lecture dépend du navigateur.
- Le wolof n'est **pas encore disponible**.
- L'IA peut faire des erreurs : les réponses doivent être vérifiées avec un technicien.

## Confidentialité

Les questions sont envoyées au service Gemini de Google pour produire la réponse : il ne faut donc pas y écrire d'informations personnelles. L'application n'enregistre pas les conversations : elles disparaissent à la fermeture de la page. Les clés API ne sont jamais stockées dans le dépôt.

## Ma contribution et les outils d'IA

Projet d'**Aminetou Kane**, étudiante en L3 Informatique (Systèmes d'Information) à l'Université Gaston Berger de Saint-Louis, Sénégal.

- **Mon travail :** choisir le problème et la zone, rédiger le cahier des charges, décider ce que l'assistant doit et ne doit pas faire (sources, pas de doses, réponses honnêtes « pas de source »), recueillir les bulletins de la SAED, installer et lancer le projet sur mon ordinateur, tester l'application et décider des changements d'interface et de périmètre.
- **Outils d'IA utilisés :** Claude (Anthropic) m'a aidée à écrire le code et les fiches de documents au cours d'une longue conversation, et Google Gemini rédige les réponses dans l'application. J'ai relu et testé les résultats ; les documents eux-mêmes sont crédités ci-dessus.

> À finir avant l'envoi : vérifier que cette partie décrit exactement votre contribution, et ajouter les liens de la démo en ligne et de la vidéo.

## Suite prévue

Le wolof (voix et texte) après validation avec des locuteurs, davantage de documents dont certains propres à la zone de Dagana, et un essai avec de vrais producteurs.

## Licence

À choisir.
