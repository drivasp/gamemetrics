const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('gamemetricsDesktop', {
  downloadAndInstall: (opts) => {
    const { onProgress, ...payload } = opts || {};
    const handler = (_e, data) => {
      if (data?.productId === payload.productId && typeof onProgress === 'function') {
        onProgress(data.pct);
      }
    };
    ipcRenderer.on('install-progress', handler);
    return ipcRenderer
      .invoke('download-and-install', payload)
      .finally(() => ipcRenderer.removeListener('install-progress', handler));
  },
  launchGame: (opts) => ipcRenderer.invoke('launch-game', opts),
  checkUpdate: (opts) => ipcRenderer.invoke('check-update', opts),
});
