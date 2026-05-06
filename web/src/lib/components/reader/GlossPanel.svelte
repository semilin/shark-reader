<script lang="ts">
	import { fade } from 'svelte/transition';
	import Badge from '../common/Badge.svelte';
	import { t } from '$lib/translations';
	import { appState } from '$lib/stores/app-state';
	import type { Gloss } from '$lib/types';

	interface Props {
		lemma: string | null;
		gloss: Gloss | null;
		isCore: boolean;
		frequency: number | null;
		onviewGlossary?: (lemma: string) => void;
	}

	let { lemma, gloss, isCore, frequency, onviewGlossary }: Props = $props();

	async function copyToClipboard(text: string) {
		try {
			await navigator.clipboard.writeText(text);
		} catch (err) {
			console.error('Failed to copy:', err);
		}
	}
</script>

<div class="gloss-panel" transition:fade={{ duration: 200 }}>
	{#if lemma}
		<div class="gloss-header">
			<div class="lemma-group">
				<h2 class="lemma">{lemma}{#if isCore} ★{/if}</h2>
				{#if gloss?.synonyms && gloss.synonyms.length > 0}
					<span class="synonyms">{gloss.synonyms.join(', ')}</span>
				{/if}
			</div>
			<div class="header-actions">
				{#if frequency !== null}
					<Badge variant="muted">{frequency.toFixed(1)}%</Badge>
				{/if}
				{#if onviewGlossary}
					<button
						type="button"
						class="view-glossary-btn"
						title={t('view_in_glossary', $appState.interfaceLang)}
						onclick={() => onviewGlossary!(lemma!)}
					>
						<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path>
							<path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path>
						</svg>
					</button>
				{/if}
			</div>
		</div>

		{#if gloss}
			<div class="definition-row">
				<p class="definition">{gloss.definition}</p>
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
				<div class="examples">
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
		{:else if isCore}
			<p class="core-note">{t('core_vocabulary', $appState.interfaceLang)}</p>
		{:else}
			<p class="no-gloss">{t('no_gloss', $appState.interfaceLang)}</p>
		{/if}
	{:else}
		<p class="placeholder">{t('click_word', $appState.interfaceLang)}</p>
	{/if}
</div>

<style>
	.gloss-panel {
		padding: var(--spacing-lg);
	}

	.gloss-header {
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
		margin-bottom: var(--spacing-md);
	}

	.lemma-group {
		display: flex;
		align-items: baseline;
		gap: var(--spacing-sm);
		flex-wrap: wrap;
		flex: 1;
	}

	.header-actions {
		display: flex;
		align-items: center;
		gap: var(--spacing-xs);
	}

	.lemma {
		font-size: 1.75rem;
		color: var(--color-primary);
		font-weight: 600;
	}

	.synonyms {
		color: var(--color-text-muted);
		font-size: 0.95rem;
	}

	.definition-row {
		display: flex;
		align-items: flex-start;
		gap: var(--spacing-sm);
		margin-bottom: var(--spacing-lg);
	}

	.definition {
		font-size: 1.125rem;
		line-height: 1.6;
		flex: 1;
		margin: 0;
	}

	.copy-btn, .view-glossary-btn {
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

	.copy-btn:hover, .view-glossary-btn:hover {
		color: var(--color-primary);
		background-color: var(--color-bg);
	}

	.examples {
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

	.core-note {
		color: var(--color-text-muted);
		font-style: italic;
	}

	.no-gloss {
		color: var(--color-text-muted);
	}

	.placeholder {
		color: var(--color-text-muted);
		text-align: center;
		padding: var(--spacing-xl);
	}
</style>
