<script lang="ts">
	import type { Token } from '$lib/types';

	interface Props {
		token: Token;
		index?: number;
		selected?: boolean;
		inRange?: boolean;
		onclick?: (index: number, event: MouseEvent) => void;
	}

	let { token, index = 0, selected = false, inRange = false, onclick }: Props = $props();
</script>

{#if token.t === 'w'}
	<button
		class="word {selected ? 'word-selected' : ''} {inRange ? 'word-in-range' : ''} {token.s ? 'word-has-substitute' : ''}"
		onclick={(e) => onclick?.(index, e)}
	>
		{token.w}
		{#if token.s}
			<span class="substitute-tooltip">{token.s}</span>
		{/if}
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


	.word-has-substitute {
		position: relative;
	}

	.substitute-tooltip {
		position: absolute;
		bottom: calc(100% + 4px);
		left: 50%;
		transform: translateX(-50%);
		background-color: var(--color-primary);
		color: var(--color-bg);
		font-size: 0.75rem;
		padding: 2px 8px;
		border-radius: var(--radius-sm);
		white-space: nowrap;
		pointer-events: none;
		opacity: 0;
		visibility: hidden;
		transition: opacity var(--transition-fast), visibility var(--transition-fast);
		z-index: 10;
	}

	.substitute-tooltip::after {
		content: '';
		position: absolute;
		top: 100%;
		left: 50%;
		transform: translateX(-50%);
		border-width: 4px;
		border-style: solid;
		border-color: var(--color-primary) transparent transparent transparent;
	}

	.word-has-substitute:hover .substitute-tooltip {
		opacity: 1;
		visibility: visible;
	}

	.word-selected .substitute-tooltip {
		background-color: var(--color-primary-dark);
	}

	.word-selected .substitute-tooltip::after {
		border-top-color: var(--color-primary-dark);
	}

	.word-in-range .substitute-tooltip {
		background-color: var(--color-bg);
		color: var(--color-primary);
	}

	.word-in-range .substitute-tooltip::after {
		border-top-color: var(--color-bg);
	}
	.word-selected {
		background-color: var(--color-bg);
		border-color: var(--color-primary);
	}

	.word-in-range {
		background-color: var(--color-primary);
		color: var(--color-bg);
	}

	.word-in-range.word-selected {
		border-color: var(--color-text);
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
