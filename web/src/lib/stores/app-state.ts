import { writable } from 'svelte/store';
import type { InterfaceLang } from '../types';

interface AppState {
	interfaceLang: InterfaceLang;
}

function createAppStore() {
	const { subscribe, set, update } = writable<AppState>({
		interfaceLang: 'english'
	});

	return {
		subscribe,
		setInterfaceLang: (lang: InterfaceLang) =>
			update((state) => ({ ...state, interfaceLang: lang })),
		cycleInterfaceLang: () =>
			update((state) => {
				const order: InterfaceLang[] = ['english', 'latin', 'greek'];
				const currentIndex = order.indexOf(state.interfaceLang);
				const nextIndex = (currentIndex + 1) % order.length;
				return { ...state, interfaceLang: order[nextIndex] };
			}),
		reset: () => set({ interfaceLang: 'english' })
	};
}

export const appState = createAppStore();
