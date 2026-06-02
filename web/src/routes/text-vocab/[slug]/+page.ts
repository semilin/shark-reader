import { vocabSlugs } from '$lib/generated/vocab-slugs';

export const prerender = true;

export function entries() {
	return vocabSlugs.map((slug) => ({ slug }));
}

export async function load({ params }: { params: { slug: string } }) {
	const { getTextVocabulary } = await import('$lib/data/text-vocab');
	const vocab = await getTextVocabulary(params.slug);
	return { vocab };
}