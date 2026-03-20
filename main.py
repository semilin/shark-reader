import argparse
import os
import sys
import pandas as pd
import json
import re
import concurrent.futures
from openai import OpenAI

# API Configuration
OPENROUTER_KEY = "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"
if not OPENROUTER_KEY:
    print("OPENROUTER_API_KEY environment variable must be set.")
    sys.exit(1)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_KEY,
)

# Models
# Using Flash Lite for fast, cheap annotation and Flash for higher-quality glosses
ANNOTATION_MODEL = "google/gemini-3.1-flash-lite-preview"
GLOSS_MODEL = "google/gemini-3-flash-preview"

# Language Configurations
CONFIGS = {
    "latin": {
        "core_vocab": "./latin-core-list.csv",
        "name": "Latin",
        "example_word": "sella",
        "example_response": '{"definition": "Sella est rēs in quā homō sedet. Haec rēs quattuor pedēs habet et in casā vel in villā invenītur.", "examples": ["Marcus in sellā sedet.", "Puer fessus ad sellam currit."]}',
        "lemma_instructions": "Put in primary principle parts (first person present active singular for verbs, nominative singular for nouns, etc.). Only the primary principle part should be listed. Don't use macrons. Capitalize proper nouns, but do not capitalize regular words."
    },
    "greek": {
        "core_vocab": "./greek-core-list.csv",
        "name": "Ancient Greek",
        "example_word": "ἵππος",
        "example_response": '{"definition": "Ὁ ἵππος ἐστὶ ζῷον μέγα ὃ ἐν τῷ ἀγρῷ τρέχει καὶ τοὺς ἀνθρώπους φέρει.", "examples": ["Ὁ παῖς ἐπὶ τοῦ ἵππου κάθηται.", "Οἱ ἵπποι εἰς τὴν πόλιν τρέχουσιν."]}',
        "lemma_instructions": "Put in primary principle parts (first person present active singular for verbs, nominative singular for nouns, etc.). Use proper polytonic accentuation. Capitalize proper nouns, but do not capitalize regular words."
    }
}

def query_openrouter(prompt, model=GLOSS_MODEL):
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

def tokenize_rich(text):
    # Regex groups for different token types
    # Group 1: Markers [70a]
    # Group 2: Speakers Socrates:
    # Group 3: Words (Latin/Greek/macrons/accents)
    # Group 4: Newline
    # Group 5: Punctuation/Whitespace (anything else)
    pattern = r"(\[\w+\])|(^[\w\s\u0370-\u03FF\u1F00-\u1FFF]+:)|([\w\u00C0-\u017F\u0370-\u03FF\u1F00-\u1FFF]+)|(\n)|([^\w\s\n\[\]]+)|(\s+)"
    
    tokens = []
    for match in re.finditer(pattern, text, flags=re.MULTILINE):
        m1, m2, m3, m4, m5, m6 = match.groups()
        if m1: tokens.append({"t": "m", "w": m1}) # Marker
        elif m2: tokens.append({"t": "s", "w": m2}) # Speaker
        elif m3: tokens.append({"t": "w", "w": m3, "l": ""}) # Word (placeholder lemma)
        elif m4: tokens.append({"t": "n"}) # Newline
        elif m5: tokens.append({"t": "p", "w": m5}) # Punctuation
        elif m6: tokens.append({"t": "p", "w": m6}) # Whitespace
        
    return tokens

def get_annotated_sentence_lemmas(sentence_text, config):
    if not sentence_text.strip():
        return []
    prompt = (
        f"Context: {config['name']} literature.\n"
        f"Directions: Lemmatize every word in the following sentence. Return a JSON list of objects, "
        f"where each object has 'w' (original word) and 'l' (dictionary lemma). "
        f"{config['lemma_instructions']}\n"
        f"Sentence: {sentence_text}\n"
        f"Example format: [{{'w': 'arma', 'l': 'arma'}}, {{'w': 'virumque', 'l': 'vir'}}, ...]"
    )
    try:
        res = query_openrouter(prompt, model=ANNOTATION_MODEL)
        if isinstance(res, dict):
            for val in res.values():
                if isinstance(val, list):
                    return val
        return res
    except Exception as e:
        print(f"  Error in annotation: {e}.")
        return []

def generate_gloss(word, config, vocab_list):
    prompt = (
        f'# CORE VOCABULARY\n{vocab_list}\n'
        f'# DIRECTIONS\nGenerate an immersive {config["name"]} gloss for the given {config["name"]} word. '
        f'The definition should, in a simple sentence or two, explain the meaning of the word using ONLY the vocab words provided in the CORE VOCABULARY. '
        f'Further, generate 2-4 example sentences using the word that cover its basic usage and give extra context to the definition (again, using only core vocab words or common {config["name"]} names). '
        f'Each example should use the word in a different form. Respond with JSON. '
        f'For example, if the word were "{config["example_word"]}", respond with {config["example_response"]}.\n'
        f'The word is: {word}.'
    )
    return query_openrouter(prompt, model=GLOSS_MODEL)

