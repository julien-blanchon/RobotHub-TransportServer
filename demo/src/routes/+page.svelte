<script lang="ts">
	import { onMount } from 'svelte';
	import { robotics } from '@robohub/transport-server-client';
	import type { robotics as roboticsTypes } from '@robohub/transport-server-client';
	import { goto } from '$app/navigation';

	// Server status
	let serverStatus = $state<'checking' | 'connected' | 'error'>('checking');
	let serverInfo = $state<{ rooms: number; version: string }>({ rooms: 0, version: 'Unknown' });
	let rooms = $state<roboticsTypes.RoomInfo[]>([]);
	let lastError = $state<string>('');
	let debugInfo = $state<{
		lastCheck: string;
		connectionAttempts: number;
		responseTime: number;
	}>({
		lastCheck: '',
		connectionAttempts: 0,
		responseTime: 0
	});

	// Workspace management
	let workspaceInput = $state<string>('');
	let recentWorkspaces = $state<string[]>([]);
	let error = $state<string>('');

	async function checkServerStatus() {
		const startTime = Date.now();
		debugInfo.connectionAttempts++;

		try {
			// Use relative URL so it works in both development and production
			const baseUrl = typeof window !== 'undefined' ? window.location.origin : 'http://localhost:7860';
			const apiUrl = `${baseUrl}/api`;
			const client = new robotics.RoboticsClientCore(apiUrl);
			const roomList = await client.listRooms('');
			rooms = roomList;
			serverInfo = { rooms: roomList.length, version: '1.0.0' };
			serverStatus = 'connected';
			lastError = '';
			debugInfo.responseTime = Date.now() - startTime;
		} catch (error) {
			console.error('Server check failed:', error);
			serverStatus = 'error';
			lastError = error instanceof Error ? error.message : String(error);
			debugInfo.responseTime = Date.now() - startTime;
		}

		debugInfo.lastCheck = new Date().toLocaleTimeString();
	}

	// Generate a new workspace ID
	function generateWorkspaceId(): string {
		return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
			const r = Math.random() * 16 | 0;
			const v = c === 'x' ? r : (r & 0x3 | 0x8);
			return v.toString(16);
		});
	}

	// Load recent workspaces from localStorage
	function loadRecentWorkspaces() {
		try {
			const stored = localStorage.getItem('lerobot-arena-workspaces');
			if (stored) {
				recentWorkspaces = JSON.parse(stored);
			}
		} catch (err) {
			console.warn('Failed to load recent workspaces:', err);
		}
	}

	// Save workspace to recent list
	function saveToRecentWorkspaces(workspaceId: string) {
		const updated = [workspaceId, ...recentWorkspaces.filter(id => id !== workspaceId)].slice(0, 10);
		recentWorkspaces = updated;
		try {
			localStorage.setItem('lerobot-arena-workspaces', JSON.stringify(updated));
		} catch (err) {
			console.warn('Failed to save recent workspaces:', err);
		}
	}

	// Create new workspace
	function createNewWorkspace() {
		const newWorkspaceId = generateWorkspaceId();
		saveToRecentWorkspaces(newWorkspaceId);
		goto(`/${newWorkspaceId}`);
	}

	// Join existing workspace
	function joinWorkspace() {
		if (!workspaceInput.trim()) {
			error = 'Please enter a workspace ID';
			return;
		}

		const workspaceId = workspaceInput.trim();
		saveToRecentWorkspaces(workspaceId);
		goto(`/${workspaceId}`);
	}

	// Join workspace from recent list
	function joinRecentWorkspace(workspaceId: string) {
		saveToRecentWorkspaces(workspaceId); // Move to top of recent list
		goto(`/${workspaceId}`);
	}

	// Remove workspace from recent list
	function removeRecentWorkspace(workspaceId: string) {
		recentWorkspaces = recentWorkspaces.filter(id => id !== workspaceId);
		try {
			localStorage.setItem('lerobot-arena-workspaces', JSON.stringify(recentWorkspaces));
		} catch (err) {
			console.warn('Failed to save recent workspaces:', err);
		}
	}

	onMount(() => {
		checkServerStatus();
		// Check server status every 10 seconds
		const interval = setInterval(checkServerStatus, 10000);
		loadRecentWorkspaces();
		return () => clearInterval(interval);
	});
</script>

<svelte:head>
	<title>LeRobot Arena - Workspace Selection</title>
</svelte:head>

