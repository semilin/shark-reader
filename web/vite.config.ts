import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import { SvelteKitPWA } from '@vite-pwa/sveltekit';

export default defineConfig({
	plugins: [
		sveltekit(),
		SvelteKitPWA({
			registerType: 'autoUpdate',
			manifest: {
				name: 'SharkReader',
				short_name: 'SharkReader',
				description: 'Immersive reader for Latin and Ancient Greek',
				theme_color: '#1a1a2e',
				background_color: '#1a1a2e',
				display: 'standalone',
				icons: [
					{
						src: '/shark-reader/favicon.png',
						sizes: '192x192',
						type: 'image/png'
					},
					{
						src: '/shark-reader/favicon.png',
						sizes: '512x512',
						type: 'image/png'
					}
				]
			},
			workbox: {
				globPatterns: ['**/*.{js,css,html,ico,png,svg,json}']
			}
		})
	]
});
