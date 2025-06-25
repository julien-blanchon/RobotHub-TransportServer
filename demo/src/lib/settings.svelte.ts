import { PUBLIC_TRANSPORT_SERVER_URL } from '$env/static/public';

interface Settings {
	transportServerUrl: string;
}

export const settings: Settings = $state({
	transportServerUrl: PUBLIC_TRANSPORT_SERVER_URL ?? 'http://localhost:8000'
});