<div class="mx-auto max-w-4xl p-4">
	<!-- Header -->
	<div class="mb-8 text-center">
		<h1 class="font-mono text-3xl font-bold text-gray-900">🤖 LeRobot Arena</h1>
		<p class="mt-2 font-mono text-lg text-gray-600">
			Real-time robotics control and monitoring platform
		</p>
		<p class="mt-1 font-mono text-sm text-gray-500">
			Select or create a workspace to get started
		</p>
	</div>

	<!-- Workspace Selection -->
	<div class="mb-8 space-y-6">
		<!-- Create New Workspace -->
		<div class="rounded border p-6">
			<div class="mb-4 text-center">
				<h2 class="font-mono text-xl font-semibold text-gray-900">Create New Workspace</h2>
				<p class="mt-1 font-mono text-sm text-gray-600">
					Start fresh with a new isolated workspace
				</p>
			</div>
			
			<div class="text-center">
				<button
					onclick={createNewWorkspace}
					class="rounded border bg-blue-600 px-6 py-3 font-mono text-white hover:bg-blue-700"
				>
					✨ Generate New Workspace
				</button>
			</div>
		</div>

		<!-- Join Existing Workspace -->
		<div class="rounded border p-6">
			<div class="mb-4 text-center">
				<h2 class="font-mono text-xl font-semibold text-gray-900">Join Existing Workspace</h2>
				<p class="mt-1 font-mono text-sm text-gray-600">
					Enter a workspace ID to join an existing session
				</p>
			</div>

			<div class="mx-auto max-w-md space-y-4">
				<div>
					<label for="workspaceInput" class="mb-1 block font-mono text-sm font-medium text-gray-700">
						Workspace ID
					</label>
					<input
						id="workspaceInput"
						type="text"
						bind:value={workspaceInput}
						placeholder="Enter workspace ID (UUID format)"
						class="w-full rounded border border-gray-300 px-3 py-2 font-mono focus:border-blue-500 focus:ring-blue-500"
						onkeydown={(e) => {
							if (e.key === 'Enter') {
								joinWorkspace();
							}
						}}
					/>
				</div>
				
				<button
					onclick={joinWorkspace}
					disabled={!workspaceInput.trim()}
					class={[
						'w-full rounded border px-4 py-2 font-mono',
						workspaceInput.trim()
							? 'bg-green-600 text-white hover:bg-green-700'
							: 'bg-gray-200 text-gray-500'
					]}
				>
					🚀 Join Workspace
				</button>

				{#if error}
					<div class="mt-2 rounded border border-red-200 bg-red-50 p-3">
						<p class="font-mono text-sm text-red-700">{error}</p>
					</div>
				{/if}
			</div>
		</div>

		<!-- Recent Workspaces -->
		{#if recentWorkspaces.length > 0}
			<div class="rounded border p-6">
				<div class="mb-4 text-center">
					<h2 class="font-mono text-xl font-semibold text-gray-900">Recent Workspaces</h2>
					<p class="mt-1 font-mono text-sm text-gray-600">
						Quick access to your previously used workspaces
					</p>
				</div>

				<div class="space-y-3">
					{#each recentWorkspaces as workspaceId}
						<div class="flex items-center justify-between rounded border bg-gray-50 p-3">
							<div>
								<div class="font-mono text-sm font-medium">{workspaceId}</div>
								<div class="font-mono text-xs text-gray-500">UUID Workspace</div>
							</div>
							<div class="flex space-x-2">
								<button
									onclick={() => joinRecentWorkspace(workspaceId)}
									class="rounded border bg-blue-100 px-3 py-1 font-mono text-sm text-blue-700 hover:bg-blue-200"
								>
									📂 Open
								</button>
								<button
									onclick={() => removeRecentWorkspace(workspaceId)}
									class="rounded border bg-red-100 px-3 py-1 font-mono text-sm text-red-700 hover:bg-red-200"
								>
									🗑️
								</button>
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}
	</div>

	<!-- About Workspaces -->
	<div class="rounded border bg-blue-50 p-6">
		<h3 class="mb-3 font-mono text-lg font-semibold text-blue-900">About Workspaces</h3>
		<div class="space-y-2 font-mono text-sm text-blue-800">
			<p>🔒 <strong>Isolation:</strong> Each workspace provides a secure, isolated environment for your robotics sessions</p>
			<p>🏠 <strong>Rooms:</strong> Create multiple rooms within a workspace for different robot configurations</p>
			<p>👥 <strong>Sharing:</strong> Share the workspace ID with others to collaborate on the same robots</p>
			<p>🔄 <strong>Real-time:</strong> All participants in a workspace see live updates from producers</p>
		</div>
	</div>
</div>
