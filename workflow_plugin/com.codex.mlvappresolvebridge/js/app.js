const dropZone = document.getElementById("dropZone");
const queue = document.getElementById("queue");
const log = document.getElementById("log");
const browseButton = document.getElementById("browseButton");
const runButton = document.getElementById("runButton");
const clearButton = document.getElementById("clearButton");
const pythonInput = document.getElementById("pythonInput");
const repoRootInput = document.getElementById("repoRootInput");
const configInput = document.getElementById("configInput");

let files = [];

function writeLog(message) {
  log.textContent = `${log.textContent}${message}\n`;
  log.scrollTop = log.scrollHeight;
}

function renderQueue() {
  queue.innerHTML = "";
  files.forEach((file) => {
    const item = document.createElement("li");
    item.textContent = file;
    queue.appendChild(item);
  });
  runButton.disabled = files.length === 0;
  clearButton.disabled = files.length === 0;
}

function addPaths(paths) {
  const next = paths.filter((filePath) => filePath && filePath.toLowerCase().endsWith(".mlv"));
  files = Array.from(new Set([...files, ...next]));
  renderQueue();
}

function addFiles(fileList) {
  addPaths(Array.from(fileList).map((file) => file.path));
}

async function loadDefaults() {
  const defaults = await window.mlvBridge.defaults();
  pythonInput.value = defaults.python || "python";
  repoRootInput.value = defaults.repoRoot || "";
  configInput.value = defaults.config || "";
}

dropZone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropZone.classList.add("active");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("active");
});

dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropZone.classList.remove("active");
  addFiles(event.dataTransfer.files);
});

browseButton.addEventListener("click", async () => {
  try {
    addPaths(await window.mlvBridge.selectMlvFiles());
  } catch (error) {
    writeLog(error.stack || error.message);
  }
});

clearButton.addEventListener("click", () => {
  files = [];
  log.textContent = "";
  renderQueue();
});

runButton.addEventListener("click", async () => {
  runButton.disabled = true;
  writeLog(`Exporting ${files.length} clip(s)...`);

  try {
    const options = { python: pythonInput.value || "python" };
    if (repoRootInput.value.trim()) {
      options.repoRoot = repoRootInput.value.trim();
    }
    if (configInput.value.trim()) {
      options.config = configInput.value.trim();
    }

    const result = await window.mlvBridge.runBridge(files, options);
    if (result.stderr) {
      writeLog(result.stderr);
    }
    if (result.code !== 0) {
      writeLog(`Bridge exited with code ${result.code}.`);
    }

    const assets = result.payload.results.flatMap((item) => item.assets || []);
    if (assets.length === 0) {
      writeLog("No exported assets were discovered.");
      return;
    }

    writeLog(`Importing ${assets.length} exported path(s) into Resolve...`);
    const imported = await window.mlvBridge.importIntoMediaPool(assets);
    imported.clipInfos.forEach((item) => {
      const range = item.StartIndex !== undefined ? ` [${item.StartIndex}-${item.EndIndex}]` : "";
      writeLog(`Resolve import: ${item.FilePath}${range}`);
    });
    writeLog(`Imported ${imported.count} item(s).`);
  } catch (error) {
    writeLog(error.stack || error.message);
  } finally {
    renderQueue();
  }
});

window.addEventListener("beforeunload", () => {
  window.mlvBridge.cleanupResolve();
});

loadDefaults()
  .catch((error) => writeLog(error.stack || error.message))
  .finally(renderQueue);
