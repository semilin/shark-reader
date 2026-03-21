<script lang="ts">
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { Button, SearchInput, Card } from '$lib/components/common';
	import { getDictionary } from '$lib/data/dictionaries';
	import { appState } from '$lib/stores/app-state';
	import { t } from '$lib/translations';
	import type { Gloss, Dictionary, Language } from '$lib/types';

	let { params } = $props();
	let lang = $derived(params.lang as Language);

	let dictionary: Dictionary = $state(new Map());
	let searchQuery = $state('');
	let selectedWord: string | null = $state(null);
	let loading = $state(true);

	let words = $derived([...dictionary.keys()].sort());

	let filteredWords = $derived(() => {
		const query = searchQuery.toLowerCase();
		return words.filter((word) => word.toLowerCase().includes(query));
	});

	onMount(async () => {
		dictionary = await getDictionary(lang);
		loading = false;
	});

	function goBack() {
		goto(base || '/');
	}

	function selectWord(word: string) {
		selectedWord = word;
	}

	function getGloss(word: string): Gloss | null {
		return dictionary.get(word) ?? null;
	}
</script>

<svelte:head>
	<title>{t('glossary', $appState.interfaceLang)} - SharkReader</title>
</svelte:head>

<div class="glossary-page">
	<header class="glossary-header">
		<Button onclick={goBack}>{t('back_to_library', $appState.interfaceLang)}</Button>
		<h1 class="glossary-title">{t('glossary', $appState.interfaceLang)}</h1>
	</header>

	{#if loading}
		<div class="loading">
			<p>Loading...</p>
		</div>
	{:else}
		<div class="glossary-content">
			<div class="word-list-panel">
				<SearchInput
					placeholder={t('search_words', $appState.interfaceLang)}
					bind:value={searchQuery}
				/>
				<div class="word-list">
					{#each filteredWords() as word (word)}
						<Card
							clickable
							selected={selectedWord === word}
							onclick={() => selectWord(word)}
						>
							<span class="word-item">{word}</span>
						</Card>
					{/each}
				</div>
			</div>

			<div class="gloss-entry-panel">
				{#if selectedWord}
					{@const gloss = getGloss(selectedWord)}
					{#if gloss}
						<div class="gloss-entry">
							<h2 class="entry-word">{selectedWord}</h2>
							<p class="entry-definition">{gloss.definition}</p>
							{#if gloss.examples.length > 0}
								<div class="entry-examples">
									<h3 class="examples-title">{t('examples', $appState.interfaceLang)}</h3>
									<ul class="examples-list">
										{#each gloss.examples as example}
											<li>{example}</li>
										{/each}
									</ul>
								</div>
							{/if}
						</div>
					{/if}
				{:else}
					<p class="placeholder">{t('select_word_detail', $appState.interfaceLang)}</p>
				{/if}
			</div>
		</div>
	{/if}
</div>

<style>
	.glossary-page {
		height: 100vh;
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	.loading {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.glossary-header {
		display: flex;
		align-items: center;
		gap: var(--spacing-lg);
		padding: var(--spacing-md) var(--spacing-lg);
		background-color: var(--color-surface);
		border-bottom: 1px solid var(--color-bg);
		flex-shrink: 0;
	}

	.glossary-title {
		font-size: 1.5rem;
		color: var(--color-primary);
	}

	.glossary-content {
		flex: 1;
		display: flex;
		overflow: hidden;
		min-height: 0;
	}

	.word-list-panel {
		width: 280px;
		flex-shrink: 0;
		display: flex;
		flex-direction: column;
		padding: var(--spacing-md);
		border-right: 1px solid var(--color-surface);
		background-color: var(--color-surface);
		gap: var(--spacing-md);
		overflow-y: auto;
	}

	.word-list {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: var(--spacing-xs);
	}

	.word-item {
		font-size: 0.875rem;
		color: var(--color-text);
	}

	.gloss-entry-panel {
		flex: 1;
		padding: var(--spacing-lg);
		overflow-y: auto;
	}

	.gloss-entry {
		max-width: 600px;
	}

	.entry-word {
		font-size: 2rem;
		color: var(--color-primary);
		margin-bottom: var(--spacing-md);
	}

	.entry-definition {
		font-size: 1.25rem;
		line-height: 1.6;
		margin-bottom: var(--spacing-lg);
	}

	.entry-examples {
		margin-top: var(--spacing-lg);
	}

	.examples-title {
		font-size: 1rem;
		color: var(--color-text-muted);
		margin-bottom: var(--spacing-sm);
	}

	.examples-list {
		list-style: none;
		display: flex;
		flex-direction: column;
		gap: var(--spacing-sm);
	}

	.examples-list li {
		position: relative;
		padding-left: var(--spacing-md);
	}

	.examples-list li::before {
		content: '•';
		position: absolute;
		left: 0;
		color: var(--color-primary);
	}

	.placeholder {
		color: var(--color-text-muted);
		font-size: 1.125rem;
	}

	@media (max-width: 768px) {
		.glossary-content {
			flex-direction: column;
		}

		.word-list-panel {
			width: 100%;
			max-height: 40vh;
			border-right: none;
			border-bottom: 1px solid var(--color-bg);
		}

		.glossary-title {
			font-size: 1.25rem;
		}
	}
</style>
