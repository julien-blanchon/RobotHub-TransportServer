<script lang="ts">
	import { onMount } from 'svelte';
	import { robotics } from '@robothub/transport-server-client';
	import type { robotics as roboticsTypes } from '@robothub/transport-server-client';
	import { settings } from '$lib/settings.svelte';
	

	// Get data from load function
	let { data } = $props();
	let workspaceId = data.workspaceId;
	let roomIdFromUrl = data.roomId;

	// State
	let consumer: robotics.RoboticsConsumer;
	let connected = $state<boolean>(false);
	let connecting = $state<boolean>(false);
	let roomId = $state<string>(roomIdFromUrl || '');
	let participantId = $state<string>('');
	let error = $state<string>('');

	// Current robot state
	let currentJoints = $state<Record<string, number>>({});
	let lastUpdate = $state<Date | null>(null);

	// Real-time monitoring
	let updateCount = $state<number>(0);
	let stateSyncCount = $state<number>(0);
	let errorCount = $state<number>(0);

	// History tracking
	let jointHistory = $state<
		Array<{ timestamp: string; joints: roboticsTypes.JointData[]; source?: string }>
	>([]);
	let stateHistory = $state<Array<{ timestamp: string; state: Record<string, number> }>>([]);
	let errorHistory = $state<Array<{ timestamp: string; message: string }>>([]);

	// Visualization data for joint trend (last 20 updates)
	let jointTrends = $state<Record<string, number[]>>({});

	// Debug info
	let debugInfo = $state<{
		connectionAttempts: number;
		messagesReceived: number;
		lastMessageType: string;
		wsConnected: boolean;
		currentRoom: string;
		workspaceId: string;
	}>({
		connectionAttempts: 0,
		messagesReceived: 0,
		lastMessageType: '',
		wsConnected: false,
		currentRoom: '',
		workspaceId: workspaceId
	});

	function updateUrlWithRoom(roomId: string) {
		const url = new URL(window.location.href);
		url.searchParams.set('room', roomId);
		window.history.replaceState({}, '', url.toString());
	}

	async function connectConsumer() {
		if (!roomId.trim() || !participantId.trim()) {
			error = 'Please enter both Room ID and Participant ID';
			return;
		}

		debugInfo.connectionAttempts++;

		try {
			connecting = true;
			error = '';

			consumer = new robotics.RoboticsConsumer(settings.transportServerUrl);

			// Set up event handlers
			consumer.onConnected(() => {
				connected = true;
				connecting = false;
				debugInfo.wsConnected = true;
				debugInfo.currentRoom = roomId;
				loadInitialState();
				updateUrlWithRoom(roomId);
			});

			consumer.onDisconnected(() => {
				connected = false;
				debugInfo.wsConnected = false;
			});

			consumer.onError((errorMsg) => {
				error = errorMsg;
				errorCount++;
				debugInfo.messagesReceived++;
				debugInfo.lastMessageType = 'ERROR';
				errorHistory = [
					{
						timestamp: new Date().toLocaleTimeString(),
						message: errorMsg
					},
					...errorHistory
				].slice(0, 10); // Keep last 10 errors only
			});

			// Joint update callback
			consumer.onJointUpdate((joints) => {
				updateCount++;
				lastUpdate = new Date();
				debugInfo.messagesReceived++;
				debugInfo.lastMessageType = 'JOINT_UPDATE';

				// Update current state
				joints.forEach((joint) => {
					currentJoints[joint.name] = joint.value;

					// Update trends
					if (!jointTrends[joint.name]) {
						jointTrends[joint.name] = [];
					}
					jointTrends[joint.name] = [...jointTrends[joint.name], joint.value].slice(-10); // Keep last 10 only
				});

				// Add to history
				jointHistory = [
					{
						timestamp: new Date().toLocaleTimeString(),
						joints,
						source: 'producer'
					},
					...jointHistory
				].slice(0, 20); // Keep last 20 updates only
			});

			// State sync callback
			consumer.onStateSync((state) => {
				stateSyncCount++;
				lastUpdate = new Date();
				debugInfo.messagesReceived++;
				debugInfo.lastMessageType = 'STATE_SYNC';

				// Update current state
				currentJoints = { ...state };

				// Update trends for all joints
				Object.entries(state).forEach(([name, value]) => {
					if (!jointTrends[name]) {
						jointTrends[name] = [];
					}
					jointTrends[name] = [...jointTrends[name], value].slice(-10); // Keep last 10 only
				});

				// Add to history
				stateHistory = [
					{
						timestamp: new Date().toLocaleTimeString(),
						state
					},
					...stateHistory
				].slice(0, 10); // Keep last 10 state syncs only
			});

			const success = await consumer.connect(workspaceId, roomId, participantId);
			if (!success) {
				error = 'Failed to connect. Room might not exist.';
				connecting = false;
			}
		} catch (err) {
			error = `Connection failed: ${err}`;
			connecting = false;
		}
	}

	async function loadInitialState() {
		if (!consumer || !connected) return;

		try {
			const state = await consumer.getStateSyncAsync();
			if (Object.keys(state).length > 0) {
				currentJoints = state;
				// Initialize trends
				Object.entries(state).forEach(([name, value]) => {
					jointTrends[name] = [value];
				});
			}
		} catch (err) {
			console.error('Failed to load initial state:', err);
		}
	}

	async function exitSession() {
		if (consumer && connected) {
			await consumer.disconnect();
		}
		connected = false;
		debugInfo.wsConnected = false;
		debugInfo.currentRoom = '';
	}

	function clearHistory() {
		jointHistory = [];
		stateHistory = [];
		errorHistory = [];
		updateCount = 0;
		stateSyncCount = 0;
		errorCount = 0;
		debugInfo.messagesReceived = 0;
	}

	// Update roomId when URL parameter changes
	$effect(() => {
		if (roomIdFromUrl) {
			roomId = roomIdFromUrl;
		}
	});

	// Update debugInfo when workspaceId changes
	$effect(() => {
		debugInfo.workspaceId = workspaceId;
	});

	onMount(() => {
		participantId = `consumer_${Date.now()}`;

		return () => {
			exitSession();
		};
	});
