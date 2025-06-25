<script lang="ts">
	import { onMount } from 'svelte';
	import { video } from '@robothub/transport-server-client';
	import { settings } from '$lib/settings.svelte.js';
	

	// Get data from load function
	let { data } = $props();
	let workspaceId = data.workspaceId;
	let roomIdFromUrl = data.roomId;

	// State
	let producer: video.VideoProducer;
	let connected = $state<boolean>(false);
	let connecting = $state<boolean>(false);
	let roomId = $state<string>(roomIdFromUrl || '');
	let participantId = $state<string>('');
	let error = $state<string>('');

	// Video configuration
	let videoConfig = $state<{
		width: number;
		height: number;
		framerate: number;
		deviceId: string;
	}>({
		width: 640,
		height: 480,
		framerate: 30,
		deviceId: ''
	});

	// Media stream
	let localVideoStream = $state<MediaStream | null>(null);
	let localVideoRef: HTMLVideoElement | null = $state(null);

	// Available video devices
	let videoDevices = $state<MediaDeviceInfo[]>([]);

	// Debug info
	let debugInfo = $state<{
		connectionAttempts: number;
		lastFrameSent: string;
		framesSent: number;
		bytesTransferred: number;
		activeBitrate: number;
		wsConnected: boolean;
		currentRoom: string;
		workspaceId: string;
	}>({
		connectionAttempts: 0,
		lastFrameSent: '',
		framesSent: 0,
		bytesTransferred: 0,
		activeBitrate: 0,
		wsConnected: false,
		currentRoom: '',
		workspaceId: workspaceId
	});

	// Video quality presets
	const qualityPresets = [
		{ name: 'Low (320x240)', width: 320, height: 240, framerate: 15 },
		{ name: 'Medium (640x480)', width: 640, height: 480, framerate: 30 },
		{ name: 'High (1280x720)', width: 1280, height: 720, framerate: 30 },
		{ name: 'Ultra (1920x1080)', width: 1920, height: 1080, framerate: 60 }
	];

	// Statistics tracking
	let statsInterval: ReturnType<typeof setInterval> | null = null;

	function updateUrlWithRoom(roomId: string) {
		const url = new URL(window.location.href);
		url.searchParams.set('room', roomId);
		window.history.replaceState({}, '', url.toString());
	}

	async function loadVideoDevices() {
		try {
			const devices = await navigator.mediaDevices.enumerateDevices();
			videoDevices = devices.filter((device) => device.kind === 'videoinput');
			if (videoDevices.length > 0 && !videoConfig.deviceId) {
				videoConfig.deviceId = videoDevices[0].deviceId;
			}
		} catch (err) {
			console.error('Failed to enumerate video devices:', err);
		}
	}

	async function startLocalVideo() {
		try {
			error = '';

			// Stop existing stream if any
			if (localVideoStream) {
				localVideoStream.getTracks().forEach((track) => track.stop());
			}

			// Get new stream with current config
			const constraints: MediaStreamConstraints = {
				video: {
					width: { ideal: videoConfig.width },
					height: { ideal: videoConfig.height },
					frameRate: { ideal: videoConfig.framerate },
					deviceId: videoConfig.deviceId ? { exact: videoConfig.deviceId } : undefined
				},
				audio: false
			};

			localVideoStream = await navigator.mediaDevices.getUserMedia(constraints);

			// Attach to video element
			if (localVideoRef) {
				localVideoRef.srcObject = localVideoStream;
			}
		} catch (err) {
			error = `Failed to access camera: ${err}`;
			console.error('Failed to start local video:', err);
		}
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

			producer = new video.VideoProducer("https://blanchon-robothub-transportserver.hf.space/api");

			producer.onConnected(() => {
				connected = true;
				connecting = false;
				debugInfo.wsConnected = true;
				debugInfo.currentRoom = roomId;
				updateUrlWithRoom(roomId);
			});

			producer.onDisconnected(() => {
				connected = false;
				debugInfo.wsConnected = false;
			});

			producer.onError((errorMsg) => {
				error = errorMsg;
			});

			const success = await producer.connect(workspaceId, roomId, participantId);
			if (!success) {
				error = 'Failed to connect. Room might not exist or already have a producer.';
				connecting = false;
			} else {
				// Start streaming after successful connection
				if (localVideoStream) {
					try {
						await producer.startCamera({
							video: {
								width: { ideal: videoConfig.width },
								height: { ideal: videoConfig.height },
								frameRate: { ideal: videoConfig.framerate },
								deviceId: videoConfig.deviceId ? { exact: videoConfig.deviceId } : undefined
							},
							audio: false
						});
						startStatTracking();
					} catch (err) {
						error = `Failed to start streaming: ${err}`;
					}
				}
			}
		} catch (err) {
			error = `Connection failed: ${err}`;
			connecting = false;
		}
	}

	async function createNewRoom() {
		if (!participantId.trim()) {
			participantId = `producer_${Date.now()}`;
		}

		if (!localVideoStream) {
			error = 'Please start camera preview first';
			return;
		}

		debugInfo.connectionAttempts++;

		try {
			connecting = true;
			error = '';

			producer = new video.VideoProducer(settings.transportServerUrl);

			producer.onConnected(() => {
				connected = true;
				connecting = false;
				debugInfo.wsConnected = true;
			});

			producer.onDisconnected(() => {
				connected = false;
				debugInfo.wsConnected = false;
				stopStatTracking();
			});

			producer.onError((errorMsg) => {
				error = errorMsg;
			});

			const roomData = await producer.createRoom(workspaceId);
			const success = await producer.connect(roomData.workspaceId, roomData.roomId, participantId);

			if (success) {
				roomId = roomData.roomId;
				connected = true;
				connecting = false;
				debugInfo.wsConnected = true;
				debugInfo.currentRoom = roomId;
				updateUrlWithRoom(roomId);
				
				// Start streaming after successful connection
				if (localVideoStream) {
					try {
						await producer.startCamera({
							video: {
								width: { ideal: videoConfig.width },
								height: { ideal: videoConfig.height },
								frameRate: { ideal: videoConfig.framerate },
								deviceId: videoConfig.deviceId ? { exact: videoConfig.deviceId } : undefined
							},
							audio: false
						});
						startStatTracking();
					} catch (err) {
						error = `Failed to start streaming: ${err}`;
					}
				}
			}
		} catch (err) {
			error = `Failed to create room: ${err}`;
			connecting = false;
		}
	}

	async function applyQualityPreset(preset: { name: string; width: number; height: number; framerate: number }) {
		videoConfig.width = preset.width;
		videoConfig.height = preset.height;
		videoConfig.framerate = preset.framerate;

		// Restart video if already streaming
		if (localVideoStream) {
			await startLocalVideo();
		}
	}

	function startStatTracking() {
		stopStatTracking();
		statsInterval = setInterval(async () => {
			if (producer && connected) {
				try {
					const stats = await producer.getStats();
					if (stats) {
						debugInfo.framesSent = stats.totalPackets || 0;
						debugInfo.bytesTransferred = (stats.videoBitsPerSecond * 2) / 8 || 0; // Rough estimate
						debugInfo.activeBitrate = stats.videoBitsPerSecond || 0;
						debugInfo.lastFrameSent = new Date().toLocaleTimeString();
					}
				} catch (err) {
					console.error('Failed to get producer stats:', err);
				}
			}
		}, 2000);
	}

	function stopStatTracking() {
		if (statsInterval) {
			clearInterval(statsInterval);
			statsInterval = null;
		}
	}

	async function exitSession() {
		if (producer && connected) {
			await producer.disconnect();
		}
		connected = false;
		debugInfo.wsConnected = false;
		debugInfo.currentRoom = '';
		stopStatTracking();

		// Stop local video stream
		if (localVideoStream) {
			localVideoStream.getTracks().forEach((track) => track.stop());
			localVideoStream = null;
		}
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

	// Reactive effect to attach local stream to video element when both are available
	$effect(() => {
		if (localVideoStream && localVideoRef) {
			console.info('🔗 Attaching local stream to video element');
			localVideoRef.srcObject = localVideoStream;
		}
	});

	onMount(() => {
		participantId = `producer_${Date.now()}`;
		loadVideoDevices();

		return () => {
			exitSession();
		};
	});
</script>

<svelte:head>
	<title>Video Producer{roomId ? ` - Room ${roomId}` : ''} - Workspace {workspaceId} - RobotHub TransportServer</title>
</svelte:head>

<div class="mx-auto max-w-6xl space-y-6">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<div>
			<h1 class="font-mono text-2xl font-bold text-gray-900">📹 Video Producer</h1>
			<p class="mt-1 font-mono text-sm text-gray-600">
				Workspace: <span class="font-bold text-blue-600">{workspaceId}</span>
				{#if roomId}
					| Room: <span class="font-bold text-blue-600">{roomId}</span>
				{:else}
					| Stream video via WebRTC
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
				href="/{workspaceId}/video"
				class="rounded border bg-gray-100 px-3 py-2 font-mono text-sm hover:bg-gray-200"
			>
				← Back to Video
			</a>
		</div>
	</div>

	<!-- Debug Info -->
	<div class="rounded border bg-gray-900 p-4 font-mono text-sm text-green-400">
		<div class="mb-2 font-bold">VIDEO PRODUCER DEBUG - WORKSPACE {debugInfo.workspaceId}{roomId ? ` - ROOM ${roomId}` : ''}</div>
		<div class="grid grid-cols-3 gap-4 md:grid-cols-5">
			<div>Attempts: {debugInfo.connectionAttempts}</div>
			<div>Frames: {debugInfo.framesSent}</div>
			<div>Bytes: {(debugInfo.bytesTransferred / 1024).toFixed(1)}KB</div>
			<div>WS: {debugInfo.wsConnected ? 'ON' : 'OFF'}</div>
			<div>Room: {debugInfo.currentRoom || 'None'}</div>
		</div>
		<div class="mt-2">
			Bitrate: {debugInfo.activeBitrate}bps | Last Frame: {debugInfo.lastFrameSent || 'Never'}
		</div>
		{#if error}
			<div class="mt-2 text-red-400">Error: {error}</div>
		{/if}
	</div>

	<!-- Video Configuration -->
	<div class="rounded border p-6">
		<h2 class="mb-4 font-mono text-lg font-semibold">📷 Camera Setup</h2>

		<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
			<!-- Camera Configuration -->
			<div class="space-y-4">
				<!-- Device Selection -->
				<div>
					<label for="deviceSelect" class="mb-1 block font-mono text-sm font-medium text-gray-700">
						Camera Device
					</label>
					<select
						id="deviceSelect"
						bind:value={videoConfig.deviceId}
						class="w-full rounded border border-gray-300 px-3 py-2 font-mono focus:border-purple-500 focus:ring-purple-500"
					>
						{#each videoDevices as device}
							<option value={device.deviceId}>
								{device.label || `Camera ${device.deviceId.slice(0, 8)}...`}
							</option>
						{/each}
					</select>
				</div>

				<!-- Quality Presets -->
				<div>
					<label class="mb-2 block font-mono text-sm font-medium text-gray-700">
						Quality Presets
					</label>
					<div class="grid grid-cols-1 gap-2">
						{#each qualityPresets as preset}
							<button
								onclick={() => applyQualityPreset(preset)}
								class="rounded border bg-gray-50 px-3 py-2 font-mono text-sm hover:bg-gray-100"
							>
								{preset.name}
							</button>
						{/each}
					</div>
				</div>

				<!-- Manual Configuration -->
				<div class="grid grid-cols-2 gap-4">
					<div>
						<label for="width" class="mb-1 block font-mono text-sm font-medium text-gray-700">
							Width
						</label>
						<input
							id="width"
							type="number"
							bind:value={videoConfig.width}
							min="320"
							max="1920"
							step="10"
							class="w-full rounded border border-gray-300 px-3 py-2 font-mono focus:border-purple-500 focus:ring-purple-500"
						/>
					</div>
					<div>
						<label for="height" class="mb-1 block font-mono text-sm font-medium text-gray-700">
							Height
						</label>
						<input
							id="height"
							type="number"
							bind:value={videoConfig.height}
							min="240"
							max="1080"
							step="10"
							class="w-full rounded border border-gray-300 px-3 py-2 font-mono focus:border-purple-500 focus:ring-purple-500"
						/>
					</div>
					<div class="col-span-2">
						<label for="framerate" class="mb-1 block font-mono text-sm font-medium text-gray-700">
							Framerate (FPS)
						</label>
						<input
							id="framerate"
							type="number"
							bind:value={videoConfig.framerate}
							min="5"
							max="60"
							step="5"
							class="w-full rounded border border-gray-300 px-3 py-2 font-mono focus:border-purple-500 focus:ring-purple-500"
						/>
					</div>
				</div>

				<button
					onclick={startLocalVideo}
					class="w-full rounded border bg-purple-600 px-4 py-2 font-mono text-white hover:bg-purple-700"
				>
					🎬 Start Camera Preview
				</button>
			</div>

			<!-- Video Preview -->
			<div class="space-y-4">
				<div class="aspect-video rounded border bg-gray-100">
					{#if localVideoStream}
						<video
							bind:this={localVideoRef}
							autoplay
							muted
							playsinline
							class="h-full w-full rounded object-cover"
						></video>
					{:else}
						<div class="flex h-full items-center justify-center">
							<div class="text-center">
								<div class="mb-2 text-4xl text-gray-400">📷</div>
								<p class="font-mono text-gray-500">Start camera preview to see video</p>
							</div>
						</div>
					{/if}
				</div>

				<div class="font-mono text-sm text-gray-600">
					<div>Resolution: {videoConfig.width}x{videoConfig.height}</div>
					<div>Framerate: {videoConfig.framerate} FPS</div>
					<div>
						Device: {videoDevices.find((d) => d.deviceId === videoConfig.deviceId)?.label ||
							'Default'}
					</div>
				</div>
			</div>
		</div>
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
							class="w-full rounded border border-gray-300 px-3 py-2 font-mono focus:border-purple-500 focus:ring-purple-500"
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
							class="w-full rounded border border-gray-300 px-3 py-2 font-mono focus:border-purple-500 focus:ring-purple-500"
						/>
					</div>
					<button
						onclick={connectProducer}
						disabled={connecting || !roomId.trim() || !participantId.trim() || !localVideoStream}
						class={[
							'w-full rounded border px-4 py-2 font-mono',
							connecting || !roomId.trim() || !participantId.trim() || !localVideoStream
								? 'bg-gray-200 text-gray-500'
								: 'bg-purple-600 text-white hover:bg-purple-700'
						]}
					>
						{connecting ? 'Connecting...' : 'Start Streaming'}
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
							class="w-full rounded border border-gray-300 px-3 py-2 font-mono focus:border-purple-500 focus:ring-purple-500"
						/>
					</div>
					<button
						onclick={createNewRoom}
						disabled={connecting || !localVideoStream}
						class={[
							'w-full rounded border px-4 py-2 font-mono',
							connecting || !localVideoStream
								? 'bg-gray-200 text-gray-500'
								: 'bg-green-600 text-white hover:bg-green-700'
						]}
					>
						{connecting ? 'Creating...' : 'Create & Stream'}
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
		<!-- Streaming Interface -->
		<div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
			<!-- Stream Preview -->
			<div class="lg:col-span-2">
				<div class="rounded border p-4">
					<h2 class="mb-3 font-mono text-lg font-semibold">🔴 Live Stream</h2>

					<div class="aspect-video rounded border bg-gray-100">
						{#if localVideoStream}
							<video
								bind:this={localVideoRef}
								autoplay
								muted
								playsinline
								class="h-full w-full rounded object-cover"
							></video>
						{/if}
					</div>

					<div class="mt-4 grid grid-cols-3 gap-4 font-mono text-sm">
						<div><span class="text-gray-500">Workspace:</span> {workspaceId}</div>
						<div><span class="text-gray-500">Room:</span> {roomId}</div>
						<div><span class="text-gray-500">ID:</span> {participantId}</div>
					</div>
				</div>
			</div>

			<!-- Stream Stats & Controls -->
			<div class="space-y-6">
				<!-- Stream Statistics -->
				<div class="rounded border p-4">
					<h2 class="mb-3 font-mono text-lg font-semibold">📊 Stream Stats</h2>
					<div class="space-y-2 font-mono text-sm">
						<div class="flex justify-between">
							<span class="text-gray-600">Frames Sent:</span>
							<span class="font-bold">{debugInfo.framesSent}</span>
						</div>
						<div class="flex justify-between">
							<span class="text-gray-600">Data Sent:</span>
							<span class="font-bold">{(debugInfo.bytesTransferred / 1024).toFixed(1)} KB</span>
						</div>
						<div class="flex justify-between">
							<span class="text-gray-600">Bitrate:</span>
							<span class="font-bold">{debugInfo.activeBitrate} bps</span>
						</div>
						<div class="flex justify-between">
							<span class="text-gray-600">Resolution:</span>
							<span class="font-bold">{videoConfig.width}x{videoConfig.height}</span>
						</div>
						<div class="flex justify-between">
							<span class="text-gray-600">FPS:</span>
							<span class="font-bold">{videoConfig.framerate}</span>
						</div>
					</div>
				</div>

				<!-- Session Control -->
				<div class="rounded border p-4">
					<h2 class="mb-3 font-mono text-lg font-semibold">Session Control</h2>
					<div class="space-y-3">
						<button
							onclick={() => {
								const url = `${window.location.origin}/${workspaceId}/video/consumer?room=${roomId}`;
								navigator.clipboard.writeText(url);
								alert('Viewer link copied to clipboard!');
							}}
							class="w-full rounded border bg-blue-100 px-4 py-2 font-mono text-blue-700 hover:bg-blue-200"
						>
							📋 Copy Viewer Link
						</button>
						<button
							onclick={exitSession}
							class="w-full rounded border bg-gray-100 px-4 py-2 font-mono hover:bg-gray-200"
						>
							🚪 Stop Streaming
						</button>
					</div>
				</div>
			</div>
		</div>
	{/if}
</div> 