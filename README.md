# AgriConseil Walo

**English** | [Français](README.fr.md)

A French-language assistant for irrigated rice growing in the Senegal River Delta and valley (Dagana department). Ask a question by typing or speaking; the answer is written only from a small set of cited documents, and the sources are shown under every answer.

- **Live demo:** [https://agriconseil-walo.streamlit.app](https://agriconseil-walo.streamlit.app)
- **Hackathon:** Build Your First AI App 2026 (Devpost)

## The problem

Useful information about irrigated rice exists, but it is scattered across long technical reports, often in English, and hard to read on a phone. Many growers and the advisers who support them cannot easily get a reliable, sourced answer to a simple practical question such as "When should I harvest?".

## The solution

AgriConseil Walo answers practical questions in simple French and tells the user where each answer comes from. When the documents do not contain a reliable answer, the assistant says so instead of inventing one. It never gives fertilizer, seed or pesticide doses, because they depend on each plot and a mistake can damage a harvest.

**Who it is for:** rice growers in the Delta and valley of the Senegal River, the advisers and group leaders who support them, and students.

## Features

- Chat interface with a **microphone** inside the input box (spoken question) and a **"Listen to the answer"** button (the answer is read aloud by the browser voice).
- **Answers with sources:** document title, date, area covered and a link to the original document.
- **"No reliable source" behaviour:** the assistant explains what the documents cover and asks the user to be more precise.
- **Context of the question** (optional): theme and growth stage, used to guide the search.
- **Pages "Sources agricoles" and "À propos":** list of documents and why they were chosen; problem, public, how it works, limits, tools, transparency.
- **Conversation history** in the side menu, kept only during the visit.
- **Clear error messages:** free quota reached, service busy, no connection.
- **Mobile-friendly layout** (checked in a mobile-size browser window; real-phone tests still to be done).

## How it works

1. The user asks a question (text or voice). Voice is transcribed with Gemini.
2. The app searches short **knowledge notes** (one Markdown file per document, in `data/sources/`) with a simple keyword search weighted by how rare each word is.
3. The best passages, with their document title, date and area, are sent to **Gemini** with strict instructions: use only these passages, say when there is no source, never give doses, give the exact area and year, and finish with the numbers of the passages used.
4. The answer is streamed to the screen and the sources actually used are listed under it.
5. If no passage is found, Gemini is **not called**: the app answers that it has no reliable document on the point.

This is a small retrieval-augmented design, built without a vector database so that it is easy to inspect and explain.

## AI implementation

- **Model:** Google Gemini through Google AI Studio (`gemini-3.1-flash-lite`, with fallback to `gemini-3.5-flash-lite` and `gemini-3.5-flash`), used to write answers from the retrieved passages and to transcribe spoken questions.
- **Retrieval:** own code in `app.py` (word matching, rarity weighting, bonus when a question word matches the title of a passage).
- **Read aloud:** the Web Speech API of the browser (no extra service).
- **Evaluation:** `tests/test_recherche.py` runs 23 automated checks on the search step (20 questions that must find a given passage and 3 that must find nothing). It checks the search only, not the quality of Gemini's wording. Manual test grids are in `tests/questions_test.md` and `tests/questions_construites.md` (20 realistic questions written from the documents' themes; they do not come from real growers, and a test with real users is still to be done).

## Documents used

The app keeps only short rewritten notes and links, not the original documents. All documents belong to their authors.

