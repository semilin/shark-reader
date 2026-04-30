import { readdirSync, readFileSync, statSync, writeFileSync } from 'fs';
import { join } from 'path';

const STATIC_DIR = new URL('../static', import.meta.url).pathname;

function minifyJsonFiles(dir) {
	for (const entry of readdirSync(dir, { withFileTypes: true })) {
		const path = join(dir, entry.name);
		if (entry.isDirectory()) {
			minifyJsonFiles(path);
		} else if (entry.name.endsWith('.json')) {
			const before = statSync(path).size;
			const data = JSON.parse(readFileSync(path, 'utf-8'));
			writeFileSync(path, JSON.stringify(data));
			const after = statSync(path).size;
			console.log(`Minified ${path} (${before} -> ${after} bytes)`);
		}
	}
}

minifyJsonFiles(STATIC_DIR);
