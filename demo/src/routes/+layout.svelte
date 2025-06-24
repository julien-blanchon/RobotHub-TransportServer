<script lang="ts">
	import '../app.css';
	import { page } from '$app/stores';

	let { children } = $props();

	// Extract workspace ID from the current route
	let workspaceId = $derived($page.params.workspaceId as string | undefined);
	let isWorkspaceRoute = $derived(!!workspaceId);
</script>

<div class="min-h-screen bg-gray-50">
	<!-- Navigation Header -->
	<header class="border-b bg-white shadow-sm">
		<div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
			<div class="flex h-14 items-center justify-between">
				<div class="flex items-center">
					<h1 class="font-mono text-lg font-bold text-gray-900">🤖 LeRobot Arena Debug</h1>
					{#if isWorkspaceRoute}
						<div class="ml-4 rounded bg-blue-100 px-2 py-1">
							<span class="font-mono text-xs text-blue-800">Workspace: {workspaceId}</span>
						</div>
					{/if}
				</div>
				<nav class="flex space-x-6">
					{#if isWorkspaceRoute}
						<!-- Workspace-scoped navigation -->
						<a
							href="/{workspaceId}"
							class={[
								'rounded-md px-3 py-2 font-mono text-sm font-medium',
								$page.url.pathname === `/${workspaceId}` || $page.url.pathname === `/${workspaceId}/`
									? 'bg-gray-100 text-gray-900'
									: 'text-gray-500 hover:text-gray-700'
							]}
						>
							Dashboard
						</a>
						<a
							href="/{workspaceId}/robotics"
							class={[
								'rounded-md px-3 py-2 font-mono text-sm font-medium',
								$page.url.pathname.startsWith(`/${workspaceId}/robotics`)
									? 'bg-gray-100 text-gray-900'
									: 'text-gray-500 hover:text-gray-700'
							]}
						>
							Robotics
						</a>
						<a
							href="/{workspaceId}/video"
							class={[
								'rounded-md px-3 py-2 font-mono text-sm font-medium',
								$page.url.pathname.startsWith(`/${workspaceId}/video`)
									? 'bg-gray-100 text-gray-900'
									: 'text-gray-500 hover:text-gray-700'
							]}
						>
							Video
						</a>
					{:else}
						<!-- Root navigation -->
						<a
							href="/"
							class={[
								'rounded-md px-3 py-2 font-mono text-sm font-medium',
								$page.url.pathname === '/'
									? 'bg-gray-100 text-gray-900'
									: 'text-gray-500 hover:text-gray-700'
							]}
						>
							Home
						</a>
					{/if}
				</nav>
			</div>
		</div>
	</header>

	<!-- Main Content -->
	<main class="mx-auto max-w-7xl px-4 py-4">
		{@render children()}
	</main>

	<!-- Footer -->
	<footer class="mt-auto border-t bg-white">
		<div class="mx-auto max-w-7xl px-4 py-3">
			<p class="text-center font-mono text-xs text-gray-500">
				LeRobot Arena Debug Tool - Real-time Library Testing
				{#if isWorkspaceRoute}
					| Workspace: {workspaceId}
				{/if}
			</p>
		</div>
	</footer>
</div>
