<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';

	type BadgeVariant = 'default' | 'primary' | 'muted';

	interface Props extends HTMLAttributes<HTMLSpanElement> {
		variant?: BadgeVariant;
		children?: Snippet;
	}

	let { variant = 'default', children, class: className, ...restProps }: Props = $props();
</script>

<span
	class="badge badge-{variant} {className ?? ''}"
	{...restProps}
>
	{#if children}
		{@render children()}
	{/if}
</span>

<style>
	.badge {
		display: inline-flex;
		align-items: center;
		padding: var(--spacing-xs) var(--spacing-sm);
		border-radius: var(--radius-sm);
		font-size: 0.75rem;
		font-weight: 500;
		white-space: nowrap;
	}

	.badge-default {
		background-color: var(--color-surface);
		color: var(--color-text);
	}

	.badge-primary {
		background-color: var(--color-primary);
		color: var(--color-bg);
	}

	.badge-muted {
		background-color: transparent;
		color: var(--color-text-muted);
	}
</style>
