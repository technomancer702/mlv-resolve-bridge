const { app, BrowserWindow, dialog, ipcMain } = require("electron");
const childProcess = require("child_process");
const fs = require("fs");
const path = require("path");

const PLUGIN_ID = "com.codex.mlvappresolvebridge";
const DEFAULT_REPO_ROOT = "F:\\Coding Projects\\mlvapp-resolve-bridge";
const DEFAULT_CONFIG = path.join(DEFAULT_REPO_ROOT, "bridge", "config.local-smoke.example.json");

let mainWindow = null;
let workflowIntegration = null;
let resolveObject = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 760,
    height: 660,
    minWidth: 580,
    minHeight: 500,
    title: "MLV-App Resolve Bridge",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    }
  });

  mainWindow.loadFile(path.join(__dirname, "index.html"));
}

function findRepoRoot(startDir = __dirname) {
  let current = startDir;
  for (let i = 0; i < 10; i += 1) {
    const candidate = path.join(current, "bridge", "mlvapp_resolve_bridge.py");
    if (fs.existsSync(candidate)) {
      return current;
    }
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
  return DEFAULT_REPO_ROOT;
}

async function getResolve() {
  if (resolveObject) return resolveObject;

  const modulePath = path.join(__dirname, "WorkflowIntegration.node");
  if (!fs.existsSync(modulePath)) {
    throw new Error(`WorkflowIntegration.node is missing from ${__dirname}`);
  }

  workflowIntegration = workflowIntegration || require(modulePath);
  const initialized = await workflowIntegration.Initialize(PLUGIN_ID);
  if (!initialized) {
    throw new Error("Resolve WorkflowIntegration.Initialize failed.");
  }

  resolveObject = await workflowIntegration.GetResolve();
  if (!resolveObject) {
    throw new Error("Could not get Resolve object.");
  }

  return resolveObject;
}

async function cleanupResolve() {
  if (workflowIntegration) {
    await workflowIntegration.CleanUp();
  }
  workflowIntegration = null;
  resolveObject = null;
}

function runBridge(_event, files, options = {}) {
  return new Promise((resolve, reject) => {
    const repoRoot = options.repoRoot || findRepoRoot();
    const script = path.join(repoRoot, "bridge", "mlvapp_resolve_bridge.py");
    const config = options.config || path.join(repoRoot, "bridge", "config.local-smoke.example.json");
    const args = [script, "--config", config, ...files];

    const child = childProcess.spawn(options.python || "python", args, {
      cwd: repoRoot,
      windowsHide: true
    });

    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("error", reject);
    child.on("close", (code) => {
      try {
        resolve({ code, stderr, payload: JSON.parse(stdout) });
      } catch (error) {
        reject(new Error(`Bridge returned invalid JSON: ${error.message}\n${stderr}\n${stdout}`));
      }
    });
  });
}

async function selectMlvFiles() {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: "Select MLV clips",
    buttonLabel: "Add Clips",
    filters: [{ name: "Magic Lantern Video", extensions: ["mlv"] }],
    properties: ["openFile", "multiSelections"]
  });

  return result.canceled ? [] : result.filePaths;
}

function dngSequenceImportInfo(assetPath) {
  const stats = fs.existsSync(assetPath) ? fs.statSync(assetPath) : null;
  const directory = stats && stats.isDirectory() ? assetPath : path.dirname(assetPath);
  if (!fs.existsSync(directory)) return null;

  const groups = new Map();
  for (const name of fs.readdirSync(directory)) {
    const match = name.match(/^(.*?)(\d+)(\.[dD][nN][gG])$/);
    if (!match) continue;

    const key = `${match[1]}|${match[2].length}|${match[3].toLowerCase()}`;
    const group = groups.get(key) || {
      prefix: match[1],
      width: match[2].length,
      extension: match[3],
      frames: []
    };
    group.frames.push(Number.parseInt(match[2], 10));
    groups.set(key, group);
  }

  const candidates = Array.from(groups.values()).filter((group) => group.frames.length > 0);
  if (candidates.length === 0) return null;

  candidates.sort((a, b) => b.frames.length - a.frames.length);
  const best = candidates[0];
  const start = Math.min(...best.frames);
  const end = Math.max(...best.frames);
  return {
    FilePath: path.join(directory, `${best.prefix}%0${best.width}d${best.extension}`),
    StartIndex: start,
    EndIndex: end
  };
}

function toImportClipInfo(assetPath) {
  const ext = path.extname(assetPath).toLowerCase();
  if (ext === ".dng" || (fs.existsSync(assetPath) && fs.statSync(assetPath).isDirectory())) {
    const sequence = dngSequenceImportInfo(assetPath);
    if (sequence) return sequence;
  }
  return { FilePath: assetPath };
}

async function importIntoMediaPool(_event, assetPaths) {
  const resolve = await getResolve();
  const projectManager = await resolve.GetProjectManager();
  const project = projectManager ? await projectManager.GetCurrentProject() : null;
  if (!project) {
    throw new Error("No current Resolve project.");
  }

  const mediaPool = await project.GetMediaPool();
  if (!mediaPool) {
    throw new Error("Could not get Resolve media pool.");
  }

  await resolve.OpenPage("media");
  const clipInfos = assetPaths.filter(Boolean).map(toImportClipInfo);
  const imported = await mediaPool.ImportMedia(clipInfos);
  return {
    count: imported ? imported.length : 0,
    clipInfos
  };
}

function registerHandlers() {
  ipcMain.handle("bridge:defaults", () => ({
    repoRoot: findRepoRoot(),
    config: DEFAULT_CONFIG,
    python: "python"
  }));
  ipcMain.handle("bridge:selectMlvFiles", selectMlvFiles);
  ipcMain.handle("bridge:runBridge", runBridge);
  ipcMain.handle("bridge:importIntoMediaPool", importIntoMediaPool);
  ipcMain.handle("bridge:cleanupResolve", cleanupResolve);
}

app.whenReady().then(() => {
  registerHandlers();
  createWindow();
});

app.on("window-all-closed", async () => {
  await cleanupResolve();
  app.quit();
});
