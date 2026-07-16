// SAGE API Connection - Auto-connect with machine UUID.
import { execSync } from 'child_process';
import { homedir, platform } from 'os';
import { v4 as uuidv4 } from 'uuid';
import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'fs';
import { join } from 'path';

const API_BASE = 'https://sage.api.marketingstudios.in';

export interface ConnectResult {
  ok: boolean;
  keyId?: string;
  apiKey?: string;
  error?: string;
}

export async function autoConnect(displayName: string): Promise<ConnectResult> {
  const machineId = getMachineId();
  
  try {
    const response = await fetch(`${API_BASE}/v1/machine-login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        display_name: displayName,
        fingerprint: machineId,
        hostname: displayName || machineId.slice(0, 12),
        installation_id: machineId,
        platform: platform(),
        client_version: '1.0.0',
        source: 'sage-js',
        expiry_days: 30
      })
    });
    
    if (!response.ok) {
      return { ok: false, error: `HTTP ${response.status}` };
    }

    const data = await response.json() as { key_id?: string; api_key?: string };
    
    // Store the key
    storeApiKey(data.api_key || data.key_id || machineId);
    
    return { ok: true, keyId: data.key_id, apiKey: data.api_key };
  } catch (e) {
    // Offline - queue for later, but still return success for setup
    storeApiKey(machineId); // Use machine ID as temporary key
    return { ok: false, error: 'Offline' };
  }
}

function getMachineId(): string {
  // 1. Check stored ID first
  const stored = getStoredId();
  if (stored) return stored;

  // 2. Try machine UUID
  try {
    if (platform() === 'win32') {
      const output = execSync('wmic csproduct get uuid', { encoding: 'utf8', timeout: 5000 });
      const uuid = output.split('\n')[1]?.trim();
      if (uuid && uuid !== 'FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF') {
        storeId(uuid);
        return uuid;
      }
    } else if (platform() === 'darwin') {
      const output = execSync('ioreg -rd1 -c IOPlatformExpertDevice | grep IOPlatformUUID', { encoding: 'utf8', timeout: 5000 });
      const match = output.match(/"([A-F0-9-]+)"/);
      if (match) {
        storeId(match[1]);
        return match[1];
      }
    } else {
      // Linux
      const output = execSync('cat /etc/machine-id 2>/dev/null || cat /var/lib/dbus/machine-id', { encoding: 'utf8', timeout: 5000 });
      if (output.trim()) {
        storeId(output.trim());
        return output.trim();
      }
    }
  } catch {
    // Machine UUID not available
  }

  // 3. Try git email
  try {
    const email = execSync('git config user.email', { encoding: 'utf8', timeout: 5000 }).trim();
    if (email) {
      const id = `git:${email}`;
      storeId(id);
      return id;
    }
  } catch {
    // Git not configured
  }

  // 4. Generate random UUID
  const newId = uuidv4();
  storeId(newId);
  return newId;
}

function getDataDir(): string {
  const home = homedir();
  if (platform() === 'win32') {
    return join(process.env.LOCALAPPDATA || join(home, 'AppData', 'Local'), 'SAGE');
  }
  return join(home, '.sage');
}

function getStoredId(): string | null {
  try {
    const idPath = join(getDataDir(), 'machine_id');
    if (existsSync(idPath)) {
      return readFileSync(idPath, 'utf-8').trim();
    }
  } catch {
    // Ignore
  }
  return null;
}

function storeId(id: string): void {
  try {
    const dir = getDataDir();
    if (!existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
    }
    writeFileSync(join(dir, 'machine_id'), id, 'utf-8');
  } catch {
    // Ignore
  }
}

function storeApiKey(key: string): void {
  try {
    const dir = getDataDir();
    if (!existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
    }
    writeFileSync(join(dir, 'api_key'), key, 'utf-8');
  } catch {
    // Ignore
  }
}

export function getApiKey(): string | null {
  try {
    const keyPath = join(getDataDir(), 'api_key');
    if (existsSync(keyPath)) {
      return readFileSync(keyPath, 'utf-8').trim();
    }
  } catch {
    // Ignore
  }
  return null;
}
