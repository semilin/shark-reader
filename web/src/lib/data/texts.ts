import type { AnnotatedText, TextMetadata, Token } from '../types';

const TEXT_FILES: Omit<TextMetadata, 'path'>[] = [
	{
		title: 'Aeneis, Prīmus Liber',
		author: 'Publius Vergilius Marō',
		language: 'latin',
		work_type: 'poem'
	},
	{
		title: 'Ἀπολογία Σωκράτους',
		author: 'Πλάτων',
		language: 'greek',
		work_type: 'dialogue'
	},
	{
		title: 'Κρίτων',
		author: 'Πλάτων',
		language: 'greek',
		work_type: 'dialogue'
	},
	{
		title: 'Μένων',
		author: 'Πλάτων',
		language: 'greek',
		work_type: 'dialogue'
	}
];

function getPathFromTitle(title: string): string {
	const pathMap: Record<string, string> = {
		'Aeneis, Prīmus Liber': 'Aeneid1',
		'Ἀπολογία Σωκράτους': 'Apology',
		'Κρίτων': 'Crito',
		'Μένων': 'Meno'
	};
	return pathMap[title] || title;
}

export function getAvailableTexts(): TextMetadata[] {
	return TEXT_FILES.map((meta) => ({
		...meta,
		path: `/shark-reader/texts/${getPathFromTitle(meta.title)}.annotated.json`
	}));
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
