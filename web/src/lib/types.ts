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