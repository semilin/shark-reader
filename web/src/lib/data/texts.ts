import type { AnnotatedText, TextMetadata, Token } from '../types';

export async function getAvailableTexts(): Promise<TextMetadata[]> {
	const response = await fetch('/shark-reader/texts/index.json');
	if (!response.ok) {
		throw new Error('Failed to load texts index');
	}
	return response.json();
}

export async function loadText(path: string): Promise<AnnotatedText> {
	const response = await fetch(path);
	if (!response.ok) {
		throw new Error(`Failed to load text: ${path}`);
	}
	return response.json();
}

export function computeLemmaFrequencies(tokens: Token[]): Map<string, number> {
	const counts = new Map<string, number>();
	let totalWords = 0;

	for (const token of tokens) {
		if (token.t === 'w' && token.l) {
			counts.set(token.l, (counts.get(token.l) || 0) + 1);
			totalWords++;
		}
	}

	const frequencies = new Map<string, number>();
	for (const [lemma, count] of counts) {
		frequencies.set(lemma, (count / totalWords) * 100);
	}

	return frequencies;
}
