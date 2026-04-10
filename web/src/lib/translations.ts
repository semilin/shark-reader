import type { InterfaceLang } from './types';

interface TranslationSet {
	library_title: string;
	search_texts: string;
	click_word: string;
	glossary: string;
	search_words: string;
	back_to_library: string;
	core_vocabulary: string;
	no_gloss: string;
	examples: string;
	select_word: string;
	select_word_detail: string;
	copy: string;
}

const translations: Record<InterfaceLang, TranslationSet> = {
	english: {
		library_title: 'Library',
		search_texts: 'Search texts...',
		click_word: 'Click a word to see its gloss',
		glossary: 'Glossary',
		search_words: 'Search words...',
		back_to_library: '← Library',
		core_vocabulary: 'Core vocabulary',
		no_gloss: 'No gloss available',
		examples: 'Examples:',
		select_word: 'Select a word',
		select_word_detail: 'Select a word to view its gloss',
		copy: 'Copy'
	},
	latin: {
		library_title: 'Bibliothēca',
		search_texts: 'Textūs quaere...',
		click_word: 'Verbum tange ut interpretātiōnem videās',
		glossary: 'Glossarium',
		search_words: 'Verba quaere...',
		back_to_library: '← Bibliothēca',
		core_vocabulary: 'Vocābulārium commune',
		no_gloss: 'Nulla interpretātiō',
		examples: 'Exempla:',
		select_word: 'Verbum ēlige',
		select_word_detail: 'Verbum ēlige ut interpretātiōnem videās',
		copy: 'Describere'
	},
	greek: {
		library_title: 'Βιβλιοθήκη',
		search_texts: 'Ζήτει συγγράμματα...',
		click_word: 'Ἅψαι λέξεως ἵνα τὴν ἐξήγησιν ἴδῃς',
		glossary: 'Γλωσσάριον',
		search_words: 'Ζήτει λέξεις...',
		back_to_library: '← Βιβλιοθήκη',
		core_vocabulary: 'Κοινὸν λεξιλόγιον',
		no_gloss: 'Οὐκ ἔστιν ἐξήγησις',
		examples: 'Παραδείγματα:',
		select_word: 'Ἐπέλεξον λέξιν',
		select_word_detail: 'Ἐπέλεξον λέξιν ἵνα τὴν ἐξήγησιν ἴδῃς',
		copy: 'Ἀντιγράφειν'
	}
};

export function t(key: keyof TranslationSet, lang: InterfaceLang): string {
	return translations[lang][key];
}

export const interfaceLangLabels: Record<InterfaceLang, string> = {
	english: 'English',
	latin: 'Latīnē',
	greek: 'Ἑλληνιστί'
};

export const languageLabels: Record<'latin' | 'greek', string> = {
	latin: 'Latīnē',
	greek: 'Ἑλληνιστί'
};
