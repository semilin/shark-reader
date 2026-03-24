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

	let wordIndex = 0;

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

	function getWordIndex(lineIdx: number, tokenIdx: number): number {
		let count = 0;
		for (let i = 0; i < lineIdx; i++) {
			for (const token of lines[i].tokens) {
				if (token.t === 'w') count++;
			}
		}
		for (let i = 0; i < tokenIdx; i++) {
			if (lines[lineIdx].tokens[i].t === 'w') count++;
		}
		return count;
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
				{#each line.tokens as token, tokenIdx (tokenIdx)}
					{#if token.t === 'w' && token.l}
						{@const idx = getWordIndex(lineIdx, tokenIdx)}
						<Word
							{token}
							index={idx}
							selected={selectedLemma === token.l && rangeIndices.size === 0}
							inRange={rangeIndices.has(idx)}
							isCore={coreLookup(token.l)}
							onclick={(index, e) => onWordClick(index, token.l!, e.shiftKey)}
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
