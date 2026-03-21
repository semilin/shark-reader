<script lang="ts">
	import Word from './Word.svelte';
	import type { Token, WorkType } from '$lib/types';

	interface Props {
		tokens: Token[];
		workType: WorkType;
		selectedLemma: string | null;
		coreLookup: (lemma: string) => boolean;
		onWordSelect: (lemma: string) => void;
	}

	let { tokens, workType, selectedLemma, coreLookup, onWordSelect }: Props = $props();

	interface Line {
		tokens: Token[];
		lineNumber: number;
	}

	function groupIntoLines(tokens: Token[], isPoem: boolean): Line[] {
		const lines: Line[] = [];
		let currentTokens: Token[] = [];
		let lineNum = 0;

		for (const token of tokens) {
			if (token.t === 'n') {
				lineNum++;
				lines.push({ tokens: currentTokens, lineNumber: lineNum });
				currentTokens = [];
			} else if (token.t === 's') {
				if (currentTokens.length > 0) {
					lines.push({ tokens: currentTokens, lineNumber: lineNum });
					currentTokens = [];
				}
				lines.push({ tokens: [token], lineNumber: lineNum });
			} else {
				currentTokens.push(token);
			}
		}

		if (currentTokens.length > 0) {
			lines.push({ tokens: currentTokens, lineNumber: lineNum });
		}

		return lines;
	}

	let lines = $derived(groupIntoLines(tokens, workType === 'poem'));

	function shouldShowLineNumber(lineNum: number): boolean {
		return workType === 'poem' && lineNum > 0 && lineNum % 5 === 0;
	}
</script>

<div class="text-display">
	{#each lines as line, idx (idx)}
		<div class="line">
			{#if workType === 'poem'}
				<span class="line-number">
					{#if shouldShowLineNumber(line.lineNumber)}
						{line.lineNumber}
					{/if}
				</span>
			{/if}
			<span class="line-content">
				{#each line.tokens as token, tokenIdx (tokenIdx)}
					{#if token.t === 'w' && token.l}
						<Word
							{token}
							selected={selectedLemma === token.l}
							isCore={coreLookup(token.l)}
							onclick={() => onWordSelect(token.l!)}
						/>
					{:else}
						<Word {token} />
					{/if}
				{/each}
			</span>
		</div>
	{/each}
</div>

<style>
	.text-display {
		padding: var(--spacing-lg);
		line-height: 1.8;
	}

	.line {
		display: flex;
		align-items: baseline;
		gap: var(--spacing-md);
		min-height: 2rem;
	}

	.line-number {
		flex-shrink: 0;
		width: 2.5rem;
		text-align: right;
		color: var(--color-text-muted);
		font-size: 0.75rem;
		padding-right: var(--spacing-sm);
	}

	.line-content {
		flex: 1;
		display: flex;
		flex-wrap: wrap;
		gap: 2px;
	}

	@media (max-width: 768px) {
		.line-number {
			width: 2rem;
		}
	}
</style>
