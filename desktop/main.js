const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');
const https = require('https');
const http = require('http');
const { URL } = require('url');
const extract = require('extract-zip');

const STORE_URL = process.env.GM_STORE_URL || 'http://localhost:4000/store';
const API_ORIGIN = process.env.GM_API_URL || 'http://localhost:8080';
const LIBRARY_DIR = path.join(app.getPath('userData'), 'library');

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function createWindow() {
  ensureDir(LIBRARY_DIR);
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    title: 'GameMetrics Desktop',
  });
  win.loadURL(STORE_URL);
}

function fetchBuffer(url, headers, onProgress) {
  return new Promise((resolve, reject) => {
    const u = new URL(url.startsWith('http') ? url : `${API_ORIGIN}${url}`);
    const lib = u.protocol === 'https:' ? https : http;
    const req = lib.get(
      {
        hostname: u.hostname,
        port: u.port,
        path: u.pathname + u.search,
        headers,
      },
      (res) => {
        if (res.statusCode && res.statusCode >= 400) {
          reject(new Error(`HTTP ${res.statusCode}`));
          res.resume();
          return;
        }
        const total = Number(res.headers['content-length'] || 0);
        const chunks = [];
        let received = 0;
        res.on('data', (chunk) => {
          chunks.push(chunk);
          received += chunk.length;
          if (onProgress) {
            const pct = total > 0 ? Math.min(99, Math.round((received / total) * 100)) : 50;
            onProgress(pct);
          }
        });
        res.on('end', () => {
          if (onProgress) onProgress(100);
          resolve(Buffer.concat(chunks));
        });
      },
    );
    req.on('error', reject);
  });
}

ipcMain.handle('download-and-install', async (event, payload) => {
  const { productId, gameName, downloadUrl, token } = payload || {};
  if (!productId || !downloadUrl) throw new Error('payload incompleto');

  const gameDir = path.join(LIBRARY_DIR, productId);
  ensureDir(gameDir);
  const zipPath = path.join(gameDir, 'package.zip');

  const buf = await fetchBuffer(
    downloadUrl,
    token ? { Authorization: `Bearer ${token}` } : {},
    (pct) => event.sender.send('install-progress', { productId, pct }),
  );
  fs.writeFileSync(zipPath, buf);
  const checksum = crypto.createHash('sha256').update(buf).digest('hex');

  await extract(zipPath, { dir: gameDir });
  fs.writeFileSync(
    path.join(gameDir, 'install.json'),
    JSON.stringify({ productId, gameName, checksum, installedAt: Date.now() }, null, 2),
  );
  return { ok: true, path: gameDir, checksum };
});

ipcMain.handle('launch-game', async (_event, payload) => {
  const { productId } = payload || {};
  const entry = path.join(LIBRARY_DIR, productId, 'index.html');
  if (!fs.existsSync(entry)) {
    throw new Error('Juego no instalado en el cliente de escritorio');
  }
  await shell.openPath(entry);
  return { ok: true };
});

ipcMain.handle('check-update', async (_event, payload) => {
  const { productId, gameName, token } = payload || {};
  if (!productId) throw new Error('productId requerido');
  const q = gameName ? `?game_name=${encodeURIComponent(gameName)}` : '';
  const url = `${API_ORIGIN}/launcher/updates/${productId}${q}`;
  const buf = await fetchBuffer(url, token ? { Authorization: `Bearer ${token}` } : {});
  const info = JSON.parse(buf.toString('utf8'));
  return info;
});

app.whenReady().then(createWindow);
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
