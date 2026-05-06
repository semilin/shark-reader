import fs from 'fs';
import path from 'path';

const TEXTS_DIR = 'static/texts';
const OUTPUT_DIR = 'static/stats';
const INDEX_FILE = path.join(TEXTS_DIR, 'index.json');

if (!fs.existsSync(OUTPUT_DIR)) {
	fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

async function generateStats() {
	const index = JSON.parse(fs.readFileSync(INDEX_FILE, 'utf-8'));
	const stats = {
		latin: {},
		greek: {}
	};

	for (const textInfo of index) {
		const lang = textInfo.language;
		const filePath = path.join('static', textInfo.path.replace('/shark-reader/', ''));
		if (!fs.existsSync(filePath)) {
			console.warn(`File not found: ${filePath}`);
			continue;
		}

		const textData = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
		const tokens = textData.tokens;

		for (const token of tokens) {
			if (token.t === 'w' && token.l) {
				const lemma = token.l;
				const word = token.w.toLowerCase().replace(/[.,\/#!$%\^&*;:{}=\-_`~()]/g, ""); // Basic punctuation strip

				if (!stats[lang][lemma]) {
					stats[lang][lemma] = {
						total: 0,
						forms: {},
						texts: {}
					};
				}

				stats[lang][lemma].total++;
				stats[lang][lemma].forms[word] = (stats[lang][lemma].forms[word] || 0) + 1;
				stats[lang][lemma].texts[textInfo.title] = (stats[lang][lemma].texts[textInfo.title] || 0) + 1;
			}
		}
	}

	for (const lang of ['latin', 'greek']) {
		const langStats = stats[lang];
		const lemmas = Object.keys(langStats);
		
		// Sort lemmas by total frequency to calculate percentiles
		const sortedLemmas = lemmas.slice().sort((a, b) => langStats[a].total - langStats[b].total);
		const totalLemmas = sortedLemmas.length;

		const finalStats = {};
		let currentFrequencyScore = 0;

		for (let i = 0; i < totalLemmas; i++) {
			const lemma = sortedLemmas[i];
			const data = langStats[lemma];

			if (i === 0 || data.total !== langStats[sortedLemmas[i - 1]].total) {
				// Find the last index with this same total to ensure tied frequencies get the same percentile
				let j = i;
				while (j + 1 < totalLemmas && langStats[sortedLemmas[j + 1]].total === data.total) {
					j++;
				}
				const rankMax = totalLemmas;
				const rankWord = totalLemmas - j;
				currentFrequencyScore = rankMax > 1
					? Math.max(0, ((Math.log(rankMax) - Math.log(rankWord)) / Math.log(rankMax)) * 100)
					: 100;
			}
			const frequencyScore = currentFrequencyScore;

			// Top 3 forms
			const topForms = Object.entries(data.forms)
				.sort((a, b) => b[1] - a[1])
				.slice(0, 3);

			// Texts ordered by frequency
			const sortedTexts = Object.entries(data.texts)
				.sort((a, b) => b[1] - a[1])
				.map(([title, count]) => ({ title, count }));

			finalStats[lemma] = {
				total: data.total,
				frequencyScore: parseFloat(frequencyScore.toFixed(1)),
				forms: topForms,
				texts: sortedTexts
			};
		}

		fs.writeFileSync(
			path.join(OUTPUT_DIR, `${lang}.json`),
			JSON.stringify(finalStats)
		);
		console.log(`Generated stats for ${lang}: ${totalLemmas} lemmas`);
	}
}

generateStats().catch(console.error);
