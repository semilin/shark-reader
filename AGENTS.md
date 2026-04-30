# SharkReader - Immersive Multi-Language Reader

SharkReader is an immersive reader for Latin and Ancient Greek that provides LLM-generated glosses restricted to core vocabulary. It consists of a **SvelteKit web frontend** for reading and a **Python CLI pipeline** for text annotation and dictionary expansion.

## Project Structure

### Web Frontend (`web/`)

A SvelteKit app (Svelte 5 runes, TypeScript) built with Vite and deployed as a static site with PWA support.

- **`src/routes/+page.svelte`**: Library page — lists available texts with search/filter, links to reader and glossary.
- **`src/routes/reader/+page.svelte`**: Reader page — loads an annotated text, displays it with clickable words, shows glosses in a side panel (desktop) or bottom sheet (mobile). Supports shift-click range selection and keyboard shortcuts (Escape to clear, copy selected text).
- **`src/routes/glossary/[lang]/+page.svelte`**: Glossary page — browsable dictionary with search and copyable definitions/examples.
- **`src/lib/components/reader/`**: `TextDisplay`, `GlossPanel`, `Word` — core reading UI.
- **`src/lib/components/library/`**: `TextCard` — text listing cards.
- **`src/lib/components/common/`**: Reusable UI (`Button`, `Card`, `Badge`, `SearchInput`, `LanguageToggle`).
- **`src/lib/stores/app-state.ts`**: Global store for interface language (English / Latin / Greek).
- **`src/lib/translations.ts`**: Trilingual UI strings.
- **`src/lib/data/`**: Async loaders for texts, dictionaries, and Dickinson core vocabulary lists.
- **`src/lib/types.ts`**: Shared TypeScript types (`Token`, `Gloss`, `AnnotatedText`, etc.).
- **`static/`**: Annotated texts (`.annotated.json`), dictionaries (`.json`), and core vocab CSVs served as static assets.

### Python Pipeline (`sharkreader/`)

A Python package for preparing texts and generating immersive glosses via OpenRouter (Gemini models).

- **`main.py`**: CLI entry point. Commands:
  - `annotate <file> --lang [latin|greek]` — LLM-based lemmatization of missing words.
  - `gloss --lang [latin|greek] --input-json <file>` — generates glosses for non-core lemmas and appends to dictionary.
  - `repair <file> --lang [latin|greek]` — token cleanup and normalization.
  - `from-xml <file> --work-type [poem|dialogue|prose]` — converts Perseus TEI XML to annotated JSON.
- **`sharkreader/annotator.py`**: Sentence chunking and LLM lemma annotation.
- **`sharkreader/glossgen.py`**: Core-vocabulary-constrained gloss generation with retry logic.
- **`sharkreader/tokenizer.py`**: Rich tokenization (words, punctuation, newlines, speakers, section markers).
- **`sharkreader/config.py`**: Per-language configuration (word patterns, models, core vocab paths).

### Data

- **`web/static/texts/`**: Annotated token streams (e.g. `Meno.annotated.json`, `Aeneid1.annotated.json`).
- **`web/static/dictionaries/`**: JSON gloss dictionaries (`latin.json`, `greek.json`).
- **`web/static/core_lists/`**: Dickinson Core Vocab lists (`latin-core-list.csv`, `greek-core-list.csv`).

## Core Technologies

- **Frontend:** SvelteKit 2, Svelte 5 (runes), TypeScript, Vite, `@sveltejs/adapter-static`, `@vite-pwa/sveltekit`.
- **Python:** `pandas`, `openai` (OpenRouter client), `concurrent.futures`, `pytest`.
- **LLMs:**
  - `google/gemini-2.5-flash-preview-05-20`: Fast contextual annotation/lemmatization.
  - `google/gemini-2.5-flash-preview-05-20`: High-quality immersive gloss generation.

## Data Formats

### Rich Tokens (`.annotated.json`)
Every element is a token with type `t`:
- `"w"`: Word (contains original `w` and lemma `l`).
- `"p"`: Punctuation or whitespace.
- `"n"`: Newline.
- `"s"`: Speaker (e.g. "Socrates:").
- `"m"`: Section Marker (e.g. "[70a]").

### Immersive Glosses
Stored in `dictionaries/`, each entry has a `definition` and `examples[]`. Glosses use simple sentences composed **only** of core vocabulary words to explain non-core terms.

## Getting Started

### Prerequisites
- Node.js 20+ (for web frontend)
- Python 3.12+ (for pipeline)
- OpenRouter API Key (set `OPENROUTER_API_KEY`)

### Web Frontend
```bash
cd web
npm install
npm run dev        # dev server
npm run build      # static build -> web/build/
```

### Pipeline Commands
```bash
# Convert Perseus TEI XML to annotated JSON
python main.py from-xml texts/meno.xml --work-type dialogue

# Annotate missing lemmas
python main.py annotate texts/meno.annotated.json --lang greek

# Generate glosses for non-core words
python main.py gloss --lang greek --input-json texts/meno.annotated.json

# Run tests
pytest tests/
```

## Development Conventions

- **Svelte 5 Runes:** Use `$state`, `$derived`, `$effect`, `$props` throughout the frontend.
- **Static Assets:** All data (texts, dictionaries, core lists) is fetched at runtime from `/shark-reader/...` static paths.
- **Data Integrity:** Glosses must strictly follow core vocabulary constraints as enforced in `glossgen.generate_gloss`.
- **Language Support:** Maintain polytonic Ancient Greek accentuation and respect Latin macrons where applicable.
- **Parallelism:** Use `ThreadPoolExecutor` in Python for high-performance annotation.
- **PWA:** The app is configured as a PWA with offline caching via Workbox.
