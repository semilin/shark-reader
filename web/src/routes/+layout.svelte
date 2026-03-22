<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>SharkReader</title>
</svelte:head>

<div class="app-container">
	{@render children()}
</div>

<style>
	.app-container {
		height: 100vh;
		max-width: 1400px;
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}
</style>
