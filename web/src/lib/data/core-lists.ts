let latinCore: Set<string> | null = null;
let greekCore: Set<string> | null = null;

function stripMacrons(word: string): string {
	return word.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

function expandHeadword(raw: string): string[] {
	const words = raw.split(/[\s,;–—/]+/).filter(Boolean);
	const result: string[] = [];
	for (const w of words) {
		const lower = w.toLowerCase();
		result.push(lower);
		const stripped = stripMacrons(lower);
		if (stripped !== lower) {
			result.push(stripped);
		}
	}
	return result;
}

function parseCSV(content: string): Set<string> {
	const lines = content.trim().split('\n');
	const core = new Set<string>();
	for (let i = 1; i < lines.length; i++) {
		const line = lines[i];
		const match = line.match(/^"([^"]+)"/);
		const headword = match ? match[1] : line.split(',')[0];
		const expanded = expandHeadword(headword);
		for (const w of expanded) {
			core.add(w);
		}
	}
	return core;
}

async function loadCoreList(lang: 'latin' | 'greek'): Promise<Set<string>> {
	const response = await fetch(`/shark-reader/core_lists/${lang}-core-list.csv`);
	if (!response.ok) {
		throw new Error(`Failed to load ${lang} core list`);
	}
	const content = await response.text();
	return parseCSV(content);
}

export async function getLatinCore(): Promise<Set<string>> {
	if (!latinCore) {
		latinCore = await loadCoreList('latin');
	}
	return latinCore;
}

export async function getGreekCore(): Promise<Set<string>> {
	if (!greekCore) {
		greekCore = await loadCoreList('greek');
	}
	return greekCore;
}

export function getCoreList(lang: 'latin' | 'greek'): Promise<Set<string>> {
	return lang === 'latin' ? getLatinCore() : getGreekCore();
}
