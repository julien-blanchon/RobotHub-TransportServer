<script lang="ts">
	import { onMount } from 'svelte';
	import { robotics, video } from '@robothub/transport-server-client';
	import type { robotics as roboticsTypes, video as videoTypes } from '@robothub/transport-server-client';

	// Get data from load function
	let { data } = $props();
	let workspaceId = data.workspaceId;

	// State
	let roboticsRooms = $state<roboticsTypes.RoomInfo[]>([]);
	let videoRooms = $state<videoTypes.RoomInfo[]>([]);
	let loading = $state<boolean>(true);
	let roboticsError = $state<string>('');
	let videoError = $state<string>('');
	let roboticsClient: robotics.RoboticsClientCore;
	let videoClient: video.VideoClientCore;

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

	async function loadRooms() {
		const startTime = Date.now();
		debugInfo.refreshCount++;
		debugInfo.apiCalls += 2;

		try {
			loading = true;
			roboticsError = '';
			videoError = '';

			// Load robotics rooms
			try {
				roboticsClient = new robotics.RoboticsClientCore('https://blanchon-robothub-transportserver.hf.space/api');
				roboticsRooms = await roboticsClient.listRooms(workspaceId);
			} catch (err) {
				roboticsError = 'Failed to load robotics rooms';
				console.error('Failed to load robotics rooms:', err);
			}

			// Load video rooms
			try {
				videoClient = new video.VideoClientCore('https://blanchon-robothub-transportserver.hf.space/api');
				videoRooms = await videoClient.listRooms(workspaceId);
			} catch (err) {
				videoError = 'Failed to load video rooms';
				console.error('Failed to load video rooms:', err);
			}

			debugInfo.responseTime = Date.now() - startTime;
		} finally {
			loading = false;
			debugInfo.lastRefresh = new Date().toLocaleTimeString();
		}
	}

	async function createRoboticsRoom() {
		const roomId = prompt('Enter robotics room ID:');
		if (!roomId?.trim()) return;

		debugInfo.apiCalls++;
		try {
			await roboticsClient.createRoom(workspaceId, roomId);
			await loadRooms();
		} catch (err) {
			alert('Failed to create robotics room. It might already exist.');
			console.error('Failed to create robotics room:', err);
		}
	}

	async function createVideoRoom() {
		const roomId = prompt('Enter video room ID:');
		if (!roomId?.trim()) return;

		debugInfo.apiCalls++;
		try {
			await videoClient.createRoom(workspaceId, roomId);
			await loadRooms();
		} catch (err) {
			alert('Failed to create video room. It might already exist.');
			console.error('Failed to create video room:', err);
		}
	}

	onMount(() => {
		loadRooms();
		// Refresh rooms every 10 seconds
		const interval = setInterval(loadRooms, 10000);
		return () => clearInterval(interval);
	});
</script>

<svelte:head>
	<title>Workspace {workspaceId} - LeRobot Arena</title>
</svelte:head>