| Document | Area | Year |
|---|---|---|
| AfricaRice, Innovation Brief 05, Good agricultural practice for rice ([link](https://www.africarice.org/_files/ugd/0839e4_055dfdaf6efa423abdb63735465956a2.pdf)) | Senegal River Delta | 2022 |
| AfricaRice, Innovation Brief 06, Agronomic options for salinity management ([link](https://www.africarice.org/_files/ugd/0839e4_8165cf02a7064e4d8bed5f9b4bc115ce.pdf)) | Delta and valley | 2022 |
| FAO, Krupnik et al., Improving irrigated rice production in the Senegal River Valley ([link](https://fao.org/fileadmin/user_upload/ippm/docs/1_Am%C3%A9liorer_du_riz.pdf)) | Middle Valley (Podor) | 2012 |
| JICA, preparatory study for the irrigated rice production project ([link](https://openjicareport.jica.go.jp/pdf/12353819.pdf)) | Dagana and Podor | 2019 |
| AfricaRice, Innovation Brief 01, RiceAdvice, fertilizer advice app ([link](https://www.africarice.org/_files/ugd/0839e4_2665069444494d459c9180e4db607de4.pdf)) | General tool for irrigated lowlands | 2022 |
| AfricaRice, Innovation Brief 02, RiceAdvice-WeedManager, weed management app ([link](https://www.africarice.org/_files/ugd/0839e4_7c68e4b917e94825ae9b76033387996d.pdf)) | General tool, with a trial in Senegal | 2022 |
| SAED, "Écho PPRI" bulletins (no online link yet) | Dagana and Podor | Oct. 2025 to Mar. 2026 |
| Wopereis et al., Preserving soil quality under irrigation in the Senegal River Valley ([link](https://library.wur.nl/ojs/index.php/njas/article/download/500/214)) | Delta and Middle Valley | 1998 |

## Try it locally

Requirements: Python 3.10 or later and a free Google AI Studio API key.

```
git clone https://github.com/aminetou-kane/agriconseil-walo.git
cd agriconseil-walo
pip install -r requirements.txt
```

Set your key as an environment variable (never put it in the repository):

- Windows (then open a new terminal): `setx GEMINI_API_KEY "your_key_here"`
- macOS or Linux: `export GEMINI_API_KEY="your_key_here"`

Run the app and the search test:

```
streamlit run app.py
python tests/test_recherche.py
```

When deployed on Streamlit Community Cloud, put the key in the app secrets as `GEMINI_API_KEY`.

## Limits and safety

- The assistant **does not replace an agricultural adviser** and **gives no doses** of fertilizer, seeds or products.
- It has **no data specific to a single village**: its documents describe the Delta and the valley. Some are old (one dates from 1998) and the answers say the year and area.
- It only knows its eight documents. For anything else it answers that it has no source.
- Voice transcription can make mistakes, and the read-aloud voice depends on the browser.
- Wolof is **not available yet**.
- AI can make mistakes: answers should be checked with a technician.

## Privacy

Questions are sent to Google's Gemini service to produce the answer, so users should not type personal information. The app does not save conversations: they disappear when the page is closed. API keys are never stored in the repository.

## My contribution and AI tools

Project by **Aminetou Kane**, Master 1 student in IADM (Artificial Intelligence and Big Data), after a bachelor's degree in Computer Science (Information Systems) at Université Gaston Berger, Saint-Louis, Senegal.

**What I did**

- I chose the subject from the reality of farming in Senegal and wrote a full specification before starting.
- I set the rules of the assistant: always show the sources, say "no source" instead of inventing an answer, and never give doses.
- I decided to focus on the Dagana area and the Delta, where more documents exist.
- I found and gathered the SAED bulletins.
- I asked for voice input and read-aloud answers for people who do not write, and decided to keep Wolof for later, until it can be checked with speakers.
- I decided the interface: a clean home page like a modern assistant, no suggested questions, the warning under the input box, conversation history in the menu, and "Sources" and "About" pages.
- I installed and ran the project on my computer (Python, Streamlit, Gemini key, GitHub repository) and solved problems along the way.
- I tested the app, found errors (for example a wrong "no source" answer about harvest time) and asked for them to be fixed.
- I tested the app on my phone and put it online on Streamlit Community Cloud.

**AI tools used:** Claude (Anthropic) helped me write the code and the document notes in a long conversation, and Google Gemini writes the answers inside the app. I tested the results and checked them against my specification; the documents themselves are credited above.

**What I learned**

- Searching documents first, before asking an AI model, makes answers more reliable and easier to check.
- A free API has limits and outages, so the app needs clear error messages and backup models.
- Testing matters: a wrong answer can come from the search step, not from the AI.
- Using Git and GitHub, and keeping the API key secret (environment variables and secrets).
- Designing for users who read little: voice, a simple interface and honest limits.
- Working with an AI assistant while keeping the decisions: what to build, what not to do, and how it should look.

## Roadmap

Wolof (voice and text) after validation with speakers, more documents including ones specific to the Dagana area, and a test with real growers.
