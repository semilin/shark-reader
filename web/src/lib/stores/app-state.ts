import { writable } from 'svelte/store';
import type { InterfaceLang } from '../types';

interface AppState {
	interfaceLang: InterfaceLang;
	readerReturnPath: string | null;
	readerScrollPosition: number;
	readerScrollPath: string | null;
}

function createAppStore() {
	const { subscribe, set, update } = writable<AppState>({
		interfaceLang: 'english',
		readerReturnPath: null,
		readerScrollPosition: 0
,		readerScrollPath: null
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
		setReaderReturnPath: (path: string | null) =>
			update((state) => ({ ...state, readerReturnPath: path })),
		setReaderScrollPosition: (pos: number) =>
			update((state) => ({ ...state, readerScrollPosition: pos })),
		setReaderScrollPath: (path: string | null) =>
			update((state) => ({ ...state, readerScrollPath: path })),
		reset: () => set({ interfaceLang: 'english', readerReturnPath: null, readerScrollPosition: 0, readerScrollPath: null })
	};
}

export const appState = createAppStore();
