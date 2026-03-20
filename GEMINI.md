# DolphinDict - Immersive Multi-Language Reader

DolphinDict is an immersive reader for Latin and Ancient Greek that provides LLM-generated glosses restricted to core vocabulary. It combines a Rust/Iced GUI for the reading experience with a Python-based pipeline for text annotation and dictionary expansion.

## Project Structure

- `src/main.rs`: The interactive GUI built with Iced 0.14.0.
- `main.py`: CLI tool for annotating texts (lemmatization) and generating glosses via OpenRouter (Gemini models).
- `core_lists/`: Contains Dickinson Core Vocab lists (`latin-core-list.csv`, `greek-core-list.csv`).
- `dictionaries/`: JSON dictionaries containing immersive glosses (`latin.json`, `greek.json`).
- `texts/`: Annotated token streams for reading (`book1.annotated.json`, `Μένων.annotated.json`).

## Core Technologies

- **Rust:** Iced 0.14.0 (GUI), `tokio` (async), `serde` (serialization), `csv` (data loading).
- **Python:** `pandas` (data processing), `openai` (OpenRouter API client), `concurrent.futures` (parallel annotation).
- **LLMs:** 
  - `google/gemini-3.1-flash-lite-preview`: Fast contextual annotation/lemmatization.
  - `google/gemini-3-flash-preview`: High-quality immersive gloss generation.

## Getting Started

### Prerequisites

- Rust (edition 2024)
- Python 3.12+
- OpenRouter API Key (configured in `main.py`)

### Commands

#### GUI Application
```bash
cargo run
```

#### Annotating Text
Converts raw text into a rich, lemmatized token stream.
```bash
python main.py annotate <file_path> --lang [latin|greek]
```

#### Generating Glosses
Expands the dictionary by scanning annotated files for missing non-core words.
```bash
python main.py gloss --lang [latin|greek] --input-json texts/<file>.annotated.json
```

## Data Formats

### Rich Tokens (`.annotated.json`)
Every element of the text is a token with a type `t`:
- `"w"`: Word (contains original word `w` and lemma `l`).
- `"p"`: Punctuation or whitespace.
- `"n"`: Newline.
- `"s"`: Speaker (e.g., "Socrates:").
- `"m"`: Section Marker (e.g., "[70a]").

### Immersive Glosses
Stored in `dictionaries/`, glosses use simple sentences composed ONLY of core vocabulary words to explain non-core terms.

## Development Conventions

- **Surgical Updates:** When modifying `src/main.rs`, maintain the Iced 0.14 application pattern (`boot`, `update`, `view`).
- **Data Integrity:** Ensure glosses strictly follow the core vocabulary constraints as enforced in the Python `generate_gloss` logic.
- **Resiliency:** The Rust JSON parser uses `serde_json::Value` to filter out malformed dictionary entries safely.
- **Language Support:** Maintain polytonic Ancient Greek accentuation and respect Latin macrons where applicable.
- **Parallelism:** Use `ThreadPoolExecutor` in Python for high-performance annotation.
