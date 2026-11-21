const { app, BrowserWindow, Tray, Menu, nativeImage, ipcMain, shell, Notification } = require('electron');
const path = require('path');
const http = require('http');

let mainWindow = null;
let tray = null;
let isQuiting = false;

// Ensure single instance lock
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      if (!mainWindow.isVisible()) mainWindow.show();
      mainWindow.focus();
    }
  });
}

function getIconPath() {
  const icoPath = path.join(__dirname, 'assets', 'icon.ico');
  const pngPath = path.join(__dirname, 'assets', 'icon.png');
  return process.platform === 'win32' ? icoPath : pngPath;
}

function checkDevServer(url) {
  return new Promise((resolve) => {
    const req = http.get(url, (res) => {
      resolve(res.statusCode >= 200 && res.statusCode < 400);
    });
    req.on('error', () => resolve(false));
    req.setTimeout(1000, () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function createWindow() {
  const icon = getIconPath();

  mainWindow = new BrowserWindow({
    width: 1280,
    height: 850,
    minWidth: 980,
    minHeight: 640,
    backgroundColor: '#0b0f19',
    autoHideMenuBar: true,
    show: false, // Show gracefully once ready-to-show
    icon: icon,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false,
    },
  });

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    mainWindow.focus();
  });

  // Minimize to tray on close rather than terminating
  mainWindow.on('close', (event) => {
    if (!isQuiting) {
      event.preventDefault();
      mainWindow.hide();
      if (tray && process.platform === 'win32') {
        tray.displayBalloon({
          iconType: 'info',
          title: 'AutoMe Active',
          content: 'AutoMe is running in the background. Auto-replies and message proxies remain active.',
        });
      }
    }
  });

  // Load either Vite Dev Server or Production Dist
  const isDev = process.env.NODE_ENV === 'development' || process.argv.includes('--dev');
  const devServerUrl = 'http://localhost:5173';

  if (isDev) {
    const devRunning = await checkDevServer(devServerUrl);
    if (devRunning) {
      mainWindow.loadURL(devServerUrl);
      return;
    }
  }

  // Fallback / Production: load build dist/index.html
  const distIndexPath = path.join(__dirname, '..', 'dist', 'index.html');
  const fs = require('fs');
  if (fs.existsSync(distIndexPath)) {
    mainWindow.loadFile(distIndexPath);
  } else {
    // If dist not built yet, attempt to connect to dev server
    mainWindow.loadURL(devServerUrl).catch(() => {
      mainWindow.loadFile(path.join(__dirname, 'splash.html')).catch(() => {});
    });
  }
}

function createTray() {
  const trayIconPath = path.join(__dirname, 'assets', 'tray-icon.png');
  const trayImage = nativeImage.createFromPath(trayIconPath);
  tray = new Tray(trayImage);

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Open AutoMe',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        }
      },
    },
    {
      label: 'Hide to Tray',
      click: () => {
        if (mainWindow) mainWindow.hide();
      },
    },
    { type: 'separator' },
    {
      label: 'Backend Swagger Docs',
      click: () => shell.openExternal('http://127.0.0.1:8000/docs'),
    },
    {
      label: 'WhatsApp Microservice Status',
      click: () => shell.openExternal('http://localhost:3001/status?user_id=2'),
    },
    { type: 'separator' },
    {
      label: 'Quit AutoMe',
      click: () => {
        isQuiting = true;
        app.quit();
      },
    },
  ]);

  tray.setToolTip('AutoMe - AI Social Proxy');
  tray.setContextMenu(contextMenu);

  tray.on('double-click', () => {
    if (mainWindow) {
      if (mainWindow.isVisible()) {
        mainWindow.hide();
      } else {
        mainWindow.show();
        mainWindow.focus();
      }
    }
  });
}

// IPC Handlers
ipcMain.on('window-minimize', () => {
  if (mainWindow) mainWindow.minimize();
});

ipcMain.on('window-maximize', () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  }
});

ipcMain.on('window-close', () => {
  if (mainWindow) mainWindow.close();
});

ipcMain.on('notify', (event, { title, body }) => {
  if (Notification.isSupported()) {
    new Notification({
      title: title || 'AutoMe',
      body: body || '',
      icon: path.join(__dirname, 'assets', 'icon.png'),
    }).show();
  }
});

app.whenReady().then(() => {
  createTray();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('before-quit', () => {
  isQuiting = true;
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    // Keep app alive in tray unless isQuiting is true
    if (isQuiting) {
      app.quit();
    }
  }
});
