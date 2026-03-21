<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { Button } from '$lib/components/common';
	import TextDisplay from '$lib/components/reader/TextDisplay.svelte';
	import GlossPanel from '$lib/components/reader/GlossPanel.svelte';
	import { loadText, computeLemmaFrequencies } from '$lib/data/texts';
	import { getDictionary } from '$lib/data/dictionaries';
	import { getCoreList } from '$lib/data/core-lists';
	import { appState } from '$lib/stores/app-state';
	import { t } from '$lib/translations';
	import type { AnnotatedText, Token, Gloss, Dictionary } from '$lib/types';

	let textData: AnnotatedText | null = $state(null);
	let tokens: Token[] = $state([]);
	let frequencies: Map<string, number> = $state(new Map());
	let dictionary: Dictionary = $state(new Map());
	let coreSet: Set<string> = $state(new Set());
	let selectedLemma: string | null = $state(null);
	let loading = $state(true);
	let error: string | null = $state(null);

	let isMobile = $state(false);

	onMount(() => {
		isMobile = window.innerWidth < 768;
		window.addEventListener('resize', () => {
			isMobile = window.innerWidth < 768;
		});
	});

	$effect(() => {
		const textPath = $page.url.searchParams.get('text');
		if (textPath) {
			loadTextContent(decodeURIComponent(textPath));
		}
	});

	async function loadTextContent(path: string) {
		try {
			loading = true;
			error = null;
			
			const data = await loadText(path);
			textData = data;
			tokens = data.tokens;
			frequencies = computeLemmaFrequencies(data.tokens);
			
			dictionary = await getDictionary(data.metadata.language);
			coreSet = await getCoreList(data.metadata.language);
			
			loading = false;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load text';
			loading = false;
		}
	}

	function handleWordSelect(lemma: string) {
		selectedLemma = lemma;
	}

	function getGloss(lemma: string): Gloss | null {
		return dictionary.get(lemma) ?? null;
	}

	function isCore(lemma: string): boolean {
		return coreSet.has(lemma.toLowerCase());
	}

	function getFrequency(lemma: string): number | null {
		return frequencies.get(lemma) ?? null;
	}

	function goBack() {
		goto(base || '/');
	}
</script>

<svelte:head>
	{#if textData}
		<title>{textData.metadata.title} - SharkReader</title>
	{/if}
</svelte:head>

<div class="reader-page">
	{#if loading}
		<div class="loading">
			<p>Loading...</p>
		</div>
	{:else if error}
		<div class="error">
			<p class="error-message">{error}</p>
			<Button onclick={goBack}>Go Back</Button>
		</div>
	{:else if textData}
		<header class="reader-header">
			<Button onclick={goBack}>{t('back_to_library', $appState.interfaceLang)}</Button>
			<div class="header-info">
				<h1 class="header-title">{textData.metadata.title}</h1>
				<p class="header-author">{textData.metadata.author}</p>
			</div>
		</header>

		<div class="reader-content">
			<div class="text-container">
				<TextDisplay
					{tokens}
					workType={textData.metadata.work_type}
					{selectedLemma}
					coreLookup={isCore}
					onWordSelect={handleWordSelect}
				/>
			</div>

			{#if isMobile}
				<div class="mobile-gloss-sheet" class:open={selectedLemma}>
					<button type="button" class="sheet-handle" aria-label="Close gloss panel" onclick={() => selectedLemma = null}>
						<span class="handle-bar"></span>
					</button>
					<GlossPanel
						lemma={selectedLemma}
						gloss={selectedLemma ? getGloss(selectedLemma) : null}
						isCore={selectedLemma ? isCore(selectedLemma) : false}
						frequency={selectedLemma ? getFrequency(selectedLemma) : null}
					/>
				</div>
			{:else}
				<aside class="desktop-gloss-panel">
					<GlossPanel
						lemma={selectedLemma}
						gloss={selectedLemma ? getGloss(selectedLemma) : null}
						isCore={selectedLemma ? isCore(selectedLemma) : false}
						frequency={selectedLemma ? getFrequency(selectedLemma) : null}
					/>
				</aside>
			{/if}
		</div>
	{/if}
</div>

<style>
	.reader-page {
		height: 100vh;
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	.loading, .error {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: var(--spacing-lg);
	}

	.error-message {
		color: var(--color-error);
		font-size: 1.125rem;
	}

	.reader-header {
		display: flex;
		align-items: center;
		gap: var(--spacing-lg);
		padding: var(--spacing-md) var(--spacing-lg);
		background-color: var(--color-surface);
		border-bottom: 1px solid var(--color-bg);
		flex-shrink: 0;
	}

	.header-info {
		flex: 1;
		min-width: 0;
	}

	.header-title {
		font-size: 1.25rem;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.header-author {
		font-size: 0.875rem;
		color: var(--color-text-muted);
	}

	.reader-content {
		flex: 1;
		display: flex;
		overflow: hidden;
		min-height: 0;
	}

	.text-container {
		flex: 1;
		overflow-y: auto;
	}

	.desktop-gloss-panel {
		width: 350px;
		flex-shrink: 0;
		border-left: 1px solid var(--color-surface);
		background-color: var(--color-surface);
		overflow-y: auto;
	}

	.mobile-gloss-sheet {
		position: fixed;
		bottom: 0;
		left: 0;
		right: 0;
		background-color: var(--color-surface);
		border-radius: var(--radius-lg) var(--radius-lg) 0 0;
		transform: translateY(calc(100% - 24px));
		transition: transform var(--transition-normal);
		max-height: 50vh;
		overflow-y: auto;
		z-index: 100;
		box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.3);
	}

	.mobile-gloss-sheet.open {
		transform: translateY(0);
	}

	.sheet-handle {
		height: 24px;
		width: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		background: none;
		border: none;
		padding: 0;
	}

	.handle-bar {
		width: 40px;
		height: 4px;
		background-color: var(--color-text-muted);
		border-radius: 2px;
	}

	@media (max-width: 768px) {
		.reader-header {
			flex-wrap: wrap;
		}
		
		.header-title {
			font-size: 1rem;
		}
	}
</style>
