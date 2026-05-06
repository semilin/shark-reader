import { base } from '$app/paths';
import type { GlobalStats, Language } from '$lib/types';

const statsCache: Map<Language, GlobalStats> = new Map();

export async function getStats(lang: Language): Promise<GlobalStats> {
	if (statsCache.has(lang)) {
		return statsCache.get(lang)!;
	}

	try {
		const response = await fetch(`${base}/stats/${lang}.json`);
		if (!response.ok) {
			throw new Error(`Failed to fetch stats for ${lang}`);
		}
		const stats = await response.json();
		statsCache.set(lang, stats);
		return stats;
	} catch (error) {
		console.error(`Error loading stats for ${lang}:`, error);
		return {};
	}
}
