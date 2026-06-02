<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { onMount, onDestroy, tick } from 'svelte';
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
	let scrollRestored = $state(false);
	let error: string | null = $state(null);

	let anchorIndex: number | null = $state(null);
	let focusIndex: number | null = $state(null);
	let rangeIndices: Set<number> = $state(new Set());

	let isMobile = $state(false);
	let textContainerRef: HTMLDivElement | null = $state(null);

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
		scrollRestored = false;
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

	function handleWordClick(index: number, lemma: string, shiftKey: boolean) {
		if (shiftKey && anchorIndex !== null) {
			focusIndex = index;
			selectedLemma = null;
			computeRangeIndices();
		} else {
			anchorIndex = index;
			focusIndex = null;
			rangeIndices = new Set();
			selectedLemma = lemma;
		}
	}

	function computeRangeIndices() {
		if (anchorIndex === null || focusIndex === null) {
			rangeIndices = new Set();
			return;
		}

		const start = Math.min(anchorIndex, focusIndex);
		const end = Math.max(anchorIndex, focusIndex);
		const indices = new Set<number>();
		for (let i = start; i <= end; i++) {
			indices.add(i);
		}
		rangeIndices = indices;
	}

	function clearSelection() {
		anchorIndex = null;
		focusIndex = null;
		rangeIndices = new Set();
		selectedLemma = null;
	}

	function getSelectedText(): string | null {
		if (rangeIndices.size > 0) {
			const sortedIndices = [...rangeIndices].sort((a, b) => a - b);
			const startIdx = sortedIndices[0];
			const endIdx = sortedIndices[sortedIndices.length - 1];

			let wordCount = 0;
			const textParts: string[] = [];

			for (const token of tokens) {
				if (token.t === 'w') {
					if (wordCount >= startIdx && wordCount <= endIdx) {
						textParts.push(token.w);
					}
					wordCount++;
				} else if (token.t === 'p' && wordCount > startIdx && wordCount <= endIdx) {
					textParts.push(token.w);
				} else if (token.t === 'n' && wordCount > startIdx && wordCount <= endIdx) {
					textParts.push(' ');
				}
			}

			return textParts.join(' ');
		}

		if (anchorIndex !== null) {
			let wordCount = 0;
			for (const token of tokens) {
				if (token.t === 'w') {
					if (wordCount === anchorIndex) {
						return token.w;
					}
					wordCount++;
				}
			}
		}

		return null;
	}

	function getGloss(lemma: string): Gloss | null {
		return dictionary.get(lemma) ?? null;
	}

	function getFrequency(lemma: string): number | null {
		return frequencies.get(lemma) ?? null;
	}

	function isCore(lemma: string): boolean {
		return coreSet.has(lemma.toLowerCase());
	}

	function handleScroll() {
		if (!scrollRestored) return;
		if (textContainerRef) {
			appState.setReaderScrollPosition(textContainerRef.scrollTop);
			const currentPath = $page.url.searchParams.get('text');
			if (currentPath) {
				appState.setReaderScrollPath(currentPath);
			}
		}
	}


	function viewInGlossary(lemma: string) {
		if (!textData) return;
		const lang = textData.metadata.language;
		const currentPath = $page.url.pathname + $page.url.search;
		appState.setReaderReturnPath(currentPath);
		goto(`${base}/glossary/${lang}?word=${encodeURIComponent(lemma)}`);
	}

	function goBack() {
		goto(base || '/');
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			clearSelection();
		}
	}

	function handleCopy(e: ClipboardEvent) {
		const text = getSelectedText();
		if (text) {
			e.preventDefault();
			e.clipboardData?.setData('text/plain', text);
		}
	}

	function handleContainerClick(e: MouseEvent) {
		const target = e.target as HTMLElement;
		if (!target.closest('button.word')) {
			clearSelection();
		}
	}

	$effect(() => {
		if (typeof window !== 'undefined') {
			document.addEventListener('keydown', handleKeydown);
			document.addEventListener('copy', handleCopy);
			return () => {
				document.removeEventListener('keydown', handleKeydown);
				document.removeEventListener('copy', handleCopy);
			};
		}
	});

	$effect(() => {
		const currentPath = $page.url.searchParams.get('text');
		if (!loading && textData && textContainerRef && !scrollRestored) {
			const savedPos = $appState.readerScrollPosition;
			const savedPath = $appState.readerScrollPath;

			if (savedPos > 0 && savedPath === currentPath) {
				// Use a small timeout to ensure the DOM has settled and layout is complete
				setTimeout(() => {
					if (textContainerRef) {
						textContainerRef.scrollTop = savedPos;
						// Mark as restored after a short delay to ignore initial scroll events
						setTimeout(() => {
							scrollRestored = true;
						}, 50);
					}
				}, 50);
			} else {
				scrollRestored = true;
			}
		}
	});
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
			<div class="text-container" bind:this={textContainerRef} onclick={handleContainerClick} onscroll={handleScroll}>
				<TextDisplay
					{tokens}
					workType={textData.metadata.work_type}
					{selectedLemma}
					{rangeIndices}
					onWordClick={handleWordClick}
				/>
			</div>

			{#if isMobile}
				<div class="mobile-gloss-sheet" class:open={selectedLemma && rangeIndices.size === 0}>
					<button type="button" class="sheet-handle" aria-label="Close gloss panel" onclick={clearSelection}>
						<span class="handle-bar"></span>
					</button>
					<GlossPanel
						lemma={selectedLemma}
						gloss={selectedLemma ? getGloss(selectedLemma) : null}
						isCore={selectedLemma ? isCore(selectedLemma) : false}
						frequency={selectedLemma ? getFrequency(selectedLemma) : null}
						onviewGlossary={viewInGlossary}
					/>
				</div>
			{:else}
				<aside class="desktop-gloss-panel">
					{#if selectedLemma && rangeIndices.size === 0}
						<GlossPanel
							lemma={selectedLemma}
							gloss={selectedLemma ? getGloss(selectedLemma) : null}
							isCore={selectedLemma ? isCore(selectedLemma) : false}
							frequency={selectedLemma ? getFrequency(selectedLemma) : null}
							onviewGlossary={viewInGlossary}
						/>
					{:else}
						<p class="placeholder">{t('click_word', $appState.interfaceLang)}</p>
					{/if}
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
		scroll-behavior: auto;

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

	.placeholder {
		color: var(--color-text-muted);
		padding: var(--spacing-lg);
		text-align: center;
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
