const { contextBridge } = require("electron");
const childProcess = require("child_process");
const fs = require("fs");
const path = require("path");

const PLUGIN_ID = "com.codex.mlvappresolvebridge";

function findRepoRoot() {
  let current = __dirname;
  for (let i = 0; i < 8; i += 1) {
    const candidate = path.join(current, "bridge", "mlvapp_resolve_bridge.py");
    if (fs.existsSync(candidate)) {
      return current;
    }
    current = path.dirname(current);
  }
  return path.resolve(__dirname, "..", "..");
}

function getResolve() {
  const modulePath = path.join(__dirname, "WorkflowIntegration.node");
  if (!fs.existsSync(modulePath)) {
    return null;
  }

  const workflowIntegration = require(modulePath);
  const initialized = workflowIntegration.Initialize(PLUGIN_ID);
  if (!initialized) {
    return null;
  }
  return workflowIntegration.GetResolve();
}

function runBridge(files, options) {
  return new Promise((resolve, reject) => {
    const repoRoot = options.repoRoot || findRepoRoot();
    const script = path.join(repoRoot, "bridge", "mlvapp_resolve_bridge.py");
    const config = options.config || path.join(repoRoot, "bridge", "config.local.json");
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
      let payload = null;
      try {
        payload = JSON.parse(stdout);
      } catch (error) {
        reject(new Error(`Bridge returned invalid JSON: ${error.message}\n${stderr}`));
        return;
      }
      resolve({ code, stderr, payload });
    });
  });
}

function importIntoMediaPool(paths) {
  const resolve = getResolve();
  if (!resolve) {
    throw new Error("Resolve WorkflowIntegration.node is missing or failed to initialize.");
  }

  const project = resolve.GetProjectManager().GetCurrentProject();
  if (!project) {
    throw new Error("No current Resolve project.");
  }

  const mediaPool = project.GetMediaPool();
  const imported = mediaPool.ImportMedia(paths);
  return { count: imported ? imported.length : 0 };
}

contextBridge.exposeInMainWorld("mlvBridge", {
  runBridge,
  importIntoMediaPool
});
