<script lang="ts">
	import Card from '../common/Card.svelte';
	import Badge from '../common/Badge.svelte';
	import { languageLabels } from '$lib/translations';
	import type { TextMetadata } from '$lib/types';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';

	interface Props {
		text: TextMetadata;
		onclick?: () => void;
	}

	let { text, onclick }: Props = $props();

	function getSlug(path: string): string {
		return path.replace('/shark-reader/texts/', '').replace('.annotated.json', '');
	}

	function openVocab(e: MouseEvent) {
		e.stopPropagation();
		const slug = getSlug(text.path);
		goto(`${base}/text-vocab/${slug}`);
	}
</script>

<Card clickable onclick={onclick}>
	<div class="text-card">
		<div class="text-info">
			<h3 class="text-title">{text.title}</h3>
			<p class="text-author">{text.author}</p>
		</div>
		<div class="text-actions">
			<Badge variant="primary">{languageLabels[text.language]}</Badge>
			<button
				type="button"
				class="vocab-icon-btn"
				title="Vocabulary"
				onclick={openVocab}
			>
				<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
					<path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
					<line x1="8" y1="7" x2="16" y2="7"/>
					<line x1="8" y1="11" x2="14" y2="11"/>
				</svg>
			</button>
		</div>
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

	.text-actions {
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
		flex-shrink: 0;
	}

	.vocab-icon-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		border-radius: var(--radius-sm);
		background: transparent;
		border: 1px solid var(--color-text-muted);
		color: var(--color-text-muted);
		cursor: pointer;
		transition: all var(--transition-fast);
		flex-shrink: 0;
	}

	.vocab-icon-btn:hover {
		color: var(--color-primary);
		border-color: var(--color-primary);
		background-color: var(--color-surface);
	}

	@media (max-width: 480px) {
		.text-card {
			flex-direction: column;
			align-items: flex-start;
		}
	}
</style>