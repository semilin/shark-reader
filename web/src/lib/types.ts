export interface Gloss {
	definition: string;
	examples: string[];
	synonyms?: string[];
}

export type TokenType = 'w' | 'p' | 'n' | 's' | 'm';

export interface Token {
	t: TokenType;
	w: string;
	l?: string;
}

export type Language = 'latin' | 'greek';

export type WorkType = 'poem' | 'dialogue' | 'prose';

export interface TextMetadata {
	title: string;
	author: string;
	language: Language;
	work_type: WorkType;
	path: string;
}

export interface AnnotatedText {
	metadata: Omit<TextMetadata, 'path'>;
	tokens: Token[];
}

export type Dictionary = Map<string, Gloss>;

export interface WordStats {
	total: number;
	frequencyScore: number;
	forms: [string, number][];
	texts: { title: string; count: number }[];
}

export type GlobalStats = Record<string, WordStats>;

export type InterfaceLang = 'english' | 'latin' | 'greek';
