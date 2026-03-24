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

	interface WordToken {
		token: Token;
		index: number;
	}

	interface Line {
		words: WordToken[];
		otherTokens: Token[];
		lineNumber: number;
	}

	function processTokens(tokens: Token[], isPoem: boolean): Line[] {
		const lines: Line[] = [];
		let currentWords: WordToken[] = [];
		let currentOther: Token[] = [];
		let lineNum = 0;
		let wordCount = 0;

		function flushLine() {
			if (currentWords.length > 0 || currentOther.length > 0) {
				lines.push({ 
					words: [...currentWords], 
					otherTokens: [...currentOther], 
					lineNumber: lineNum 
				});
				currentWords = [];
				currentOther = [];
			}
		}

		for (const token of tokens) {
			if (token.t === 'n') {
				flushLine();
				lineNum++;
			} else if (token.t === 's') {
				flushLine();
				lines.push({ words: [], otherTokens: [token], lineNumber: lineNum });
			} else if (token.t === 'w' && token.l) {
				currentWords.push({ token, index: wordCount });
				wordCount++;
			} else {
				currentOther.push(token);
			}
		}

		flushLine();
		return lines;
	}

	let lines = $derived(processTokens(tokens, workType === 'poem'));

	function shouldShowLineNumber(lineNum: number): boolean {
		return workType === 'poem' && lineNum > 0 && lineNum % 5 === 0;
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
				{#each line.words as { token, index } (index)}
					<Word
						{token}
						{index}
						selected={selectedLemma === token.l && rangeIndices.size === 0}
						inRange={rangeIndices.has(index)}
						isCore={coreLookup(token.l!)}
						onclick={(i, e) => onWordClick(i, token.l!, e.shiftKey)}
					/>
				{/each}
				{#each line.otherTokens as token, idx (idx)}
					<Word {token} />
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
