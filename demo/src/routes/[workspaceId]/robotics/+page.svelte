<script lang="ts">
	import { onMount } from 'svelte';
	import { robotics } from '@robothub/transport-server-client';
	import type { robotics as roboticsTypes } from '@robothub/transport-server-client';
	

	// Get data from load function
	let { data } = $props();
	let workspaceId = data.workspaceId;

	// State
	let rooms = $state<roboticsTypes.RoomInfo[]>([]);
	let loading = $state<boolean>(true);
	let error = $state<string>('');
	let newRoomId = $state<string>('');
	let showCreateRoom = $state<boolean>(false);
	let client: robotics.RoboticsClientCore;

	// Debug info
	let debugInfo = $state<{
		lastRefresh: string;
		refreshCount: number;
		responseTime: number;
		apiCalls: number;
	}>({
		lastRefresh: '',
		refreshCount: 0,
		responseTime: 0,
		apiCalls: 0
	});

	// Store scroll position to prevent jumping
	let scrollPosition = 0;

	async function loadRooms() {
		// Save current scroll position
		scrollPosition = window.scrollY;

		const startTime = Date.now();
		debugInfo.refreshCount++;
		debugInfo.apiCalls++;

		try {
			loading = true;
			error = '';
			client = new robotics.RoboticsClientCore('https://blanchon-robothub-transportserver.hf.space/api');
			rooms = await client.listRooms(workspaceId);
			debugInfo.responseTime = Date.now() - startTime;
		} catch (err) {
			error = "Failed to connect to server. Make sure it's running on https://blanchon-robothub-transportserver.hf.space/api";
			console.error('Failed to load robotics rooms:', err);
			debugInfo.responseTime = Date.now() - startTime;
		} finally {
			loading = false;
			debugInfo.lastRefresh = new Date().toLocaleTimeString();

			// Restore scroll position after a small delay
			setTimeout(() => {
				window.scrollTo(0, scrollPosition);
			}, 50);
		}
	}

	async function createRoom() {
		if (!newRoomId.trim()) {
			alert('Please enter a room ID');
			return;
		}

		debugInfo.apiCalls++;
		try {
			await client.createRoom(workspaceId, newRoomId);
			newRoomId = '';
			showCreateRoom = false;
			await loadRooms();
		} catch (err) {
			alert('Failed to create robotics room. It might already exist.');
			console.error('Failed to create robotics room:', err);
		}
	}

	async function deleteRoom(roomId: string) {
		debugInfo.apiCalls++;
		try {
			await client.deleteRoom(workspaceId, roomId);
			await loadRooms();
		} catch (err) {
			alert('Failed to delete robotics room');
			console.error('Failed to delete robotics room:', err);
		}
	}

	onMount(() => {
		loadRooms();
		// Refresh rooms every 5 seconds
		const interval = setInterval(loadRooms, 5000);
		return () => clearInterval(interval);
	});
</script>

<svelte:head>
	<title>Robotics Control - Workspace {workspaceId} - RobotHub TransportServer</title>
</svelte:head>

