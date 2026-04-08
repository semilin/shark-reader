<script lang="ts">
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { Button, SearchInput, Card, Badge, LanguageToggle } from '$lib/components/common';
	import TextCard from '$lib/components/library/TextCard.svelte';
	import { getAvailableTexts } from '$lib/data/texts';
	import { appState } from '$lib/stores/app-state';
	import { t, languageLabels } from '$lib/translations';
	import type { TextMetadata, Language } from '$lib/types';

	let searchQuery = $state('');
	let availableTexts = $state<TextMetadata[]>([]);
	let isLoading = $state(true);
	let error = $state<string | null>(null);

	$effect(() => {
		getAvailableTexts()
			.then((texts) => {
				availableTexts = texts;
				isLoading = false;
			})
			.catch((err) => {
				error = err.message;
				isLoading = false;
			});
	});

	function interfaceLangToLanguage(): Language | null {
		if ($appState.interfaceLang === 'latin') return 'latin';
		if ($appState.interfaceLang === 'greek') return 'greek';
		return null;
	}

	let filteredTexts = $derived(() => {
		const query = searchQuery.toLowerCase();
		const targetLang = interfaceLangToLanguage();
		
		return availableTexts.filter((text) => {
			const matchesSearch = 
				text.title.toLowerCase().includes(query) ||
				text.author.toLowerCase().includes(query);
			const matchesLang = targetLang === null || text.language === targetLang;
			return matchesSearch && matchesLang;
		});
	});

	function openText(text: TextMetadata) {
		const encodedPath = encodeURIComponent(text.path);
		goto(`${base}/reader?text=${encodedPath}`);
	}

	function openGlossary(lang: Language) {
		goto(`${base}/glossary/${lang}`);
	}
</script>

<div class="library">
	<div class="library-header">
		<h1 class="library-title">{t('library_title', $appState.interfaceLang)}</h1>
		<div class="library-controls">
			<SearchInput 
				placeholder={t('search_texts', $appState.interfaceLang)}
				bind:value={searchQuery}
			/>
			<LanguageToggle />
		</div>
	</div>

	<div class="text-list">
		{#if isLoading}
			<div class="loading-message">Loading texts...</div>
		{:else if error}
			<div class="error-message">Error: {error}</div>
		{:else}
			{#each filteredTexts() as text (text.path)}
				<TextCard {text} onclick={() => openText(text)} />
			{/each}
		{/if}
	</div>

	<div class="glossary-buttons">
		{#if $appState.interfaceLang === 'english'}
			<Button onclick={() => openGlossary('latin')}>Latin Glossary</Button>
			<Button onclick={() => openGlossary('greek')}>Greek Glossary</Button>
		{:else if $appState.interfaceLang === 'latin'}
			<Button onclick={() => openGlossary('latin')}>{t('glossary', 'latin')}</Button>
		{:else}
			<Button onclick={() => openGlossary('greek')}>{t('glossary', 'greek')}</Button>
		{/if}
	</div>
</div>

<style>
	.library {
		height: 100%;
		display: flex;
		flex-direction: column;
		padding: var(--spacing-xl);
		max-width: 600px;
		margin: 0 auto;
		width: 100%;
		overflow: hidden;
	}

	.library-header {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-lg);
		margin-bottom: var(--spacing-xl);
		flex-shrink: 0;
	}

	.library-title {
		font-size: 2.25rem;
		color: var(--color-primary);
		text-align: center;
	}

	.library-controls {
		display: flex;
		gap: var(--spacing-md);
	}

	.library-controls :global(.search-input) {
		flex: 1;
	}

	.text-list {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: var(--spacing-md);
		overflow-y: auto;
		min-height: 0;
	}

	.glossary-buttons {
		display: flex;
		gap: var(--spacing-lg);
		justify-content: center;
		margin-top: var(--spacing-xl);
		padding-top: var(--spacing-lg);
		border-top: 1px solid var(--color-surface);
		flex-shrink: 0;
	}

	.loading-message,
	.error-message {
		text-align: center;
		padding: var(--spacing-xl);
		color: var(--color-text-secondary);
	}

	.error-message {
		color: var(--color-error, #dc3545);
	}

	@media (max-width: 768px) {
		.library {
			padding: var(--spacing-md);
		}

		.library-title {
			font-size: 1.75rem;
		}

		.library-controls {
			flex-direction: column;
		}

		.glossary-buttons {
			flex-direction: column;
			gap: var(--spacing-sm);
		}
	}
</style>
