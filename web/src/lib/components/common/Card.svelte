<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';

	interface Props {
		clickable?: boolean;
		selected?: boolean;
		children?: Snippet;
		class?: string;
		onclick?: (e: MouseEvent) => void;
	}

	let { clickable = false, selected = false, children, class: className, onclick }: Props = $props();
</script>

{#if clickable}
	<button
		type="button"
		class="card card-clickable {selected ? 'card-selected' : ''} {className ?? ''}"
		{onclick}
	>
		{#if children}
			{@render children()}
		{/if}
	</button>
{:else}
	<div class="card {className ?? ''}">
		{#if children}
			{@render children()}
		{/if}
	</div>
{/if}

<style>
	.card {
		background-color: var(--color-surface);
		border-radius: var(--radius-md);
		padding: var(--spacing-md);
		transition: all var(--transition-fast);
	}

	.card-clickable {
		cursor: pointer;
		border: 2px solid transparent;
	}

	.card-clickable:hover {
		border-color: var(--color-primary);
	}

	.card-clickable:focus {
		outline: none;
		border-color: var(--color-primary);
	}

	.card-clickable:active {
		transform: scale(0.99);
	}

	.card-selected {
		border: 2px solid var(--color-primary);
		background-color: var(--color-bg);
	}
</style>
