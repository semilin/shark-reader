import type { Dictionary, Gloss } from '../types';

let latinDictionary: Dictionary | null = null;
let greekDictionary: Dictionary | null = null;

async function loadDictionary(lang: 'latin' | 'greek'): Promise<Dictionary> {
	const response = await fetch(`/shark-reader/dictionaries/${lang}.json`);
	if (!response.ok) {
		throw new Error(`Failed to load ${lang} dictionary`);
	}
	const data: Record<string, Gloss> = await response.json();
	return new Map(Object.entries(data));
}

export async function getLatinDictionary(): Promise<Dictionary> {
	if (!latinDictionary) {
		latinDictionary = await loadDictionary('latin');
	}
	return latinDictionary;
}

export async function getGreekDictionary(): Promise<Dictionary> {
	if (!greekDictionary) {
		greekDictionary = await loadDictionary('greek');
	}
	return greekDictionary;
}

export function getDictionary(lang: 'latin' | 'greek'): Promise<Dictionary> {
	return lang === 'latin' ? getLatinDictionary() : getGreekDictionary();
}
