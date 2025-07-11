import { env } from '$env/dynamic/public';

interface Settings {
	transportServerUrl: string;
}

export const settings: Settings = $state({
	transportServerUrl: env.PUBLIC_TRANSPORT_SERVER_URL ?? 'https://blanchon-robothub-transportserver.hf.space/api'
});
