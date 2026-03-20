import argparse
import os
import sys
import pandas as pd
import json
import re
from openai import OpenAI

# API Configuration
KEY = "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"
if not KEY:
    print("OPENROUTER_API_KEY environment variable must be set.")
    sys.exit(1)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=KEY,
)
MODEL = "google/gemini-3-flash-preview"

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

def basic_completion(prompt, json_mode=True):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"} if json_mode else {}
    )
    return response

def generate_gloss(word, config, vocab):
    prompt = (
        f'# CORE VOCABULARY\n{vocab}\n'
        f'# DIRECTIONS\nGenerate an immersive {config["name"]} gloss for the given {config["name"]} word. '
        f'The definition should, in a simple sentence or two, explain the meaning of the word using ONLY the vocab words provided in the CORE VOCABULARY. '
        f'Further, generate 2-4 example sentences using the word that cover its basic usage and give extra context to the definition (again, using only core vocab words or common {config["name"]} names). '
        f'Each example should use the word in a different form. Respond with JSON. '
        f'For example, if the word were "{config["example_word"]}", respond with {config["example_response"]}.\n'
        f'The word is: {word}.'
    )
    response = basic_completion(prompt)
    return json.loads(response.choices[0].message.content)

def get_lemmas(text, config, vocab):
    prompt = (
        f'# CORE VOCABULARY\n{vocab}\n'
        f'# DIRECTIONS\nGiven {config["name"]} text, return each unique lemma not found in the CORE VOCABULARY in a JSON list. '
        f'For example, return {{"lemmas": ["lemma1", "lemma2"]}}. Since words in the core vocabulary should be omitted. '
        f'{config["lemma_instructions"]} '
        f'If the string is empty or contains only lemmas found in the Core Vocabulary, simply respond with an empty list: {{"lemmas": []}}.\n'
        f"# Text\n{text}"
    )
    response = basic_completion(prompt)
    return json.loads(response.choices[0].message.content)

def clean_text(text):
    # Remove section markers like [70a], [71b]
    text = re.sub(r'\[\w+\]', '', text)
    # Remove speaker names at start of lines (e.g. Μένων:, Σωκράτης:)
    text = re.sub(r'^[Α-Ωα-ω\s]+:', '', text, flags=re.MULTILINE)
    return text.strip()

def chunk_text(text, target_words=100):
    words = text.split()
    for i in range(0, len(words), target_words):
        yield ' '.join(words[i:i + target_words])

def main():
    parser = argparse.ArgumentParser(description="Generate immersive glosses for Latin or Greek texts.")
    parser.add_argument("file", help="Input text file path")
    parser.add_argument("--lang", choices=["latin", "greek"], required=True, help="Language of the text")
    parser.add_argument("--out", default="dict.json", help="Output JSON dictionary path")
    args = parser.parse_args()

    config = CONFIGS[args.lang]
    vocab_df = pd.read_csv(config["core_vocab"])
    vocab_list = vocab_df['Headword'].tolist()

    with open(args.file, 'r', encoding='utf-8') as f:
        full_text = clean_text(f.read())

    all_lemmas = set()
    chunks = list(chunk_text(full_text))
    
    print(f"Processing {len(chunks)} chunks of text...")
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i+1}/{len(chunks)}: {chunk[:50]}...")
        while True:
            try:
                res = get_lemmas(chunk, config, vocab_list)
                new_lemmas = [l for l in res['lemmas'] if l not in vocab_list]
                old_len = len(all_lemmas)
                all_lemmas.update(new_lemmas)
                new_len = len(all_lemmas)
                print(f"  Found {len(new_lemmas)} non-core lemmas ({new_len-old_len} new)")
                break
            except Exception as e:
                print(f"  Error in get_lemmas: {e}. Retrying...")

    print(f"Total unique non-core lemmas found: {len(all_lemmas)}")
    
    # Load existing dict if it exists to avoid re-generating
    dictionary = {}
    if os.path.exists(args.out):
        with open(args.out, 'r', encoding='utf-8') as f:
            try:
                dictionary = json.load(f)
            except:
                pass

    for i, lemma in enumerate(all_lemmas):
        if lemma in dictionary:
            continue
            
        print(f"Generating gloss for {lemma} ({i+1}/{len(all_lemmas)})...")
        while True:
            try:
                gloss = generate_gloss(lemma, config, vocab_list)
                dictionary[lemma] = gloss
                # Save incrementally
                with open(args.out, 'w', encoding='utf-8') as f:
                    json.dump(dictionary, f, ensure_ascii=False, indent=2)
                break
            except Exception as e:
                print(f"  Error in generate_gloss: {e}. Retrying...")

    print(f"Done! Dictionary saved to {args.out}")

if __name__ == "__main__":
    main()
