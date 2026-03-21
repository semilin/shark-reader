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
	}

	let { lemma, gloss, isCore, frequency }: Props = $props();
</script>

<div class="gloss-panel" transition:fade={{ duration: 200 }}>
	{#if lemma}
		<div class="gloss-header">
			<h2 class="lemma">{lemma}{#if isCore} ★{/if}</h2>
			{#if frequency !== null}
				<Badge variant="muted">{frequency.toFixed(1)}%</Badge>
			{/if}
		</div>

		{#if gloss}
			<p class="definition">{gloss.definition}</p>

			{#if gloss.examples.length > 0}
				<div class="examples">
					<h3 class="examples-title">{t('examples', $appState.interfaceLang)}</h3>
					<ul class="examples-list">
						{#each gloss.examples as example}
							<li>{example}</li>
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

	.lemma {
		font-size: 1.75rem;
		color: var(--color-primary);
		font-weight: 600;
	}

	.definition {
		font-size: 1.125rem;
		line-height: 1.6;
		margin-bottom: var(--spacing-lg);
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
		position: relative;
		padding-left: var(--spacing-md);
	}

	.examples-list li::before {
		content: '•';
		position: absolute;
		left: 0;
		color: var(--color-primary);
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
