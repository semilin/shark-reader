export interface VocabEntry {
	lemma: string;
	count: number;
}

export interface TextVocabulary {
	title: string;
	author: string;
	language: Language;
	workType: WorkType;
	categories: {
		core: VocabEntry[];
		frequent: VocabEntry[];
		medium: VocabEntry[];
		rare: VocabEntry[];
		hapax: string[];
	};
}

export type TokenType = 'w' | 'p' | 'n' | 's' | 'm';

export interface Token {
	t: TokenType;
	w: string;
	l: string;
	s?: string;  // substitute: a simple paraphrase/replacement for tricky words
}

export interface Gloss {
	definition: string;
	examples: string[];
	synonyms?: string[];
}

export type Dictionary = Map<string, Gloss>;

export interface TextMetadata {
	title: string;
	author: string;
	language: Language;
	work_type: WorkType;
}

export interface AnnotatedText {
	metadata: TextMetadata;
	tokens: Token[];
}

export type Language = 'latin' | 'greek';
export type WorkType = 'poem' | 'dialogue' | 'prose';
export type InterfaceLang = 'english' | 'latin' | 'greek';

export interface GlobalStats {
	totalTexts: number;
	totalWords: number;
}

export interface WordStats {
	lemma: string;
	frequency: number;
	isCore: boolean;
}