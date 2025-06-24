// place files you want to import through the `$lib` alias in this folder.

/**
 * Get the server URL based on environment variables and dev/prod mode
 * Priority: ENV variable > dev mode (localhost:8000) > prod mode (HF Space)
 */
export function getServerUrl(): string {
  // Check for environment variable first
  if (typeof window !== 'undefined') {
    // Client-side: check for runtime environment variable
    const envUrl = (window as any).__SERVER_URL__;
    if (envUrl) {
      return envUrl;
    }
  } else {
    // Server-side: check for build-time environment variable
    const envUrl = process.env.PUBLIC_SERVER_URL;
    if (envUrl) {
      return envUrl;
    }
  }

  // Fall back to dev/prod detection
  if (typeof window !== 'undefined') {
    // Client-side: check if we're in development
    const isDev = window.location.hostname === 'localhost' || 
                  window.location.hostname === '127.0.0.1' ||
                  window.location.hostname.startsWith('192.168.');
    
    return isDev ? 'http://localhost:8000' : 'https://blanchon-robottransportserver.hf.space/api';
  }
  
  // Server-side fallback
  return 'http://localhost:8000';
}
