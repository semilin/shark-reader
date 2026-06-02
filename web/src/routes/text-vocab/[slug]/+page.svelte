<script lang="ts">
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { Button } from '$lib/components/common';
	import { appState } from '$lib/stores/app-state';
	import { languageLabels } from '$lib/translations';
	import type { TextVocabulary } from '$lib/types';
	import Badge from '$lib/components/common/Badge.svelte';

	interface Props {
		data: { vocab: TextVocabulary };
	}

	let { data }: Props = $props();
	let vocab = $derived(data.vocab);

	let openSections = $state<Record<string, boolean>>({
		core: true,
		frequent: false,
		medium: false,
		rare: false,
		hapax: false
	});

	function toggleSection(key: string) {
		openSections[key] = !openSections[key];
	}

	function goBack() {
		goto(base || '/');
	}

	function goToGlossary(lemma: string) {
		goto(`${base}/glossary/${vocab.language}?word=${encodeURIComponent(lemma)}`);
	}

	function sectionCount(key: string): number {
		const cat = vocab.categories[key as keyof typeof vocab.categories];
		if (key === 'hapax') return (cat as string[]).length;
		return (cat as { lemma: string; count: number }[]).length;
	}

	const sectionLabels: Record<string, string> = {
		core: 'Core Vocabulary',
		frequent: 'Frequent',
		medium: 'Medium Frequency',
		rare: 'Rare',
		hapax: 'Hapax Legomena (appears once)'
	};
</script>

<svelte:head>
	<title>{vocab.title} - Vocabulary - SharkReader</title>
</svelte:head>

<div class="vocab-page">
	<header class="vocab-header">
		<Button onclick={goBack}>← Library</Button>
		<div class="vocab-title-group">
			<h1 class="vocab-title">{vocab.title}</h1>
			<p class="vocab-author">{vocab.author} <Badge variant="primary">{languageLabels[vocab.language]}</Badge></p>
		</div>
	</header>

	<div class="vocab-content">
		{#each ['core', 'frequent', 'medium', 'rare', 'hapax'] as key}
			{#if sectionCount(key) > 0}
				<div class="category-section">
					<button
						class="category-header"
						onclick={() => toggleSection(key)}
					>
						<span class="category-toggle">{openSections[key] ? '▾' : '▸'}</span>
						<span class="category-label">{sectionLabels[key]}</span>
						<span class="category-count">{sectionCount(key)}</span>
					</button>

					{#if openSections[key]}
						<div class="word-list">
							{#if key === 'hapax'}
								{#each vocab.categories.hapax as lemma}
									<button
										class="word-entry"
										onclick={() => goToGlossary(lemma)}
									>
										<span class="word-lemma">{lemma}</span>
										<span class="word-count">1</span>
									</button>
								{/each}
							{:else}
								{@const entries = vocab.categories[key as 'core' | 'frequent' | 'medium' | 'rare']}
								{#each entries as entry}
									<button
										class="word-entry"
										onclick={() => goToGlossary(entry.lemma)}
									>
										<span class="word-lemma">{entry.lemma}</span>
										<span class="word-count">{entry.count}</span>
									</button>
								{/each}
							{/if}
						</div>
					{/if}
				</div>
			{/if}
		{/each}
	</div>
</div>

<style>
	.vocab-page {
		height: 100vh;
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	.vocab-header {
		display: flex;
		align-items: center;
		gap: var(--spacing-lg);
		padding: var(--spacing-md) var(--spacing-lg);
		background-color: var(--color-surface);
		border-bottom: 1px solid var(--color-bg);
		flex-shrink: 0;
	}

	.vocab-title-group {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-xs);
	}

	.vocab-title {
		font-size: 1.5rem;
		color: var(--color-primary);
	}

	.vocab-author {
		font-size: 0.875rem;
		color: var(--color-text-muted);
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
	}

	.vocab-content {
		flex: 1;
		overflow-y: auto;
		padding: var(--spacing-md) var(--spacing-lg);
		max-width: 700px;
		margin: 0 auto;
		width: 100%;
	}

	.category-section {
		margin-bottom: var(--spacing-md);
	}

	.category-header {
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
		width: 100%;
		padding: var(--spacing-sm) var(--spacing-md);
		background-color: var(--color-surface);
		border-radius: var(--radius-md);
		color: var(--color-text);
		font-size: 1rem;
		font-weight: 600;
		text-align: left;
		transition: background-color var(--transition-fast);
	}

	.category-header:hover {
		background-color: var(--color-primary-dark);
	}

	.category-toggle {
		font-size: 0.75rem;
		width: 1rem;
		flex-shrink: 0;
	}

	.category-label {
		flex: 1;
	}

	.category-count {
		font-size: 0.75rem;
		color: var(--color-text-muted);
		background-color: var(--color-bg);
		padding: 2px 8px;
		border-radius: var(--radius-full);
	}

	.word-list {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
		gap: var(--spacing-xs);
		margin-top: var(--spacing-xs);
		padding-left: var(--spacing-lg);
	}

	.word-entry {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--spacing-sm);
		padding: var(--spacing-xs) var(--spacing-sm);
		background-color: transparent;
		border-radius: var(--radius-sm);
		color: var(--color-text);
		font-size: 0.875rem;
		text-align: left;
		transition: background-color var(--transition-fast);
		width: 100%;
	}

	.word-entry:hover {
		background-color: var(--color-surface);
		color: var(--color-primary);
	}

	.word-lemma {
		font-family: var(--font-serif);
	}

	.word-count {
		font-size: 0.75rem;
		color: var(--color-text-muted);
		flex-shrink: 0;
	}

	@media (max-width: 768px) {
		.vocab-header {
			padding: var(--spacing-md);
		}

		.vocab-title {
			font-size: 1.25rem;
		}

		.vocab-content {
			padding: var(--spacing-sm);
		}

		.word-list {
			grid-template-columns: 1fr 1fr;
			padding-left: var(--spacing-md);
		}
	}
</style>