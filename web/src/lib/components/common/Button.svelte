<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLButtonAttributes } from 'svelte/elements';

	type ButtonVariant = 'primary' | 'bordered' | 'text';

	interface Props extends HTMLButtonAttributes {
		variant?: ButtonVariant;
		children?: Snippet;
	}

	let { variant = 'primary', children, class: className, ...restProps }: Props = $props();
</script>

<button
	class="btn btn-{variant} {className ?? ''}"
	{...restProps}
>
	{#if children}
		{@render children()}
	{/if}
</button>

<style>
	.btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		padding: var(--spacing-sm) var(--spacing-md);
		border-radius: var(--radius-md);
		font-weight: 500;
		transition: all var(--transition-fast);
		white-space: nowrap;
	}

	.btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.btn-primary {
		background-color: var(--color-primary);
		color: var(--color-bg);
	}

	.btn-primary:hover:not(:disabled) {
		background-color: var(--color-primary-dark);
	}

	.btn-primary:active:not(:disabled) {
		transform: scale(0.98);
	}

	.btn-bordered {
		background-color: var(--color-surface);
		color: var(--color-text);
		border: 2px solid var(--color-primary);
	}

	.btn-bordered:hover:not(:disabled) {
		background-color: var(--color-primary);
		color: var(--color-bg);
	}

	.btn-text {
		background-color: transparent;
		color: var(--color-text);
	}

	.btn-text:hover:not(:disabled) {
		color: var(--color-primary);
	}
</style>
