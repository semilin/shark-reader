<script lang="ts">
	import type { Token } from '$lib/types';

	interface Props {
		token: Token;
		selected?: boolean;
		isCore?: boolean;
		onclick?: () => void;
	}

	let { token, selected = false, isCore = false, onclick }: Props = $props();
</script>

{#if token.t === 'w'}
	<button
		class="word {selected ? 'word-selected' : ''}"
		onclick={onclick}
	>
		{token.w}{#if isCore}<span class="core-star"> ★</span>{/if}
	</button>
{:else if token.t === 'p'}
	<span class="punctuation">{token.w}</span>
{:else if token.t === 's'}
	<span class="speaker">{token.w}</span>
{:else if token.t === 'm'}
	<span class="marker">{token.w}</span>
{/if}

<style>
	.word {
		background: none;
		border: 2px solid transparent;
		color: var(--color-text);
		font-family: var(--font-serif);
		font-size: 1.125rem;
		padding: 2px 0px;
		border-radius: var(--radius-sm);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.word:hover {
		background-color: var(--color-surface);
	}

	.word-selected {
		background-color: var(--color-bg);
		border-color: var(--color-primary);
	}

	.core-star {
		color: var(--color-primary);
		font-size: 0.875rem;
	}

	.punctuation {
		color: var(--color-text);
		font-size: 1.125rem;
	}

	.speaker {
		display: block;
		font-size: 1.25rem;
		font-weight: 600;
		color: var(--color-text);
		margin-top: var(--spacing-md);
		margin-bottom: var(--spacing-sm);
	}

	.marker {
		color: var(--color-text-muted);
		font-size: 0.875rem;
	}
</style>
