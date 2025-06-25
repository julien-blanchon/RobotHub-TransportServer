<script lang="ts">
	import { onMount } from 'svelte';
	import { robotics } from '@robothub/transport-server-client';
	import { settings } from '$lib/settings.svelte';
	

	// Get data from load function
	let { data } = $props();
	let workspaceId = data.workspaceId;
	let roomIdFromUrl = data.roomId;

	// State
	let producer: robotics.RoboticsProducer;
	let connected = $state<boolean>(false);
	let connecting = $state<boolean>(false);
	let roomId = $state<string>(roomIdFromUrl || '');
	let participantId = $state<string>('');
	let error = $state<string>('');

	// Robot arm joints (6-DOF)
	let joints = $state<{
		Rotation: number;
		Pitch: number;
		Elbow: number;
		Wrist_Pitch: number;
		Wrist_Roll: number;
		Jaw: number;
	}>({
		Rotation: 0.0,
		Pitch: 0.0,
		Elbow: 0.0,
		Wrist_Pitch: 0.0,
		Wrist_Roll: 0.0,
		Jaw: 0.0
	});

	type JointName = keyof typeof joints;

	// Joint limits (degrees)
	const jointLimits: Record<JointName, { min: number; max: number }> = {
		Rotation: { min: -180, max: 180 },
		Pitch: { min: -90, max: 90 },
		Elbow: { min: -135, max: 135 },
		Wrist_Pitch: { min: -180, max: 180 },
		Wrist_Roll: { min: -90, max: 90 },
		Jaw: { min: 0, max: 100 }
	};

	// Command history
	let commandHistory = $state<Array<{ timestamp: string; command: string; joints: any }>>([]);

	// Debug info
	let debugInfo = $state<{
		connectionAttempts: number;
		lastCommandSent: string;
		commandsSent: number;
		wsConnected: boolean;
		currentRoom: string;
		workspaceId: string;
	}>({
		connectionAttempts: 0,
		lastCommandSent: '',
		commandsSent: 0,
		wsConnected: false,
		currentRoom: '',
		workspaceId: workspaceId
	});

	// Auto-send joint updates when sliders change
	let sendTimeout: ReturnType<typeof setTimeout> | null = null;

	function handleJointChange(jointName: JointName) {
		if (!connected) return;

		if (sendTimeout) {
			clearTimeout(sendTimeout);
		}

		sendTimeout = setTimeout(() => {
			sendJointUpdate(jointName);
			sendTimeout = null;
		}, 5);
	}

	function updateUrlWithRoom(roomId: string) {
		const url = new URL(window.location.href);
		url.searchParams.set('room', roomId);
		window.history.replaceState({}, '', url.toString());
	}

	async function connectProducer() {
		if (!roomId.trim() || !participantId.trim()) {
			error = 'Please enter both Room ID and Participant ID';
			return;
		}

		debugInfo.connectionAttempts++;

		try {
			connecting = true;
			error = '';

			producer = new robotics.RoboticsProducer(settings.transportServerUrl);

			producer.onConnected(() => {
				connected = true;
				connecting = false;
				debugInfo.wsConnected = true;
				debugInfo.currentRoom = roomId;
				addToHistory('CONNECTED', 'Connected to room as producer');
				updateUrlWithRoom(roomId);
			});

			producer.onDisconnected(() => {
				connected = false;
				debugInfo.wsConnected = false;
				addToHistory('DISCONNECTED', 'Disconnected from room');
			});

			producer.onError((errorMsg) => {
				error = errorMsg;
				addToHistory('ERROR', errorMsg);
			});

			const success = await producer.connect(workspaceId, roomId, participantId);
			if (!success) {
				error = 'Failed to connect. Room might not exist or already have a producer.';
				connecting = false;
			}
		} catch (err) {
			error = `Connection failed: ${err}`;
			connecting = false;
		}
	}

	async function createNewRoom() {
		debugInfo.connectionAttempts++;

		try {
			connecting = true;
			error = '';

			producer = new robotics.RoboticsProducer(settings.transportServerUrl);

			producer.onConnected(() => {
				connected = true;
				connecting = false;
				roomId = producer.currentRoomId || '';
				debugInfo.wsConnected = true;
				debugInfo.currentRoom = roomId;
				addToHistory('ROOM_CREATED', `Created and connected to room ${roomId}`);
				updateUrlWithRoom(roomId);
			});

			producer.onDisconnected(() => {
				connected = false;
				debugInfo.wsConnected = false;
			});

			producer.onError((errorMsg) => {
				error = errorMsg;
				addToHistory('ERROR', errorMsg);
			});

			const roomData = await producer.createRoom(workspaceId);
			const success = await producer.connect(workspaceId, roomData.roomId, participantId || `producer_${Date.now()}`);

			if (success) {
				roomId = roomData.roomId;
				connected = true;
				connecting = false;
				debugInfo.wsConnected = true;
				debugInfo.currentRoom = roomId;
				addToHistory('ROOM_CREATED', `Created room ${roomId}`);
			}
		} catch (err) {
			error = `Failed to create room: ${err}`;
			connecting = false;
		}
	}

	async function sendJointUpdate(jointName?: JointName) {
		if (!connected || !producer) return;

		debugInfo.commandsSent++;
		debugInfo.lastCommandSent = 'JOINT_UPDATE';

		try {
			const jointData = jointName
				? [{ name: jointName, value: joints[jointName] }]
				: Object.entries(joints).map(([name, value]) => ({ name, value }));

			await producer.sendJointUpdate(jointData);

			const historyData = jointName ? { [jointName]: joints[jointName] } : joints;
			addToHistory('JOINT_UPDATE', historyData);
		} catch (err) {
			error = `Failed to send joint update: ${err}`;
		}
	}

	function addToHistory(command: string, data: any) {
		commandHistory = [
			{
				timestamp: new Date().toLocaleTimeString(),
				command,
				joints: data
			},
			...commandHistory
		].slice(0, 10);
	}

	function resetJoints() {
		joints = {
			Rotation: 0.0,
			Pitch: 0.0,
			Elbow: 0.0,
			Wrist_Pitch: 0.0,
			Wrist_Roll: 0.0,
			Jaw: 0.0
		};
		if (connected) {
			sendJointUpdate();
		}
	}

	async function exitSession() {
		if (producer && connected) {
			await producer.disconnect();
		}
		connected = false;
		debugInfo.wsConnected = false;
		debugInfo.currentRoom = '';
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
		participantId = `producer_${Date.now()}`;
		return () => {
			exitSession();
		};
	});
