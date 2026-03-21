<script lang="ts">
	import Card from '../common/Card.svelte';
	import Badge from '../common/Badge.svelte';
	import { languageLabels } from '$lib/translations';
	import type { TextMetadata } from '$lib/types';

	interface Props {
		text: TextMetadata;
		onclick?: () => void;
	}

	let { text, onclick }: Props = $props();
</script>

<Card clickable onclick={onclick}>
	<div class="text-card">
		<div class="text-info">
			<h3 class="text-title">{text.title}</h3>
			<p class="text-author">{text.author}</p>
		</div>
		<Badge variant="primary">{languageLabels[text.language]}</Badge>
	</div>
</Card>

<style>
	.text-card {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--spacing-md);
	}

	.text-info {
		flex: 1;
		min-width: 0;
	}

	.text-title {
		font-size: 1.125rem;
		font-weight: 600;
		margin-bottom: var(--spacing-xs);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		color: var(--color-text);
	}

	.text-author {
		font-size: 0.875rem;
		color: var(--color-text);
		opacity: 0.7;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	@media (max-width: 480px) {
		.text-card {
			flex-direction: column;
			align-items: flex-start;
		}
	}
</style>
