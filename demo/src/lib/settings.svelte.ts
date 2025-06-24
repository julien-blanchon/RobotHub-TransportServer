import { getServerUrl } from './index.js';

interface Settings {
	transportServerUrl: string;
}

export const settings: Settings = $state({
	transportServerUrl: getServerUrl()
});
