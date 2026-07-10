import { useState, useEffect, useCallback } from 'react';
import { useWebSocket } from './useWebSocket';

export interface Settings {
  display_name: string;
  username: string;
  permission_mode: 'ask' | 'approve' | 'full';
  ml_enabled: boolean;
  compression_enabled: boolean;
  agents_enabled: boolean;
  telemetry_enabled: boolean;
  theme: 'dark' | 'light';
}

const DEFAULT_SETTINGS: Settings = {
  display_name: '',
  username: '',
  permission_mode: 'ask',
  ml_enabled: true,
  compression_enabled: true,
  agents_enabled: true,
  telemetry_enabled: true,
  theme: 'dark',
};

export function useSettings() {
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const { connected, send, on } = useWebSocket();

  useEffect(() => {
    if (!connected) return;

    const unsub = on('settings.get.response', (msg) => {
      setSettings({ ...DEFAULT_SETTINGS, ...msg.payload.settings });
    });

    send('settings.get', {});
    return unsub;
  }, [connected, send, on]);

  const updateSettings = useCallback((patch: Partial<Settings>) => {
    const updated = { ...settings, ...patch };
    setSettings(updated);
    send('settings.set', patch);
  }, [settings, send]);

  return { settings, updateSettings };
}
