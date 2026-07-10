const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('vertexElectron', {
  isElectron: true,
  platform: process.platform,
});