<div class="mx-auto max-w-7xl">
	<!-- Header -->
	<div class="mb-6 flex items-center justify-between">
		<div>
			<h1 class="font-mono text-2xl font-bold text-gray-900">🤖 Robotics Control Console</h1>
			<p class="mt-1 font-mono text-sm text-gray-600">
				Workspace: <span class="font-bold text-blue-600">{workspaceId}</span>
				| Real-time robot arm control and monitoring
			</p>
		</div>
		<div class="flex space-x-3">
			<button
				onclick={loadRooms}
				disabled={loading}
				class={[
					'rounded border px-3 py-2 font-mono text-sm',
					loading ? 'bg-gray-100 text-gray-500' : 'bg-gray-100 hover:bg-gray-200'
				]}
			>
				{loading ? '🔄 Loading...' : '🔄 Refresh'}
			</button>
			<button
				onclick={() => (showCreateRoom = true)}
				class="rounded border bg-blue-600 px-3 py-2 font-mono text-sm text-white hover:bg-blue-700"
			>
				➕ Create Room
			</button>
			<a
				href="/{workspaceId}"
				class="rounded border bg-gray-100 px-3 py-2 font-mono text-sm hover:bg-gray-200"
			>
				← Back to Workspace
			</a>
		</div>
	</div>

	<!-- Debug Info -->
	<div class="mb-6 rounded border bg-gray-900 p-4 font-mono text-sm text-green-400">
		<div class="mb-2 font-bold">ROBOTICS DEBUG - WORKSPACE {workspaceId}</div>
		<div class="grid grid-cols-2 gap-4 md:grid-cols-4">
			<div>Last Refresh: {debugInfo.lastRefresh}</div>
			<div>Refresh Count: {debugInfo.refreshCount}</div>
			<div>API Calls: {debugInfo.apiCalls}</div>
			<div>Response Time: {debugInfo.responseTime}ms</div>
		</div>
		<div class="mt-2">
			Active Rooms: {rooms.length} | Loading: {loading ? 'YES' : 'NO'}
		</div>
		{#if error}
			<div class="mt-2 text-red-400">Error: {error}</div>
		{/if}
	</div>

	<!-- Error State -->
	{#if error}
		<div class="mb-6 rounded border border-red-200 bg-red-50 p-4">
			<div class="flex">
				<div class="flex-shrink-0">
					<span class="text-red-400">⚠️</span>
				</div>
				<div class="ml-3">
					<h3 class="font-mono text-sm font-medium text-red-800">Connection Error</h3>
					<div class="mt-2 font-mono text-sm text-red-700">
						<p>{error}</p>
					</div>
				</div>
			</div>
		</div>
	{/if}

	<!-- Quick Launch -->
	<div class="mb-6 rounded border p-4">
		<h2 class="mb-4 font-mono text-lg font-semibold">🚀 Quick Launch</h2>
		<div class="grid grid-cols-2 gap-3 md:grid-cols-4">
			<a
				href="/{workspaceId}/robotics/producer"
				class={[
					'rounded border px-4 py-2 text-center font-mono',
					'bg-green-600 text-white hover:bg-green-700'
				]}
			>
				🎮 Producer
			</a>
			<a
				href="/{workspaceId}/robotics/consumer"
				class={[
					'rounded border px-4 py-2 text-center font-mono',
					'bg-blue-600 text-white hover:bg-blue-700'
				]}
			>
				📊 Consumer
			</a>
			<a
				href="/{workspaceId}"
				class={['rounded border px-4 py-2 text-center font-mono', 'bg-gray-100 hover:bg-gray-200']}
			>
				🏠 Workspace
			</a>
			<button
				onclick={() => (showCreateRoom = true)}
				class={['rounded border px-4 py-2 font-mono', 'bg-purple-600 text-white hover:bg-purple-700']}
			>
				➕ New Room
			</button>
		</div>
	</div>

	<!-- Rooms List -->
	<div class="rounded border p-4">
		<div class="mb-6 flex items-center justify-between">
			<h2 class="font-mono text-lg font-semibold">Active Robotics Rooms</h2>
			<span class="font-mono text-sm text-gray-500">
				{rooms.length} room{rooms.length !== 1 ? 's' : ''} active in this workspace
			</span>
		</div>

		{#if loading}
			<div class="py-8 text-center">
				<div
					class="inline-block h-8 w-8 animate-spin rounded-full border-b-2 border-blue-500"
				></div>
				<p class="mt-2 font-mono text-gray-500">Loading robotics rooms...</p>
			</div>
		{:else if rooms.length === 0}
			<div class="py-8 text-center">
				<div class="mb-4 text-6xl text-gray-400">🤖</div>
				<h3 class="mb-2 font-mono text-lg font-medium">No Active Robotics Rooms</h3>
				<p class="mb-4 font-mono text-gray-500">Create a room to start robot control</p>
				<button
					onclick={() => (showCreateRoom = true)}
					class="rounded border bg-blue-600 px-4 py-2 font-mono text-white hover:bg-blue-700"
				>
					Create First Room
				</button>
			</div>
		{:else}
			<div class="space-y-4">
				{#each rooms as room}
					<div class="rounded border p-4 hover:bg-gray-50">
						<div class="flex items-center justify-between">
							<div class="flex-1">
								<div class="mb-2 flex items-center space-x-3">
									<h3 class="font-mono text-lg font-medium">{room.id}</h3>
									{#if room.participants.producer}
										<span class="rounded bg-green-100 px-2 py-1 font-mono text-xs text-green-800">
											✓ Producer Active
										</span>
									{:else}
										<span class="rounded bg-gray-100 px-2 py-1 font-mono text-xs text-gray-600">
											○ No Producer
										</span>
									{/if}
								</div>

								<div class="space-y-1 font-mono text-sm text-gray-600">
									<div>👥 Participants: {room.participants.total}</div>
									<div>📊 Consumers: {room.participants.consumers.length}</div>
									<div>🎮 Producer: {room.participants.producer || 'None'}</div>
								</div>

								{#if room.participants.consumers.length > 0}
									<div class="mt-1 font-mono text-xs text-blue-600">
										Consumers: {room.participants.consumers.join(', ')}
									</div>
								{/if}
							</div>

							<div class="flex items-center space-x-2">
								<a
									href="/{workspaceId}/robotics/consumer?room={room.id}"
									class={[
										'rounded border px-3 py-2 font-mono text-sm',
										'bg-blue-100 text-blue-700 hover:bg-blue-200'
									]}
								>
									📊 Monitor
								</a>

								{#if !room.participants.producer}
									<a
										href="/{workspaceId}/robotics/producer?room={room.id}"
										class={[
											'rounded border px-3 py-2 font-mono text-sm',
											'bg-green-100 text-green-700 hover:bg-green-200'
										]}
									>
										🎮 Control
									</a>
								{:else}
									<span class="px-3 py-2 font-mono text-sm text-gray-400">Producer occupied</span>
								{/if}

								<button
									onclick={() => deleteRoom(room.id)}
									class={[
										'rounded border px-3 py-2 font-mono text-sm',
										'bg-red-100 text-red-700 hover:bg-red-200'
									]}
								>
									🗑️ Delete
								</button>
							</div>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>

<!-- Create Room Modal -->
{#if showCreateRoom}
	<div class="bg-opacity-50 fixed inset-0 z-50 flex items-center justify-center bg-gray-600 p-4">
		<div class="w-full max-w-md rounded border bg-white p-6 shadow-xl">
			<h3 class="mb-4 font-mono text-lg font-medium">Create New Robotics Room</h3>

			<div class="mb-4">
				<label for="roomId" class="mb-2 block font-mono text-sm font-medium text-gray-700">
					Room ID
				</label>
				<input
					id="roomId"
					type="text"
					bind:value={newRoomId}
					placeholder="Enter unique room ID"
					class="w-full rounded border border-gray-300 px-3 py-2 font-mono focus:border-blue-500 focus:ring-blue-500"
				/>
				<p class="mt-1 font-mono text-xs text-gray-500">
					Use alphanumeric characters, hyphens, and underscores
				</p>
			</div>

			<div class="flex justify-end space-x-3">
				<button
					onclick={() => {
						showCreateRoom = false;
						newRoomId = '';
					}}
					class="rounded border bg-gray-100 px-4 py-2 font-mono hover:bg-gray-200"
				>
					Cancel
				</button>
				<button
					onclick={createRoom}
					disabled={!newRoomId.trim()}
					class={[
						'rounded border px-4 py-2 font-mono',
						newRoomId.trim()
							? 'bg-blue-600 text-white hover:bg-blue-700'
							: 'bg-gray-200 text-gray-500'
					]}
				>
					Create Room
				</button>
			</div>
		</div>
	</div>
{/if} 