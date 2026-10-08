const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("mlvBridge", {
  defaults: () => ipcRenderer.invoke("bridge:defaults"),
  selectMlvFiles: () => ipcRenderer.invoke("bridge:selectMlvFiles"),
  runBridge: (files, options) => ipcRenderer.invoke("bridge:runBridge", files, options),
  importIntoMediaPool: (paths) => ipcRenderer.invoke("bridge:importIntoMediaPool", paths),
  cleanupResolve: () => ipcRenderer.invoke("bridge:cleanupResolve")
});