def cmd_annotate(args):
    config = CONFIGS[args.lang]

    with open(args.file, 'r', encoding='utf-8') as f:
        full_text = f.read()

    print("Step 1: Tokenizing rich text...")
    rich_tokens = tokenize_rich(full_text)
    
    # Chunk into sentences based on punctuation in rich_tokens
    sentences = []
    current_sentence_indices = []
    for i in range(len(rich_tokens)):
        current_sentence_indices.append(i)
        if rich_tokens[i]["t"] == "p" and any(c in rich_tokens[i]["w"] for c in ".?;·"):
            sentences.append(current_sentence_indices)
            current_sentence_indices = []
    if current_sentence_indices:
        sentences.append(current_sentence_indices)

    print(f"Step 2: Annotating {len(sentences)} sentences in parallel (max_workers=20)...")
    
    # Process sentences in parallel
    results = [None] * len(sentences)
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_idx = {}
        for idx, sent_indices in enumerate(sentences):
            sent_words = [rich_tokens[i]["w"] for i in sent_indices if rich_tokens[i]["t"] == "w"]
            if sent_words:
                sent_text = " ".join(sent_words)
                future = executor.submit(get_annotated_sentence_lemmas, sent_text, config)
                future_to_idx[future] = idx
        
        completed = 0
        for future in concurrent.futures.as_completed(future_to_idx):
            idx = future_to_idx[future]
            results[idx] = future.result()
            completed += 1
            if completed % 10 == 0 or completed == len(future_to_idx):
                print(f"  Completed {completed}/{len(future_to_idx)} sentences...")

    # Map back to rich tokens
    for idx, lemmas_res in enumerate(results):
        if lemmas_res is None: continue
        
        sent_indices = sentences[idx]
        word_idx_in_sent = 0
        for token_idx in sent_indices:
            if rich_tokens[token_idx]["t"] == "w":
                if word_idx_in_sent < len(lemmas_res):
                    rich_tokens[token_idx]["l"] = lemmas_res[word_idx_in_sent]["l"]
                else:
                    rich_tokens[token_idx]["l"] = rich_tokens[token_idx]["w"].lower()
                word_idx_in_sent += 1

    out_anno = args.out if args.out else f"{os.path.splitext(args.file)[0]}.annotated.json"
    with open(out_anno, 'w', encoding='utf-8') as f:
        json.dump(rich_tokens, f, ensure_ascii=False, indent=2)
    print(f"Annotated text saved to {out_anno}")

def cmd_gloss(args):
    config = CONFIGS[args.lang]
    vocab_df = pd.read_csv(config["core_vocab"])
    vocab_list = set(vocab_df['Headword'].str.lower().tolist())
    
    dict_path = args.dict if args.dict else ("greek_dict.json" if args.lang == "greek" else "dict.json")
    dictionary = {}
    if os.path.exists(dict_path):
        with open(dict_path, 'r', encoding='utf-8') as f:
            try:
                dictionary = json.load(f)
            except:
                pass

    encountered_lemmas = set()
    if args.input_json:
        with open(args.input_json, 'r', encoding='utf-8') as f:
            tokens = json.load(f)
            for t in tokens:
                if t["t"] == "w":
                    encountered_lemmas.add(t['l'])
    elif args.word:
        encountered_lemmas.add(args.word)
    else:
        print("Error: Must provide either --input-json or --word")
        return

    missing_lemmas = sorted([
        l for l in encountered_lemmas 
        if l and l.lower() not in vocab_list and l not in dictionary
    ])
    
    print(f"Expanding dictionary ({len(missing_lemmas)} new lemmas)...")
    for i, lemma in enumerate(missing_lemmas):
        print(f"  [{i+1}/{len(missing_lemmas)}] Generating gloss for '{lemma}'...")
        while True:
            try:
                gloss = generate_gloss(lemma, config, list(vocab_list))
                dictionary[lemma] = gloss
                with open(dict_path, 'w', encoding='utf-8') as f:
                    json.dump(dictionary, f, ensure_ascii=False, indent=2)
                break
            except Exception as e:
                print(f"    Error: {e}. Retrying...")
    print(f"Done! Dictionary '{dict_path}' updated.")

def main():
    parser = argparse.ArgumentParser(description="DolphinDict CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Annotate command
    parser_anno = subparsers.add_parser("annotate", help="Annotate a text file with lemmas and formatting")
    parser_anno.add_argument("file", help="Input text file")
    parser_anno.add_argument("--lang", choices=["latin", "greek"], required=True)
    parser_anno.add_argument("--out", help="Output JSON path")
    parser_anno.set_defaults(func=cmd_annotate)

    # Gloss command
    parser_gloss = subparsers.add_parser("gloss", help="Generate immersive glosses for missing words")
    parser_gloss.add_argument("--lang", choices=["latin", "greek"], required=True)
    parser_gloss.add_argument("--input-json", help="Annotated JSON file to scan for new words")
    parser_gloss.add_argument("--word", help="Single word to generate gloss for")
    parser_gloss.add_argument("--dict", help="Dictionary file to update")
    parser_gloss.set_defaults(func=cmd_gloss)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
