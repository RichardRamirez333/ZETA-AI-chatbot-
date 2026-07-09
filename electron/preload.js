const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('zetaElectron', {
  isElectron: true,
  platform: process.platform,
});