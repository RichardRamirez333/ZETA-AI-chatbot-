const { app, BrowserWindow, Menu } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

let mainWindow = null;
let serverProcess = null;
const PORT = 3000;
const SERVER_URL = `http://127.0.0.1:${PORT}`;

function getResourcePath(relativePath) {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, relativePath);
  }
  return path.join(__dirname, '..', relativePath);
}

function startServer() {
  return new Promise((resolve, reject) => {
    let exePath;
    if (app.isPackaged) {
      exePath = path.join(process.resourcesPath, 'backend', 'ZETA.exe');
    } else {
      exePath = path.join(__dirname, '..', 'dist', 'ZETA.exe');
    }

    if (!fs.existsSync(exePath)) {
      console.log('ZETA.exe not found. Starting Python directly...');
      const pythonPath = path.join(__dirname, '..', 'win_launcher.py');
      serverProcess = spawn('python', [pythonPath], {
        cwd: path.join(__dirname, '..'),
        stdio: ['pipe', 'pipe', 'pipe'],
      });
    } else {
      serverProcess = spawn(exePath, [], {
        cwd: path.join(__dirname, '..'),
        stdio: ['pipe', 'pipe', 'pipe'],
      });
    }

    serverProcess.stdout.on('data', (data) => {
      const msg = data.toString();
      console.log('[server]', msg);
      if (msg.includes('Running on') || msg.includes('http://')) {
        resolve();
      }
    });

    serverProcess.stderr.on('data', (data) => {
      const msg = data.toString();
      console.log('[server]', msg);
      if (msg.includes('Running on') || msg.includes('http://')) {
        resolve();
      }
    });

    serverProcess.on('error', (err) => {
      console.error('Failed to start server:', err);
      reject(err);
    });

    serverProcess.on('exit', (code) => {
      console.log('Server exited with code:', code);
    });

    setTimeout(resolve, 4000);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    icon: path.join(__dirname, '..', 'electron', 'icon.png'),
    title: 'ZETA',
    backgroundColor: '#0a0a0c',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  Menu.setApplicationMenu(null);

  mainWindow.loadURL(SERVER_URL);

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(async () => {
  try {
    await startServer();
    createWindow();
  } catch (err) {
    console.error('Could not start server:', err);
    app.quit();
  }
});

app.on('window-all-closed', () => {
  if (serverProcess) {
    serverProcess.kill();
    serverProcess = null;
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});

app.on('before-quit', () => {
  if (serverProcess) {
    serverProcess.kill();
    serverProcess = null;
  }
});