</script>

<svelte:head>
	<title>Robotics Producer{roomId ? ` - Room ${roomId}` : ''} - Workspace {workspaceId} - RobotHub TransportServer</title>
</svelte:head>

<div class="mx-auto max-w-6xl space-y-6">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<div>
			<h1 class="font-mono text-2xl font-bold text-gray-900">🤖 Robotics Producer</h1>
			<p class="mt-1 font-mono text-sm text-gray-600">
				Workspace: <span class="font-bold text-blue-600">{workspaceId}</span>
				{#if roomId}
					| Room: <span class="font-bold text-blue-600">{roomId}</span>
				{:else}
					| Control robot arm joints in real-time
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
		<div class="mb-2 font-bold">ROBOTICS PRODUCER DEBUG - WORKSPACE {debugInfo.workspaceId}{roomId ? ` - ROOM ${roomId}` : ''}</div>
		<div class="grid grid-cols-3 gap-4 md:grid-cols-5">
			<div>Attempts: {debugInfo.connectionAttempts}</div>
			<div>Commands: {debugInfo.commandsSent}</div>
			<div>Last: {debugInfo.lastCommandSent || 'None'}</div>
			<div>WS: {debugInfo.wsConnected ? 'ON' : 'OFF'}</div>
			<div>Room: {debugInfo.currentRoom || 'None'}</div>
		</div>
		{#if error}
			<div class="mt-2 text-red-400">Error: {error}</div>
		{/if}
	</div>

	{#if !connected}
		<!-- Connection Section -->
		<div class="grid grid-cols-1 gap-6 md:grid-cols-2">
			<!-- Join Existing Room -->
			<div class="rounded border p-6">
				<h3 class="mb-4 font-mono text-lg font-medium">Join Existing Room</h3>
				<div class="space-y-4">
					<div>
						<label for="roomId" class="mb-1 block font-mono text-sm font-medium text-gray-700">
							Room ID
						</label>
						<input
							id="roomId"
							type="text"
							bind:value={roomId}
							placeholder="Enter room ID"
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
					<button
						onclick={connectProducer}
						disabled={connecting || !roomId.trim() || !participantId.trim()}
						class={[
							'w-full rounded border px-4 py-2 font-mono',
							connecting || !roomId.trim() || !participantId.trim()
								? 'bg-gray-200 text-gray-500'
								: 'bg-blue-600 text-white hover:bg-blue-700'
						]}
					>
						{connecting ? 'Connecting...' : 'Join as Producer'}
					</button>
				</div>
			</div>

			<!-- Create New Room -->
			<div class="rounded border p-6">
				<h3 class="mb-4 font-mono text-lg font-medium">Create New Room</h3>
				<div class="space-y-4">
					<p class="font-mono text-sm text-gray-600">Create a new room in this workspace</p>
					<div>
						<label for="newParticipantId" class="mb-1 block font-mono text-sm font-medium text-gray-700">
							Participant ID (optional)
						</label>
						<input
							id="newParticipantId"
							type="text"
							bind:value={participantId}
							placeholder="Auto-generated if empty"
							class="w-full rounded border border-gray-300 px-3 py-2 font-mono focus:border-blue-500 focus:ring-blue-500"
						/>
					</div>
					<button
						onclick={createNewRoom}
						disabled={connecting}
						class={[
							'w-full rounded border px-4 py-2 font-mono',
							connecting
								? 'bg-gray-200 text-gray-500'
								: 'bg-green-600 text-white hover:bg-green-700'
						]}
					>
						{connecting ? 'Creating...' : 'Create New Room'}
					</button>
				</div>
			</div>
		</div>

		{#if error}
			<div class="rounded border border-red-200 bg-red-50 p-4">
				<p class="font-mono text-sm text-red-700">{error}</p>
			</div>
		{/if}
	{:else}
		<!-- Control Interface -->
		<div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
			<!-- Joint Controls -->
			<div class="space-y-6 lg:col-span-2">
				<!-- Connection Info -->
				<div class="rounded border p-4">
					<h2 class="mb-3 font-mono text-lg font-semibold">Session Info</h2>
					<div class="grid grid-cols-3 gap-4 font-mono text-sm">
						<div><span class="text-gray-500">Workspace:</span> {workspaceId}</div>
						<div><span class="text-gray-500">Room:</span> {roomId}</div>
						<div><span class="text-gray-500">ID:</span> {participantId}</div>
						<div><span class="text-gray-500">Role:</span> Producer</div>
					</div>
				</div>

				<!-- Robot Arm Visualization -->
				<div class="rounded border p-6">
					<h2 class="mb-4 font-mono text-lg font-semibold">Robot Arm Visualization</h2>
					<div class="aspect-video rounded border bg-gray-50 p-4">
						<div class="flex h-full items-center justify-center">
							<div class="text-center">
								<div class="mb-4 text-6xl">🦾</div>
								<p class="font-mono text-gray-600">3D Robot Visualization</p>
								<p class="font-mono text-xs text-gray-500">Real-time joint positions</p>
							</div>
						</div>
					</div>
				</div>

				<!-- Joint Controls -->
				<div class="rounded border p-6">
					<div class="mb-4 flex items-center justify-between">
						<h2 class="font-mono text-lg font-semibold">Joint Control</h2>
						<button
							onclick={resetJoints}
							class="rounded border bg-gray-100 px-3 py-1 font-mono text-sm hover:bg-gray-200"
						>
							🔄 Reset All
						</button>
					</div>

					<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
						{#each Object.entries(joints) as [jointName, value]}
							{@const limits = jointLimits[jointName as JointName]}
							<div class="rounded border bg-gray-50 p-4">
								<div class="mb-2 flex items-center justify-between">
									<div class="font-mono text-sm font-medium capitalize text-gray-700">
										{jointName.replace(/([A-Z])/g, ' $1').replace(/^./, (str) => str.toUpperCase())}
									</div>
									<span class="font-mono text-sm font-bold text-blue-600">
										{value.toFixed(1)}°
									</span>
								</div>
								<input
									type="range"
									min={limits.min}
									max={limits.max}
									step="0.1"
									bind:value={joints[jointName as JointName]}
									oninput={() => handleJointChange(jointName as JointName)}
									class="w-full"
								/>
								<div class="mt-1 flex justify-between font-mono text-xs text-gray-500">
									<span>{limits.min}°</span>
									<span>{limits.max}°</span>
								</div>
							</div>
						{/each}
					</div>
				</div>
			</div>

			<!-- Status & History -->
			<div class="space-y-6">
				<!-- Current Joint Values -->
				<div class="rounded border p-4">
					<h2 class="mb-3 font-mono text-lg font-semibold">Current Values</h2>
					<div class="space-y-2 font-mono text-sm">
						{#each Object.entries(joints) as [name, value]}
							<div class="flex justify-between">
								<span class="text-gray-600 capitalize">
									{name.replace(/([A-Z])/g, ' $1').replace(/^./, (str) => str.toUpperCase())}:
								</span>
								<span class="font-bold">{value.toFixed(1)}°</span>
							</div>
						{/each}
					</div>
				</div>

				<!-- Command History -->
				<div class="rounded border p-4">
					<h2 class="mb-3 font-mono text-lg font-semibold">Recent Commands</h2>
					<div class="max-h-64 space-y-2 overflow-y-auto">
						{#each commandHistory as command}
							<div class="rounded border-l-4 border-blue-200 bg-gray-50 p-2">
								<div class="flex items-center justify-between">
									<span class="font-mono text-xs text-gray-500">{command.timestamp}</span>
									<span class="font-mono text-xs font-medium text-blue-600">
										{command.command}
									</span>
								</div>
							</div>
						{:else}
							<p class="py-4 text-center font-mono text-sm text-gray-500">No commands sent yet</p>
						{/each}
					</div>
				</div>

				<!-- Session Control -->
				<div class="rounded border p-4">
					<h2 class="mb-3 font-mono text-lg font-semibold">Session Control</h2>
					<button
						onclick={exitSession}
						class="w-full rounded border bg-gray-100 px-4 py-2 font-mono hover:bg-gray-200"
					>
						🚪 Exit Session
					</button>
				</div>
			</div>
		</div>
	{/if}
</div>
