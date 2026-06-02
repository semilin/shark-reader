import type { TextVocabulary } from '../types';

const cache = new Map<string, TextVocabulary>();

export async function getTextVocabulary(slug: string): Promise<TextVocabulary> {
	if (cache.has(slug)) {
		return cache.get(slug)!;
	}
	const response = await fetch(`/shark-reader/text-vocab/${slug}.vocab.json`);
	if (!response.ok) {
		throw new Error(`Failed to load vocabulary for ${slug}`);
	}
	const data: TextVocabulary = await response.json();
	cache.set(slug, data);
	return data;
}

export async function getTextVocabIndex(): Promise<{ slug: string; title: string; author: string; language: string }[]> {
	const response = await fetch('/shark-reader/text-vocab/index.json');
	if (!response.ok) {
		throw new Error('Failed to load text vocab index');
	}
	return response.json();
}