</script>

<svelte:head>
	<title>Robotics Consumer{roomId ? ` - Room ${roomId}` : ''} - Workspace {workspaceId} - RobotHub TransportServer</title>
</svelte:head>

<div class="mx-auto max-w-6xl space-y-6">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<div>
			<h1 class="font-mono text-2xl font-bold text-gray-900">🤖 Robotics Consumer</h1>
			<p class="mt-1 font-mono text-sm text-gray-600">
				Workspace: <span class="font-bold text-blue-600">{workspaceId}</span>
				{#if roomId}
					| Room: <span class="font-bold text-blue-600">{roomId}</span>
				{:else}
					| Monitor robot arm state in real-time
				{/if}
			</p>
		</div>
		<div class="flex items-center space-x-4">
			<div class="flex items-center space-x-2">
				{#if connected}
					<div class="h-3 w-3 rounded-full bg-green-500"></div>
					<span class="font-mono text-sm font-medium text-green-700">Connected</span>
				{:else if connecting}
					<div class="h-3 w-3 animate-pulse rounded-full bg-yellow-500"></div>
					<span class="font-mono text-sm font-medium text-yellow-700">Connecting...</span>
				{:else}
					<div class="h-3 w-3 rounded-full bg-red-500"></div>
					<span class="font-mono text-sm font-medium text-red-700">Disconnected</span>
				{/if}
			</div>
			<a
				href="/{workspaceId}/robotics"
				class="rounded border bg-gray-100 px-3 py-2 font-mono text-sm hover:bg-gray-200"
			>
				← Back to Robotics
			</a>
		</div>
	</div>

	<!-- Debug Info -->
	<div class="rounded border bg-gray-900 p-4 font-mono text-sm text-green-400">
		<div class="mb-2 font-bold">ROBOTICS CONSUMER DEBUG - WORKSPACE {debugInfo.workspaceId}{roomId ? ` - ROOM ${roomId}` : ''}</div>
		<div class="grid grid-cols-3 gap-4 md:grid-cols-5">
			<div>Attempts: {debugInfo.connectionAttempts}</div>
			<div>Messages: {debugInfo.messagesReceived}</div>
			<div>Last: {debugInfo.lastMessageType || 'None'}</div>
			<div>WS: {debugInfo.wsConnected ? 'ON' : 'OFF'}</div>
			<div>Room: {debugInfo.currentRoom || 'None'}</div>
		</div>
		<div class="mt-2 grid grid-cols-3 gap-4">
			<div>Updates: {updateCount}</div>
			<div>State Syncs: {stateSyncCount}</div>
			<div>Errors: {errorCount}</div>
		</div>
		<div class="mt-2">Last Update: {lastUpdate ? lastUpdate.toLocaleTimeString() : 'Never'}</div>
		{#if error}
			<div class="mt-2 text-red-400">Error: {error}</div>
		{/if}
	</div>

	{#if !connected}
		<!-- Connection Section -->
		<div class="rounded border p-6">
			<h2 class="mb-4 font-mono text-lg font-semibold">Connect to Robotics Room</h2>

			<div class="grid grid-cols-1 gap-6 md:grid-cols-2">
				<div>
					<label for="roomId" class="mb-1 block font-mono text-sm font-medium text-gray-700">
						Room ID
					</label>
					<input
						id="roomId"
						type="text"
						bind:value={roomId}
						placeholder="Enter room ID to monitor"
						class="w-full rounded border border-gray-300 px-3 py-2 font-mono focus:border-blue-500 focus:ring-blue-500"
					/>
				</div>
				<div>
					<label for="participantId" class="mb-1 block font-mono text-sm font-medium text-gray-700">
						Participant ID
					</label>
					<input
						id="participantId"
						type="text"
						bind:value={participantId}
						placeholder="Your participant ID"
						class="w-full rounded border border-gray-300 px-3 py-2 font-mono focus:border-blue-500 focus:ring-blue-500"
					/>
				</div>
			</div>

			<div class="mt-4">
				<button
					onclick={connectConsumer}
					disabled={connecting || !roomId.trim() || !participantId.trim()}
					class={[
						'rounded border px-4 py-2 font-mono',
						connecting || !roomId.trim() || !participantId.trim()
							? 'bg-gray-200 text-gray-500'
							: 'bg-blue-600 text-white hover:bg-blue-700'
					]}
				>
					{connecting ? 'Connecting...' : 'Join as Observer'}
				</button>
			</div>

			{#if error}
				<div class="mt-4 rounded border border-red-200 bg-red-50 p-4">
					<p class="font-mono text-sm text-red-700">{error}</p>
				</div>
			{/if}
		</div>
	{:else}
		<!-- Monitoring Interface -->
		<div class="space-y-6">
			<!-- Status Overview -->
			<div class="grid grid-cols-2 gap-4 md:grid-cols-4">
				<div class="rounded border p-4 text-center">
					<div class="font-mono text-2xl font-bold text-blue-600">{updateCount}</div>
					<div class="font-mono text-sm text-gray-500">Joint Updates</div>
				</div>
				<div class="rounded border p-4 text-center">
					<div class="font-mono text-2xl font-bold text-purple-600">{stateSyncCount}</div>
					<div class="font-mono text-sm text-gray-500">State Syncs</div>
				</div>
				<div class="rounded border p-4 text-center">
					<div class="font-mono text-2xl font-bold text-red-600">{errorCount}</div>
					<div class="font-mono text-sm text-gray-500">Errors</div>
				</div>
				<div class="rounded border p-4 text-center">
					<div class="font-mono text-2xl font-bold text-green-600">
						{lastUpdate ? lastUpdate.toLocaleTimeString() : 'N/A'}
					</div>
					<div class="font-mono text-sm text-gray-500">Last Update</div>
				</div>
			</div>

			<!-- Robot State Display -->
			<div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
				<!-- Robot Visualization -->
				<div class="rounded border p-4 lg:col-span-2">
					<h2 class="mb-3 font-mono text-lg font-semibold">Robot Arm Visualization</h2>

					<div class="aspect-video rounded border bg-gray-50 p-4">
						<div class="flex h-full items-center justify-center">
							<div class="text-center">
								<div class="mb-4 text-6xl">🦾</div>
								<p class="font-mono text-gray-600">3D Robot Visualization</p>
								<p class="font-mono text-xs text-gray-500">Live joint positions from producer</p>
							</div>
						</div>
					</div>

					<!-- Current Joint Values -->
					{#if Object.keys(currentJoints).length > 0}
						<div class="mt-4 grid grid-cols-2 gap-4 md:grid-cols-3">
							{#each Object.entries(currentJoints) as [name, value]}
								<div class="text-center">
									<div class="font-mono text-sm text-gray-500 capitalize">
										{name.replace(/([A-Z])/g, ' $1').replace(/^./, (str) => str.toUpperCase())}
									</div>
									<div class="font-mono text-lg font-bold">{value.toFixed(1)}°</div>
								</div>
							{/each}
						</div>
					{/if}
				</div>

				<!-- Session Info & Controls -->
				<div class="space-y-6">
					<!-- Session Info -->
					<div class="rounded border p-4">
						<h2 class="mb-3 font-mono text-lg font-semibold">Session Info</h2>
						<div class="grid grid-cols-1 gap-2 font-mono text-sm">
							<div><span class="text-gray-500">Workspace:</span> {workspaceId}</div>
							<div><span class="text-gray-500">Room:</span> {roomId}</div>
							<div><span class="text-gray-500">ID:</span> {participantId}</div>
							<div><span class="text-gray-500">Role:</span> Consumer</div>
							<div><span class="text-gray-500">Active Joints:</span> {Object.keys(currentJoints).length}</div>
						</div>
						<div class="mt-4 flex space-x-3">
							<button
								onclick={clearHistory}
								class="rounded border bg-gray-100 px-3 py-2 font-mono text-sm hover:bg-gray-200"
							>
								Clear History
							</button>
							<button
								onclick={exitSession}
								class="rounded border bg-gray-100 px-3 py-2 font-mono text-sm hover:bg-gray-200"
							>
								🚪 Exit Session
							</button>
						</div>
					</div>

					<!-- Joint Trends -->
					{#if Object.keys(jointTrends).length > 0}
						<div class="rounded border p-4">
							<h2 class="mb-3 font-mono text-lg font-semibold">Joint Trends</h2>
							<div class="max-h-48 space-y-2 overflow-y-auto">
								{#each Object.entries(jointTrends) as [name, values]}
									<div class="rounded bg-gray-50 p-2">
										<div class="flex items-center justify-between">
											<span class="font-mono text-xs text-gray-600 capitalize">
												{name.replace(/([A-Z])/g, ' $1').replace(/^./, (str) => str.toUpperCase())}
											</span>
											<span class="font-mono text-xs font-bold">
												{values[values.length - 1]?.toFixed(1) || '0.0'}°
											</span>
										</div>
										<div class="mt-1 flex h-4 items-end space-x-1">
											{#each values as value, i}
												<div
													class="w-2 bg-blue-300"
													style="height: {Math.abs(value) / 180 * 100}%"
													title="{value.toFixed(1)}°"
												></div>
											{/each}
										</div>
									</div>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			</div>

			<!-- Real-time Updates -->
			<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
				<!-- Joint Updates History -->
				<div class="rounded border p-4">
					<h2 class="mb-3 font-mono text-lg font-semibold">Recent Joint Updates</h2>
					<div class="max-h-64 space-y-2 overflow-y-auto">
						{#each jointHistory.slice(0, 10) as update}
							<div class="rounded border-l-4 border-blue-200 bg-gray-50 p-2">
								<div class="flex items-center justify-between">
									<span class="font-mono text-xs text-gray-500">{update.timestamp}</span>
									<span class="font-mono text-xs text-blue-600">JOINT_UPDATE</span>
								</div>
								<div class="mt-1 text-sm">
									<span class="font-mono text-gray-700">
										{update.joints.length} joint(s): 
										{update.joints.map(j => `${j.name}=${j.value.toFixed(1)}°`).join(', ')}
									</span>
								</div>
							</div>
						{:else}
							<p class="py-4 text-center font-mono text-sm text-gray-500">No joint updates received yet</p>
						{/each}
					</div>
				</div>

				<!-- State Sync History -->
				<div class="rounded border p-4">
					<h2 class="mb-3 font-mono text-lg font-semibold">State Sync History</h2>
					<div class="max-h-64 space-y-2 overflow-y-auto">
						{#each stateHistory as state}
							<div class="rounded border-l-4 border-purple-200 bg-gray-50 p-2">
								<div class="flex items-center justify-between">
									<span class="font-mono text-xs text-gray-500">{state.timestamp}</span>
									<span class="font-mono text-xs text-purple-600">STATE_SYNC</span>
								</div>
								<div class="mt-1 text-sm">
									<div class="font-mono text-gray-700">
										{Object.keys(state.state).length} joints synchronized
									</div>
								</div>
							</div>
						{:else}
							<p class="py-4 text-center font-mono text-sm text-gray-500">
								No state syncs received yet
							</p>
						{/each}
					</div>
				</div>
			</div>

			<!-- Error History -->
			{#if errorHistory.length > 0}
				<div class="rounded border p-4">
					<h2 class="mb-3 font-mono text-lg font-semibold">Recent Errors</h2>
					<div class="max-h-32 space-y-2 overflow-y-auto">
						{#each errorHistory as error}
							<div class="rounded border-l-4 border-red-200 bg-red-50 p-2">
								<div class="flex items-center justify-between">
									<span class="font-mono text-xs text-gray-500">{error.timestamp}</span>
									<span class="font-mono text-xs text-red-600">ERROR</span>
								</div>
								<div class="mt-1 font-mono text-sm text-red-700">
									{error.message}
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	{/if}
</div> 