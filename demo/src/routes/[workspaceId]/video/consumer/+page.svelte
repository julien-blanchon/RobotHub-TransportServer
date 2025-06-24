<script lang="ts">
	import { onMount } from 'svelte';
	import { video } from '@robothub/transport-server-client';

	// Get data from load function
	let { data } = $props();
	let workspaceId = data.workspaceId;
	let roomIdFromUrl = data.roomId;

	// State
	let consumer: video.VideoConsumer;
	let connected = $state<boolean>(false);
	let connecting = $state<boolean>(false);
	let roomId = $state<string>(roomIdFromUrl || '');
	let participantId = $state<string>('');
	let error = $state<string>('');

	// Remote video stream
	let remoteVideoStream = $state<MediaStream | null>(null);
	let remoteVideoRef: HTMLVideoElement;

	// Stream status
	let streamActive = $state<boolean>(false);
	let producerConnected = $state<boolean>(false);

	// Debug info
	let debugInfo = $state<{
		connectionAttempts: number;
		framesReceived: number;
		bytesReceived: number;
		currentBitrate: number;
		lastFrameReceived: string;
		wsConnected: boolean;
		currentRoom: string;
		workspaceId: string;
	}>({
		connectionAttempts: 0,
		framesReceived: 0,
		bytesReceived: 0,
		currentBitrate: 0,
		lastFrameReceived: '',
		wsConnected: false,
		currentRoom: '',
		workspaceId: workspaceId
	});

	// Stream quality info
	let streamQuality = $state<{
		resolution: { width: number; height: number } | null;
		framerate: number;
		codec: string;
	}>({
		resolution: null,
		framerate: 0,
		codec: ''
	});

	// Statistics tracking
	let statsInterval: ReturnType<typeof setInterval> | null = null;
	let lastStats: any = null;
	let lastStatsTime = 0;

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

			consumer = new video.VideoConsumer('http://localhost:8000');

			// Set up event handlers
			consumer.onConnected(() => {
				connected = true;
				connecting = false;
				debugInfo.wsConnected = true;
				debugInfo.currentRoom = roomId;
				updateUrlWithRoom(roomId);
				startStatTracking();
			});

			consumer.onDisconnected(() => {
				connected = false;
				debugInfo.wsConnected = false;
				streamActive = false;
				producerConnected = false;
				stopStatTracking();
			});

			consumer.onError((errorMsg) => {
				error = errorMsg;
			});

			// Video stream callback - use the correct event-based API
			consumer.on('remoteStream', (stream: MediaStream) => {
				console.info('📺 Remote stream received:', stream);
				remoteVideoStream = stream;
				streamActive = true;
				producerConnected = true;

				// Update stream quality info
				const videoTrack = stream.getVideoTracks()[0];
				if (videoTrack) {
					const settings = videoTrack.getSettings();
					streamQuality.resolution = {
						width: settings.width || 0,
						height: settings.height || 0
					};
					streamQuality.framerate = settings.frameRate || 0;
					console.info('📊 Stream quality:', streamQuality);
				}
			});

			// Producer status updates - use stream event callbacks
			consumer.onStreamStarted((config, participantId) => {
				producerConnected = true;
				console.info(`Stream started by producer ${participantId}`);
			});

			consumer.onStreamStopped((participantId, reason) => {
				producerConnected = false;
				streamActive = false;
				remoteVideoStream = null;
				if (remoteVideoRef) {
					remoteVideoRef.srcObject = null;
				}
				console.info(`Stream stopped by producer ${participantId}: ${reason}`);
			});

			const success = await consumer.connect(workspaceId, roomId, participantId);
			if (!success) {
				error = 'Failed to connect. Room might not exist.';
				connecting = false;
			} else {
				// Start receiving after successful connection
				await consumer.startReceiving();
			}
		} catch (err) {
			error = `Connection failed: ${err}`;
			connecting = false;
		}
	}

	function startStatTracking() {
		stopStatTracking();
		lastStats = null;
		lastStatsTime = 0;
		
		statsInterval = setInterval(async () => {
			if (consumer && connected && remoteVideoRef) {
				try {
					const stats = await consumer.getVideoStats();
					const currentTime = Date.now();
					
					if (stats) {
						// Calculate rates if we have previous stats
						if (lastStats && lastStatsTime > 0) {
							const timeDiffSec = (currentTime - lastStatsTime) / 1000;
							
							// Calculate bitrate from bytes difference
							const bytesDiff = (stats.videoBitsPerSecond || 0) - (lastStats.videoBitsPerSecond || 0);
							const bitsPerSec = timeDiffSec > 0 ? (bytesDiff * 8) / timeDiffSec : 0;
							
							// Calculate packet rate
							const packetsDiff = (stats.totalPackets || 0) - (lastStats.totalPackets || 0);
							
							debugInfo.framesReceived = stats.totalPackets || 0;
							debugInfo.bytesReceived = stats.videoBitsPerSecond || 0; // Total bytes received
							debugInfo.currentBitrate = Math.round(bitsPerSec);
							debugInfo.lastFrameReceived = new Date().toLocaleTimeString();
						} else {
							// First measurement
							debugInfo.framesReceived = stats.totalPackets || 0;
							debugInfo.bytesReceived = stats.videoBitsPerSecond || 0;
							debugInfo.currentBitrate = 0; // Can't calculate rate on first measurement
							debugInfo.lastFrameReceived = new Date().toLocaleTimeString();
						}
						
						// Update stream quality from stats
						if (stats.frameWidth && stats.frameHeight) {
							streamQuality.resolution = {
								width: stats.frameWidth,
								height: stats.frameHeight
							};
							streamQuality.framerate = stats.framesPerSecond || 0;
						}
						
						// Store for next calculation
						lastStats = { ...stats };
						lastStatsTime = currentTime;
					}
				} catch (err) {
					console.error('Failed to get consumer stats:', err);
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
		if (consumer && connected) {
			await consumer.disconnect();
		}
		connected = false;
		debugInfo.wsConnected = false;
		debugInfo.currentRoom = '';
		streamActive = false;
		producerConnected = false;
		remoteVideoStream = null;
		stopStatTracking();

		if (remoteVideoRef) {
			remoteVideoRef.srcObject = null;
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

	// Reactive effect to attach stream to video element when both are available
	$effect(() => {
		if (remoteVideoStream && remoteVideoRef) {
			console.info('🔗 Attaching remote stream to video element');
			remoteVideoRef.srcObject = remoteVideoStream;
			
			// Ensure video starts playing
			remoteVideoRef.play().catch((err) => {
				console.warn('Auto-play failed:', err);
				// Try to play with user gesture required
				remoteVideoRef.muted = true;
				remoteVideoRef.play().catch((err2) => {
					console.error('Failed to play video even when muted:', err2);
				});
			});
		}
	});

	onMount(() => {
		participantId = `consumer_${Date.now()}`;

		return () => {
			exitSession();
		};
	});
</script>

<svelte:head>
	<title>Video Consumer{roomId ? ` - Room ${roomId}` : ''} - Workspace {workspaceId} - LeRobot Arena</title>
</svelte:head>

<div class="mx-auto max-w-6xl space-y-6">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<div>
			<h1 class="font-mono text-2xl font-bold text-gray-900">📺 Video Consumer</h1>
			<p class="mt-1 font-mono text-sm text-gray-600">
				Workspace: <span class="font-bold text-blue-600">{workspaceId}</span>
				{#if roomId}
					| Room: <span class="font-bold text-blue-600">{roomId}</span>
				{:else}
					| Watch video streams via WebRTC
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
		<div class="mb-2 font-bold">VIDEO CONSUMER DEBUG - WORKSPACE {debugInfo.workspaceId}{roomId ? ` - ROOM ${roomId}` : ''}</div>
		<div class="grid grid-cols-3 gap-4 md:grid-cols-5">
			<div>Attempts: {debugInfo.connectionAttempts}</div>
			<div>Frames: {debugInfo.framesReceived}</div>
			<div>Bytes: {(debugInfo.bytesReceived / 1024).toFixed(1)}KB</div>
			<div>WS: {debugInfo.wsConnected ? 'ON' : 'OFF'}</div>
			<div>Room: {debugInfo.currentRoom || 'None'}</div>
		</div>
		<div class="mt-2">
			Stream: {streamActive ? 'ACTIVE' : 'INACTIVE'} | Producer: {producerConnected ? 'CONNECTED' : 'DISCONNECTED'}
		</div>
		<div class="mt-2">
			Bitrate: {debugInfo.currentBitrate}bps | Last Frame: {debugInfo.lastFrameReceived || 'Never'}
		</div>
		{#if error}
			<div class="mt-2 text-red-400">Error: {error}</div>
		{/if}
	</div>

	{#if !connected}
		<!-- Connection Section -->
		<div class="rounded border p-6">
			<h2 class="mb-4 font-mono text-lg font-semibold">Connect to Video Room</h2>

			<div class="grid grid-cols-1 gap-6 md:grid-cols-2">
				<div>
					<label for="roomId" class="mb-1 block font-mono text-sm font-medium text-gray-700">
						Room ID
					</label>
					<input
						id="roomId"
						type="text"
						bind:value={roomId}
						placeholder="Enter room ID to watch"
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
			</div>

			<div class="mt-4">
				<button
					onclick={connectConsumer}
					disabled={connecting || !roomId.trim() || !participantId.trim()}
					class={[
						'rounded border px-4 py-2 font-mono',
						connecting || !roomId.trim() || !participantId.trim()
							? 'bg-gray-200 text-gray-500'
							: 'bg-purple-600 text-white hover:bg-purple-700'
					]}
				>
					{connecting ? 'Connecting...' : 'Join as Viewer'}
				</button>
			</div>

			{#if error}
				<div class="mt-4 rounded border border-red-200 bg-red-50 p-4">
					<p class="font-mono text-sm text-red-700">{error}</p>
				</div>
			{/if}
		</div>
	{:else}
		<!-- Viewing Interface -->
		<div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
			<!-- Video Display -->
			<div class="lg:col-span-2">
				<div class="rounded border p-4">
					<div class="mb-3 flex items-center justify-between">
						<h2 class="font-mono text-lg font-semibold">📺 Live Stream</h2>
						<div class="flex items-center space-x-2">
							{#if streamActive}
								<div class="h-2 w-2 rounded-full bg-red-500"></div>
								<span class="font-mono text-sm text-red-600">LIVE</span>
							{:else if producerConnected}
								<div class="h-2 w-2 rounded-full bg-yellow-500"></div>
								<span class="font-mono text-sm text-yellow-600">WAITING</span>
							{:else}
								<div class="h-2 w-2 rounded-full bg-gray-500"></div>
								<span class="font-mono text-sm text-gray-600">NO STREAM</span>
							{/if}
						</div>
					</div>

					<div class="aspect-video rounded border bg-gray-100">
						{#if streamActive && remoteVideoStream}
							<video
								bind:this={remoteVideoRef}
								autoplay
								muted
								playsinline
								class="h-full w-full rounded object-cover"
							></video>
						{:else if producerConnected}
							<div class="flex h-full items-center justify-center">
								<div class="text-center">
									<div class="mb-4 text-4xl text-yellow-500">⏳</div>
									<p class="font-mono text-gray-600">Waiting for video stream...</p>
									<p class="font-mono text-sm text-gray-500">Producer is connected but not streaming yet</p>
								</div>
							</div>
						{:else}
							<div class="flex h-full items-center justify-center">
								<div class="text-center">
									<div class="mb-4 text-4xl text-gray-400">📺</div>
									<p class="font-mono text-gray-600">No video stream available</p>
									<p class="font-mono text-sm text-gray-500">Waiting for producer to join and start streaming</p>
								</div>
							</div>
						{/if}
					</div>

					<!-- Stream Info -->
					{#if streamActive && streamQuality.resolution}
						<div class="mt-4 grid grid-cols-3 gap-4 font-mono text-sm text-gray-600">
							<div>
								Resolution: {streamQuality.resolution.width}x{streamQuality.resolution.height}
							</div>
							<div>Framerate: {streamQuality.framerate} FPS</div>
							<div>Codec: {streamQuality.codec || 'Unknown'}</div>
						</div>
					{/if}
				</div>
			</div>

			<!-- Controls & Stats -->
			<div class="space-y-6">
				<!-- Session Info -->
				<div class="rounded border p-4">
					<h2 class="mb-3 font-mono text-lg font-semibold">Session Info</h2>
					<div class="space-y-2 font-mono text-sm">
						<div><span class="text-gray-500">Workspace:</span> {workspaceId}</div>
						<div><span class="text-gray-500">Room:</span> {roomId}</div>
						<div><span class="text-gray-500">ID:</span> {participantId}</div>
						<div><span class="text-gray-500">Role:</span> Consumer</div>
						<div>
							<span class="text-gray-500">Status:</span>
							{#if streamActive}
								<span class="text-green-600">Streaming</span>
							{:else if producerConnected}
								<span class="text-yellow-600">Waiting</span>
							{:else}
								<span class="text-gray-600">No Producer</span>
							{/if}
						</div>
					</div>
				</div>

				<!-- Stream Statistics -->
				{#if streamActive}
					<div class="rounded border p-4">
						<h2 class="mb-3 font-mono text-lg font-semibold">📊 Stream Stats</h2>
						<div class="space-y-2 font-mono text-sm">
							<div class="flex justify-between">
								<span class="text-gray-600">Frames Received:</span>
								<span class="font-bold">{debugInfo.framesReceived}</span>
							</div>
							<div class="flex justify-between">
								<span class="text-gray-600">Data Received:</span>
								<span class="font-bold">{(debugInfo.bytesReceived / 1024).toFixed(1)} KB</span>
							</div>
							<div class="flex justify-between">
								<span class="text-gray-600">Bitrate:</span>
								<span class="font-bold">{debugInfo.currentBitrate} bps</span>
							</div>
							{#if streamQuality.resolution}
								<div class="flex justify-between">
									<span class="text-gray-600">Resolution:</span>
									<span class="font-bold">{streamQuality.resolution.width}x{streamQuality.resolution.height}</span>
								</div>
								<div class="flex justify-between">
									<span class="text-gray-600">FPS:</span>
									<span class="font-bold">{streamQuality.framerate}</span>
								</div>
							{/if}
						</div>
					</div>
				{/if}

				<!-- Controls -->
				<div class="rounded border p-4">
					<h2 class="mb-3 font-mono text-lg font-semibold">Controls</h2>
					<div class="space-y-3">
						{#if streamActive && remoteVideoRef}
							<button
								onclick={() => {
									if (remoteVideoRef.requestFullscreen) {
										remoteVideoRef.requestFullscreen();
									}
								}}
								class="w-full rounded border bg-blue-100 px-4 py-2 font-mono text-blue-700 hover:bg-blue-200"
							>
								🔍 Fullscreen
							</button>
						{/if}
						<button
							onclick={() => {
								const url = `${window.location.origin}/${workspaceId}/video/producer?room=${roomId}`;
								navigator.clipboard.writeText(url);
								alert('Producer link copied to clipboard!');
							}}
							class="w-full rounded border bg-purple-100 px-4 py-2 font-mono text-purple-700 hover:bg-purple-200"
						>
							📋 Copy Producer Link
						</button>
						<button
							onclick={exitSession}
							class="w-full rounded border bg-gray-100 px-4 py-2 font-mono hover:bg-gray-200"
						>
							🚪 Leave Room
						</button>
					</div>
				</div>
			</div>
		</div>
	{/if}
</div> 