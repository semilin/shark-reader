<script lang="ts">
	import type { HTMLInputAttributes } from 'svelte/elements';

	interface Props extends HTMLInputAttributes {
		value?: string;
	}

	let { value = $bindable(''), class: className, ...restProps }: Props = $props();
</script>

<input
	type="text"
	class="search-input {className ?? ''}"
	bind:value
	{...restProps}
/>

<style>
	.search-input {
		width: 100%;
		padding: var(--spacing-sm) var(--spacing-md);
		background-color: var(--color-surface);
		color: var(--color-text);
		border: 2px solid transparent;
		border-radius: var(--radius-md);
		font-size: 1rem;
		transition: all var(--transition-fast);
	}

	.search-input::placeholder {
		color: var(--color-text-muted);
	}

	.search-input:focus {
		outline: none;
		border-color: var(--color-primary);
	}

	.search-input:hover:not(:focus) {
		border-color: var(--color-primary-dark);
	}
</style>