<div class="mx-auto max-w-7xl">
	<!-- Header -->
	<div class="mb-6 flex items-center justify-between">
		<div>
			<h1 class="font-mono text-2xl font-bold text-gray-900">🏠 Workspace Dashboard</h1>
			<p class="mt-1 font-mono text-sm text-gray-600">
				Workspace: <span class="font-bold text-blue-600">{workspaceId}</span>
				| Manage robotics and video rooms
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
			<a href="/" class="rounded border bg-gray-100 px-3 py-2 font-mono text-sm hover:bg-gray-200">
				← All Workspaces
			</a>
		</div>
	</div>

	<!-- Debug Info -->
	<div class="mb-6 rounded border bg-gray-900 p-4 font-mono text-sm text-green-400">
		<div class="mb-2 font-bold">WORKSPACE DEBUG - {workspaceId}</div>
		<div class="grid grid-cols-2 gap-4 md:grid-cols-4">
			<div>Last Refresh: {debugInfo.lastRefresh}</div>
			<div>Refresh Count: {debugInfo.refreshCount}</div>
			<div>API Calls: {debugInfo.apiCalls}</div>
			<div>Response Time: {debugInfo.responseTime}ms</div>
		</div>
		<div class="mt-2">
			Robotics Rooms: {roboticsRooms.length} | Video Rooms: {videoRooms.length} | Loading: {loading
				? 'YES'
				: 'NO'}
		</div>
		{#if roboticsError || videoError}
			<div class="mt-2 text-red-400">
				{#if roboticsError}Robotics Error: {roboticsError}{/if}
				{#if videoError}Video Error: {videoError}{/if}
			</div>
		{/if}
	</div>

	<!-- Quick Actions -->
	<div class="mb-6 rounded border p-4">
		<h2 class="mb-4 font-mono text-lg font-semibold">🚀 Quick Actions</h2>
		<div class="grid grid-cols-2 gap-3 md:grid-cols-4">
			<a
				href="/{workspaceId}/robotics"
				class={[
					'rounded border px-4 py-2 text-center font-mono',
					'bg-blue-600 text-white hover:bg-blue-700'
				]}
			>
				🤖 Robotics
			</a>
			<a
				href="/{workspaceId}/video"
				class={[
					'rounded border px-4 py-2 text-center font-mono',
					'bg-purple-600 text-white hover:bg-purple-700'
				]}
			>
				📹 Video
			</a>
			<a
				href="/{workspaceId}/robotics/producer"
				class={['rounded border px-4 py-2 text-center font-mono', 'bg-green-100 hover:bg-green-200']}
			>
				🎮 Robot Producer
			</a>
			<a
				href="/{workspaceId}/video/producer"
				class={['rounded border px-4 py-2 text-center font-mono', 'bg-pink-100 hover:bg-pink-200']}
			>
				📹 Video Producer
			</a>
		</div>
	</div>

	<!-- Rooms Overview -->
	<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
		<!-- Robotics Rooms -->
		<div class="rounded border p-4">
			<div class="mb-4 flex items-center justify-between">
				<h2 class="font-mono text-lg font-semibold">🤖 Robotics Rooms</h2>
				<div class="flex space-x-2">
					<button
						onclick={createRoboticsRoom}
						class="rounded border bg-blue-100 px-3 py-1 font-mono text-sm text-blue-700 hover:bg-blue-200"
					>
						➕ Create
					</button>
					<a
						href="/{workspaceId}/robotics"
						class="rounded border bg-gray-100 px-3 py-1 font-mono text-sm hover:bg-gray-200"
					>
						View All
					</a>
				</div>
			</div>

			{#if roboticsError}
				<div class="rounded border border-red-200 bg-red-50 p-4">
					<p class="font-mono text-sm text-red-700">{roboticsError}</p>
				</div>
			{:else if roboticsRooms.length === 0}
				<div class="py-8 text-center">
					<div class="mb-2 text-4xl text-gray-400">🤖</div>
					<p class="font-mono text-gray-500">No robotics rooms yet</p>
					<button
						onclick={createRoboticsRoom}
						class="mt-2 rounded border bg-blue-600 px-3 py-1 font-mono text-sm text-white hover:bg-blue-700"
					>
						Create First Room
					</button>
				</div>
			{:else}
				<div class="space-y-3">
					{#each roboticsRooms.slice(0, 3) as room}
						<div class="rounded border bg-gray-50 p-3">
							<div class="flex items-center justify-between">
								<div>
									<h3 class="font-mono font-medium">{room.id}</h3>
									<p class="font-mono text-sm text-gray-600">
										👥 {room.participants.total} participants
									</p>
								</div>
								<div class="flex space-x-2">
									<a
										href="/{workspaceId}/robotics/consumer?room={room.id}"
										class="rounded border bg-blue-100 px-2 py-1 font-mono text-xs text-blue-700 hover:bg-blue-200"
									>
										👁️ Monitor
									</a>
									{#if !room.participants.producer}
										<a
											href="/{workspaceId}/robotics/producer?room={room.id}"
											class="rounded border bg-green-100 px-2 py-1 font-mono text-xs text-green-700 hover:bg-green-200"
										>
											🎮 Control
										</a>
									{/if}
								</div>
							</div>
						</div>
					{/each}
					{#if roboticsRooms.length > 3}
						<div class="text-center">
							<a
								href="/{workspaceId}/robotics"
								class="font-mono text-sm text-blue-600 hover:text-blue-800"
							>
								... and {roboticsRooms.length - 3} more
							</a>
						</div>
					{/if}
				</div>
			{/if}
		</div>

		<!-- Video Rooms -->
		<div class="rounded border p-4">
			<div class="mb-4 flex items-center justify-between">
				<h2 class="font-mono text-lg font-semibold">📹 Video Rooms</h2>
				<div class="flex space-x-2">
					<button
						onclick={createVideoRoom}
						class="rounded border bg-purple-100 px-3 py-1 font-mono text-sm text-purple-700 hover:bg-purple-200"
					>
						➕ Create
					</button>
					<a
						href="/{workspaceId}/video"
						class="rounded border bg-gray-100 px-3 py-1 font-mono text-sm hover:bg-gray-200"
					>
						View All
					</a>
				</div>
			</div>

			{#if videoError}
				<div class="rounded border border-red-200 bg-red-50 p-4">
					<p class="font-mono text-sm text-red-700">{videoError}</p>
				</div>
			{:else if videoRooms.length === 0}
				<div class="py-8 text-center">
					<div class="mb-2 text-4xl text-gray-400">📹</div>
					<p class="font-mono text-gray-500">No video rooms yet</p>
					<button
						onclick={createVideoRoom}
						class="mt-2 rounded border bg-purple-600 px-3 py-1 font-mono text-sm text-white hover:bg-purple-700"
					>
						Create First Room
					</button>
				</div>
			{:else}
				<div class="space-y-3">
					{#each videoRooms.slice(0, 3) as room}
						<div class="rounded border bg-gray-50 p-3">
							<div class="flex items-center justify-between">
								<div>
									<h3 class="font-mono font-medium">{room.id}</h3>
									<p class="font-mono text-sm text-gray-600">
										👥 {room.participants.total} participants
										{#if room.participants.producer}
											| 🔴 Streaming
										{/if}
									</p>
								</div>
								<div class="flex space-x-2">
									<a
										href="/{workspaceId}/video/consumer?room={room.id}"
										class="rounded border bg-purple-100 px-2 py-1 font-mono text-xs text-purple-700 hover:bg-purple-200"
									>
										📺 Watch
									</a>
									{#if !room.participants.producer}
										<a
											href="/{workspaceId}/video/producer?room={room.id}"
											class="rounded border bg-pink-100 px-2 py-1 font-mono text-xs text-pink-700 hover:bg-pink-200"
										>
											📹 Stream
										</a>
									{/if}
								</div>
							</div>
						</div>
					{/each}
					{#if videoRooms.length > 3}
						<div class="text-center">
							<a
								href="/{workspaceId}/video"
								class="font-mono text-sm text-purple-600 hover:text-purple-800"
							>
								... and {videoRooms.length - 3} more
							</a>
						</div>
					{/if}
				</div>
			{/if}
		</div>
	</div>
</div> 