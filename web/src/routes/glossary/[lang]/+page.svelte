<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { Button, SearchInput, Card } from '$lib/components/common';
	import { getDictionary } from '$lib/data/dictionaries';
	import { appState } from '$lib/stores/app-state';
	import { t } from '$lib/translations';
	import type { Gloss, Dictionary, Language, GlobalStats, WordStats } from '$lib/types';
	import { getStats } from '$lib/data/stats';

	let { params } = $props();
	let lang = $derived(params.lang as Language);

	let dictionary: Dictionary = $state(new Map());
	let stats: GlobalStats = $state({});
	let searchQuery = $state('');
	let selectedWord: string | null = $state(null);
	let loading = $state(true);

	$effect(() => {
		const wordParam = $page.url.searchParams.get('word');
		if (wordParam && words.includes(wordParam)) {
			selectedWord = wordParam;
		}
	});

	let words = $derived([...dictionary.keys()].sort());

	let filteredWords = $derived(() => {
		const query = searchQuery.toLowerCase();
		return words.filter((word) => word.toLowerCase().includes(query));
	});

	onMount(async () => {
		dictionary = await getDictionary(lang);
		stats = await getStats(lang);
		loading = false;
	});

	function goBack() {
		if ($appState.readerReturnPath) {
			const path = $appState.readerReturnPath;
			appState.setReaderReturnPath(null);
			goto(path);
		} else {
			goto(base || '/');
		}
	}

	function selectWord(word: string) {
		selectedWord = word;
	}

	function getGloss(word: string): Gloss | null {
		return dictionary.get(word) ?? null;
	}

	function getWordStats(word: string): WordStats | null {
		return stats[word] ?? null;
	}

	async function copyToClipboard(text: string) {
		try {
			await navigator.clipboard.writeText(text);
		} catch (err) {
			console.error('Failed to copy:', err);
		}
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
							<div class="entry-definition-row">
								<p class="entry-definition">{gloss.definition}</p>
								<button
									type="button"
									class="copy-btn"
									title={t('copy', $appState.interfaceLang)}
									onclick={() => copyToClipboard(gloss.definition)}
								>
									<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
										<rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
										<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
									</svg>
								</button>
							</div>
							{#if gloss.examples.length > 0}
								<div class="entry-examples">
									<h3 class="examples-title">{t('examples', $appState.interfaceLang)}</h3>
									<ul class="examples-list">
										{#each gloss.examples as example}
											<li>
												<span class="example-text">{example}</span>
												<button
													type="button"
													class="copy-btn"
													title={t('copy', $appState.interfaceLang)}
													onclick={() => copyToClipboard(example)}
												>
													<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
														<rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
														<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
													</svg>
												</button>
											</li>
										{/each}
									</ul>
								</div>
							{/if}
						</div>

						{#if getWordStats(selectedWord)}
							{@const wordStats = getWordStats(selectedWord)!}
							<div class="stats-panel">
								<h3 class="stats-title">{t('word_stats', $appState.interfaceLang)}</h3>
								<div class="stats-grid">
									<div class="stat-item">
										<span class="stat-label">{t('total_appearances', $appState.interfaceLang)}</span>
										<span class="stat-value">{wordStats.total}</span>
									</div>
									<div class="stat-item">
										<span class="stat-label">{t('frequency_score', $appState.interfaceLang)}</span>
										<span class="stat-value">{wordStats.frequencyScore}</span>
									</div>
								</div>

								<div class="stats-section">
									<h4 class="stats-subtitle">{t('top_forms', $appState.interfaceLang)}</h4>
									<div class="forms-list">
										{#each wordStats.forms as [form, count]}
											<div class="form-tag">
												<span class="form-text">{form}</span>
												<span class="form-count">{count}</span>
											</div>
										{/each}
									</div>
								</div>

								<div class="stats-section">
									<h4 class="stats-subtitle">{t('appearances_by_text', $appState.interfaceLang)}</h4>
									<ul class="text-stats-list">
										{#each wordStats.texts as text}
											<li>
												<span class="text-title">{text.title}</span>
												<span class="text-count">{text.count}</span>
											</li>
										{/each}
									</ul>
								</div>
							</div>
						{/if}
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

	.entry-definition-row {
		display: flex;
		align-items: flex-start;
		gap: var(--spacing-sm);
		margin-bottom: var(--spacing-lg);
	}

	.entry-definition {
		font-size: 1.25rem;
		line-height: 1.6;
		flex: 1;
		margin: 0;
	}

	.copy-btn {
		background: none;
		border: none;
		padding: var(--spacing-xs);
		cursor: pointer;
		color: var(--color-text-muted);
		border-radius: var(--radius-sm);
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
		transition: all var(--transition-fast);
	}

	.copy-btn:hover {
		color: var(--color-primary);
		background-color: var(--color-surface);
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
		display: flex;
		align-items: flex-start;
		gap: var(--spacing-xs);
		position: relative;
		padding-left: var(--spacing-md);
	}

	.examples-list li::before {
		content: '•';
		position: absolute;
		left: 0;
		color: var(--color-primary);
	}

	.example-text {
		flex: 1;
	}

	.stats-panel {
		margin-top: var(--spacing-xl);
		padding-top: var(--spacing-lg);
		border-top: 1px solid var(--color-surface);
	}

	.stats-title {
		font-size: 1.25rem;
		color: var(--color-text);
		margin-bottom: var(--spacing-md);
	}

	.stats-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
		gap: var(--spacing-md);
		margin-bottom: var(--spacing-lg);
	}

	.stat-item {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-xs);
		padding: var(--spacing-sm);
		background-color: var(--color-surface);
		border-radius: var(--radius-md);
	}

	.stat-label {
		font-size: 0.75rem;
		color: var(--color-text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.stat-value {
		font-size: 1.5rem;
		font-weight: 600;
		color: var(--color-primary);
	}

	.stats-section {
		margin-bottom: var(--spacing-lg);
	}

	.stats-subtitle {
		font-size: 0.875rem;
		color: var(--color-text-muted);
		margin-bottom: var(--spacing-sm);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.forms-list {
		display: flex;
		flex-wrap: wrap;
		gap: var(--spacing-xs);
	}

	.form-tag {
		display: flex;
		align-items: center;
		gap: var(--spacing-xs);
		padding: var(--spacing-xs) var(--spacing-sm);
		background-color: var(--color-surface);
		border-radius: var(--radius-full);
		font-size: 0.875rem;
	}

	.form-count {
		color: var(--color-text-muted);
		font-size: 0.75rem;
	}

	.text-stats-list {
		list-style: none;
		display: flex;
		flex-direction: column;
		gap: var(--spacing-xs);
	}

	.text-stats-list li {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: var(--spacing-xs) var(--spacing-sm);
		background-color: var(--color-surface);
		border-radius: var(--radius-sm);
		font-size: 0.875rem;
	}

	.text-count {
		font-weight: 600;
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
