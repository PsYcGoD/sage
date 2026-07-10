import { app, BrowserWindow, ipcMain, shell } from 'electron';
import { join } from 'path';
import { spawn, ChildProcess } from 'child_process';
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';

let mainWindow: BrowserWindow | null = null;
let pythonProcess: ChildProcess | null = null;

const PYTHON_WS_PORT = 19480;

// Window state persistence
interface WindowState {
  x?: number;
  y?: number;
  width: number;
  height: number;
  isMaximized: boolean;
  sidebarWidth: number;
}

function getStateFilePath(): string {
  const userDataPath = app.getPath('userData');
  return join(userDataPath, 'window-state.json');
}

function loadWindowState(): WindowState {
  const defaults: WindowState = { width: 1400, height: 900, isMaximized: false, sidebarWidth: 280 };
  try {
    const filePath = getStateFilePath();
    if (existsSync(filePath)) {
      const data = JSON.parse(readFileSync(filePath, 'utf-8'));
      return { ...defaults, ...data };
    }
  } catch {}
  return defaults;
}

function saveWindowState() {
  if (!mainWindow) return;
  const bounds = mainWindow.getBounds();
  const state: WindowState = {
    x: bounds.x,
    y: bounds.y,
    width: bounds.width,
    height: bounds.height,
    isMaximized: mainWindow.isMaximized(),
    sidebarWidth: 280,
  };
  try {
    const dir = app.getPath('userData');
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
    writeFileSync(getStateFilePath(), JSON.stringify(state, null, 2));
  } catch {}
}

function createWindow() {
  const state = loadWindowState();

  mainWindow = new BrowserWindow({
    width: state.width,
    height: state.height,
    x: state.x,
    y: state.y,
    minWidth: 800,
    minHeight: 600,
    frame: false,
    titleBarStyle: 'hidden',
    backgroundColor: '#1a1b26',
    icon: join(__dirname, '../src/assets/sage-icon.png'),
    webPreferences: {
      preload: join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (state.isMaximized) {
    mainWindow.maximize();
  }

  mainWindow.on('close', () => saveWindowState());

  if (process.env.VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL);
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  } else {
    mainWindow.loadFile(join(__dirname, '../dist/index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
}

function startPythonBackend() {
  pythonProcess = spawn('python', ['-m', 'sage.gui_server', '--port', String(PYTHON_WS_PORT)], {
    stdio: ['pipe', 'pipe', 'pipe'],
    env: { ...process.env },
  });

  pythonProcess.stdout?.on('data', (data: Buffer) => {
    console.log('[SAGE Backend]', data.toString().trim());
  });

  pythonProcess.stderr?.on('data', (data: Buffer) => {
    console.error('[SAGE Backend Error]', data.toString().trim());
  });

  pythonProcess.on('exit', (code) => {
    console.log(`[SAGE Backend] exited with code ${code}`);
    pythonProcess = null;
  });
}

function stopPythonBackend() {
  if (pythonProcess) {
    pythonProcess.kill('SIGTERM');
    pythonProcess = null;
  }
}

// IPC handlers for window controls
ipcMain.on('window:minimize', () => mainWindow?.minimize());
ipcMain.on('window:maximize', () => {
  if (mainWindow?.isMaximized()) {
    mainWindow.unmaximize();
  } else {
    mainWindow?.maximize();
  }
});
ipcMain.on('window:close', () => mainWindow?.close());
ipcMain.handle('window:isMaximized', () => mainWindow?.isMaximized() ?? false);

// Dialog handlers
ipcMain.handle('dialog:pickFolder', async () => {
  const { dialog } = await import('electron');
  const result = await dialog.showOpenDialog(mainWindow!, {
    properties: ['openDirectory'],
    title: 'Select Project Folder',
  });
  if (result.canceled || result.filePaths.length === 0) return null;
  return result.filePaths[0];
});

// Window state events
function setupWindowStateEvents() {
  if (!mainWindow) return;
  mainWindow.on('maximize', () => mainWindow?.webContents.send('window:maximized', true));
  mainWindow.on('unmaximize', () => mainWindow?.webContents.send('window:maximized', false));
}

app.whenReady().then(() => {
  startPythonBackend();
  createWindow();
  setupWindowStateEvents();
});

app.on('window-all-closed', () => {
  stopPythonBackend();
  app.quit();
});

app.on('before-quit', () => {
  stopPythonBackend();
});
