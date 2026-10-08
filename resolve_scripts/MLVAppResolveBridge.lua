local REPO_ROOT = "F:\\Coding Projects\\mlvapp-resolve-bridge"
local CONFIG = REPO_ROOT .. "\\bridge\\config.local-smoke.example.json"
local PYTHON = "python"

local function quote(value)
    return '"' .. tostring(value):gsub('"', '\\"') .. '"'
end

local function requestMlvFiles()
    local ok, selected = pcall(function()
        return fusion:RequestFile("", "", { FReqB_Multi = true })
    end)

    if not ok then
        ok, selected = pcall(function()
            return fusion.RequestFile("", "", { FReqB_Multi = true })
        end)
    end

    if not ok or selected == nil or selected == "" then
        return {}
    end

    if type(selected) == "string" then
        if selected:lower():match("%.mlv$") then
            return { selected }
        end
        return {}
    end

    local paths = {}
    if type(selected) == "table" then
        local base = selected.Path or selected.path or ""
        for key, value in pairs(selected) do
            if key ~= "Path" and key ~= "path" then
                local child = tostring(value)
                local fullPath = child
                if base ~= "" and not child:match("^%a:[/\\]") then
                    fullPath = base .. child
                end
                if fullPath:lower():match("%.mlv$") then
                    table.insert(paths, fullPath)
                end
            end
        end
    end
    return paths
end

local function runBridge(paths)
    local bridgeScript = REPO_ROOT .. "\\bridge\\mlvapp_resolve_bridge.py"
    local parts = {
        quote(PYTHON),
        quote(bridgeScript),
        "--resolve-import-list",
        "--config",
        quote(CONFIG)
    }

    for _, path in ipairs(paths) do
        table.insert(parts, quote(path))
    end

    local command = table.concat(parts, " ")
    print("MLV bridge command: " .. command)

    local handle = io.popen(command)
    if handle == nil then
        print("Could not launch bridge command.")
        return {}
    end

    local output = handle:read("*a")
    handle:close()

    local clipInfos = {}
    for line in output:gmatch("[^\r\n]+") do
        local kind, filePath, startIndex, endIndex = line:match("^([^\t]+)\t([^\t]+)\t([^\t]*)\t([^\t]*)$")
        if filePath ~= nil then
            if kind == "sequence" then
                table.insert(clipInfos, {
                    FilePath = filePath,
                    StartIndex = tonumber(startIndex),
                    EndIndex = tonumber(endIndex)
                })
            else
                table.insert(clipInfos, { FilePath = filePath })
            end
        else
            print(line)
        end
    end
    return clipInfos
end

local paths = requestMlvFiles()
if #paths == 0 then
    print("No .MLV clips selected.")
    return
end

local resolveObj = resolve or Resolve()
local projectManager = resolveObj:GetProjectManager()
local project = projectManager:GetCurrentProject()
if project == nil then
    print("No current Resolve project.")
    return
end

local clipInfos = runBridge(paths)
if #clipInfos == 0 then
    print("No exported assets were discovered.")
    return
end

resolveObj:OpenPage("media")
local mediaPool = project:GetMediaPool()
local imported = mediaPool:ImportMedia(clipInfos)

for _, info in ipairs(clipInfos) do
    local suffix = ""
    if info.StartIndex ~= nil then
        suffix = " [" .. tostring(info.StartIndex) .. "-" .. tostring(info.EndIndex) .. "]"
    end
    print("Resolve import: " .. info.FilePath .. suffix)
end

if imported ~= nil then
    print("Imported " .. tostring(#imported) .. " item(s).")
else
    print("Resolve did not report imported clips.")
end
