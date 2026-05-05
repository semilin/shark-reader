<script lang="ts">
	import Word from './Word.svelte';
	import type { Token, WorkType } from '$lib/types';

	interface Props {
		tokens: Token[];
		workType: WorkType;
		selectedLemma: string | null;
		rangeIndices: Set<number>;
		coreLookup: (lemma: string) => boolean;
		onWordClick: (index: number, lemma: string, shiftKey: boolean) => void;
	}

	let { tokens, workType, selectedLemma, rangeIndices, coreLookup, onWordClick }: Props = $props();

	interface LineToken {
		token: Token;
		index: number | undefined;
	}

	interface Line {
		tokens: LineToken[];
		lineNumber: number | null;
	}

	function processTokens(tokens: Token[], isPoem: boolean): Line[] {
		const lines: Line[] = [];
		let currentTokens: LineToken[] = [];
		let poeticLineNum = 0;
		let wordCount = 0;
		let hasContent = false;

		function flushLine() {
			if (currentTokens.length > 0) {
				const lineNumber = isPoem && hasContent ? ++poeticLineNum : null;

				lines.push({
					tokens: [...currentTokens],
					lineNumber
				});
				currentTokens = [];
				hasContent = false;
			}
		}

		for (const token of tokens) {
			if (token.t === 'n') {
				flushLine();
			} else if (token.t === 's') {
				flushLine();
				lines.push({ tokens: [{ token, index: undefined }], lineNumber: null });
			} else if (token.t === 'w' && token.l) {
				hasContent = true;
				currentTokens.push({ token, index: wordCount });
				wordCount++;
			} else {
				currentTokens.push({ token, index: undefined });
			}
		}

		flushLine();
		return lines;
	}

	let lines = $derived(processTokens(tokens, workType === 'poem'));

	function shouldShowLineNumber(lineNum: number | null): boolean {
		return lineNum !== null && lineNum > 0 && lineNum % 5 === 0;
	}
</script>

<div class="text-display">
	{#each lines as line, lineIdx (lineIdx)}
		<div class="line">
			{#if workType === 'poem'}
				<span class="line-number">
					{#if shouldShowLineNumber(line.lineNumber)}
						{line.lineNumber}
					{/if}
				</span>
			{/if}
			<span class="line-content">
				{#each line.tokens as { token, index }, idx (idx)}
					{#if token.t === 'w'}
						<Word
							{token}
							{index}
							selected={selectedLemma === token.l && rangeIndices.size === 0}
							inRange={rangeIndices.has(index!)}
							isCore={coreLookup(token.l!)}
							onclick={(i, e) => onWordClick(i, token.l!, e.shiftKey)}
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
