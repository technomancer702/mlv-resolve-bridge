const { app, BrowserWindow } = require("electron");
const path = require("path");

function createWindow() {
  const win = new BrowserWindow({
    width: 720,
    height: 620,
    minWidth: 560,
    minHeight: 460,
    title: "MLV-App Resolve Bridge",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    }
  });

  win.loadFile(path.join(__dirname, "index.html"));
}

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  app.quit();
});
