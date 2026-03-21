<script lang="ts">
	import Button from './Button.svelte';
	import { appState } from '$lib/stores/app-state';
</script>

<Button variant="primary" onclick={() => appState.cycleInterfaceLang()}>
	{$appState.interfaceLang === 'english' ? 'English' : $appState.interfaceLang === 'latin' ? 'Latīnē' : 'Ἑλληνιστί'}
</Button>
