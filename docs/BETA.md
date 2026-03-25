# Piano Tutor Beta（桌面版）

Beta 目标：让体验用户**无需安装 Python / pip**，解压后**双击 `Piano Tutor Beta.exe`** 即可使用（同一套 FastAPI + Vue，由 PyInstaller 打包的后端 `piano-backend.exe` 提供）。

## 原理简述

1. **FastAPI** 在存在 `frontend/dist` 时，会在**同一端口**托管静态页面（`/api` 与页面同源）。
2. **Electron** 在打包产物中启动 `resources/piano/piano-backend/piano-backend.exe`（内嵌 uvicorn），监听 `127.0.0.1:8765`（可用环境变量 `PIANO_TUTOR_PORT` 修改），窗口加载该地址。
3. **开发者本机调试**仍可用系统 Python：`py -m uvicorn backend.app:app`（见下文）。

## 体验用户环境要求（当前 Beta）

- **Windows 10/11（64 位）**
- **无需**安装 Python；首次运行若杀毒软件拦截，请将程序加入信任。

> **MP3 录音比对**：若需 MP3，本机最好已安装 **ffmpeg** 并可在 PATH 中使用；或把 **ffmpeg.exe** 放到 `piano-backend` 文件夹（与 `piano-backend.exe` 同级）。**WAV / MIDI** 一般可直接用。

## 云端 Beta（仅 Electron 壳，无本地 Python / 无 PyInstaller）

适用：你已在公网部署 **HTTPS API**（如 `docs/CLOUD_DEPLOY_MINIMAL.md`），希望用户**解压即用**，所有逻辑走云端，安装包**不必**包含 `piano-backend`。

1. **构建前端**（写入公网 API 基址 + 供 `file://` 使用的相对资源路径 `base: './'`）：在项目根执行 **`npm run beta:build-web:cloud`**。  
   脚本里默认域名是 **`https://api.keygent.xyz`** 与 **`https://admin-api.keygent.xyz`**；换域名请改根目录 `package.json` 里该脚本的 `VITE_PUBLIC_API_BASE` / `VITE_ADMIN_API_BASE`，或自行执行  
   `cross-env VITE_PUBLIC_API_BASE=... VITE_ADMIN_API_BASE=... VITE_ELECTRON_FILE=1 npm run build --prefix frontend`。

2. **开发机自测云端模式**：将 **`desktop/app-config.cloud.example.json`** 复制为 **`desktop/app-config.json`**（或把其中 `backendMode` 改为 `cloud` 并填写 `cloudPublicApiBase` / `cloudAdminApiBase`），再 **`cd desktop && npm start`**。此时不会启动本机 uvicorn，会先请求云端 `/health`，再打开本地 `frontend/dist`。

3. **打精简安装包**（不含 `dist_py/piano-backend`，体积小）：项目根 **`npm run beta:pack:cloud`**（会先执行 `beta:build-web:cloud`）。  
   产物显示名为 **Piano Tutor Beta (Cloud)**。包内 **`resources/piano/app-config.json`** 固定来自 **`desktop/app-config.cloud.example.json`**，避免误把开发机上的 `backendMode=local` 打进包。

4. **助手密钥**：走云端时 **DashScope Key 只放在服务器 `.env`**，用户端无需配置 `publisher.env`。

5. **与本地全量 Beta 的区别**：含冻结后端的绿色包仍用 **`npm run beta:pack`**；云端精简包用 **`npm run beta:pack:cloud`**。

环境变量覆盖（可选）：**`PIANO_BACKEND_MODE=cloud`** 或 **`local`** 可覆盖 `app-config.json` 里的 `backendMode`。

## 开发者：本地调试桌面壳

在项目根目录：

```bash
cd frontend && npm run build
cd ../desktop && npm install && npm start
```

若前端已构建过，可直接：

```bash
cd desktop && npm start
```

一键重新构建前端并启动：

```bash
cd desktop && npm run start:fresh
```

（开发模式下 Electron 会调用本机 `py -m uvicorn`，需在项目根执行过一次 `py -m pip install -r backend/requirements.txt`。）

## 开发者：打 Windows 包（含冻结后端）

```bash
npm run beta:pack
```

该命令会依次：**构建前端** → **PyInstaller 打包后端到 `dist_py/piano-backend/`** → **electron-builder 打 zip**。

若你已打好 `dist_py/piano-backend` 且只想重打 Electron 壳：

```bash
npm run beta:build-web
cd desktop && npm install && npm run dist
```

产物在 `desktop/dist-out/`：

- **ZIP 包（默认）**：`Piano Tutor Beta x.x.x.zip` — **不经过 NSIS**，适合国内网络。发给用户后：**解压 zip → 进入文件夹 → 双击 `Piano Tutor Beta.exe`**。
- **单文件便携 exe**（仍依赖 NSIS 工具链）：`cd desktop && npm install && npm run dist:portable`（已配置 `ELECTRON_BUILDER_BINARIES_MIRROR`）。

**可选：NSIS 安装包**：

```bash
cd desktop && npm run dist:installer
```

成功后在 `dist-out/` 得到 `Piano Tutor Beta Setup x.x.x.exe`。

打包后目录要点：

- `resources/piano/piano-backend/`：整份 onedir（含 `piano-backend.exe`、`frontend/dist`、`_internal` 等）。
- 运行时 **曲库 / SQLite** 写在 `piano-backend/data/`（与 exe 同级，可写）。

## 仅打包后端（调试 PyInstaller）

在项目根：

```bash
npm run beta:bundle-backend
```

需已安装 **Python 3.10+**，且能执行 `py`。首次或依赖变更后建议先：`py -m pip install -r backend/requirements.txt`。

## 环境变量与智能助手

### 发布者代填密钥（用户无需配置）

打包前在项目里：

1. 复制 **`desktop/publisher.env.example`** 为 **`desktop/publisher.env`**（该文件已在 `.gitignore` 中，勿提交仓库）。
2. 在 `publisher.env` 中填写 **`DASHSCOPE_API_KEY`**（及可选的 `DASHSCOPE_MODEL`、`ADMIN_PASSCODE` 等）。
3. 执行 **`npm run beta:pack`**。脚本会把内容写入 `resources/piano/publisher-bundled.env` 打进 zip。

**注意**：密钥会出现在分发给用户的安装包中，存在被盗用与产生费用的风险，仅建议可控范围内测使用。

### 用户自行配置（未使用 publisher.env 时）

将 `resources/piano/.env.example` 复制为同目录 **`.env`**，按说明填入密钥。冻结后端加载顺序为：

1. `resources/piano/publisher-bundled.env`（发布者内置，可为占位空文件）
2. `resources/piano/.env`
3. `piano-backend/.env`（若存在则**覆盖**同名项）

不配置助手也能用上传、比对等其它功能。

## 用户使用方式（与你描述的流程一致）

1. **浏览器或网盘下载**你提供的 **ZIP 安装包**（`npm run beta:pack` 产物）。
2. **解压到任意文件夹**（路径尽量简短，少特殊字符）。
3. **双击 `Piano Tutor Beta.exe`** → 自动起本地服务 → 窗口内即全部功能（无需再装 Python）。

> 说明：当前为 **绿色版 / 便携包**，不做「安装向导写注册表」；若以后需要 NSIS 安装程序，可用 `npm run dist:installer`，用户仍是「下载 → 运行安装程序 → 从开始菜单打开」。

## 版本更新提醒（发布者配置）

应用会在启动约 **3 秒后**尝试拉取一份 **release 清单（JSON）**，若发现**新版本号大于当前**（`desktop/package.json` 里的 `version`），会弹窗提示，并可一键用浏览器打开 **下载链接**。

- **清单格式示例**：见仓库 **`docs/release-manifest.example.json`**（字段 `version`、`downloadUrl`、`notes`；也支持 `url` / `changelog` 等别名）。
- **强制更新阈值（可选）**：在 JSON 里设置 `min_supported_version`（或 `minSupportedVersion`）。当客户端版本低于该值时，会弹出“需要更新”并退出应用（可引导打开下载链接）。
- **把清单放到网上**：任意 **HTTPS** 可访问地址即可（如 **GitHub Raw**、对象存储、你自己的服务器）。
- **告诉程序去哪里读清单**（三选一）：
  1. 打包前编辑 **`desktop/update-config.json`**，填写 `"manifestUrl": "https://你的域名/.../release.json"`（会打进 `resources/piano/update-config.json`，高级用户也可解压后改这个文件）。
  2. 或设置环境变量 **`PIANO_UPDATE_MANIFEST_URL`**（同一条 HTTPS 链接）。
  3. 若 `manifestUrl` 为空且未设环境变量，则**不检查更新**，不影响使用。

用户可在菜单 **「帮助 → 检查更新」** 手动检查；**「不再提示此版本」** 会记住该版本号，**下一个更高版本**发布后会再次提醒。

> 当前实现为 **「提醒 + 打开下载页」**，不会在后台自动下载、替换程序（避免签名与杀毒误报问题）。发新版时记得同步提高 **`desktop/package.json` 的 `version`**，并与网上 JSON 里的 `version` 一致或更低（用户端才会判定为「有更新」）。如需淘汰旧版本，可提升 `min_supported_version`。

## 端口与冲突

默认 **8765**。若占用，启动前设置：

```bash
set PIANO_TUTOR_PORT=8877
```

（Electron 的 `main.js` 已读取 `PIANO_TUTOR_PORT` 并传给子进程。）

## 常见问题

| 现象 | 处理 |
|------|------|
| 提示未找到 `frontend/dist` | 打包前执行 `npm run beta:build-web`；或检查 `dist_py/piano-backend/frontend/dist` 是否存在 |
| `npm run beta:pack` 时 PyInstaller 报错缺模块 | 在 `desktop/pyinstaller/piano-backend.spec` 的 `hiddenimports` 中补充，或对相应包使用 `collect_all` |
| 后端启动超时 | 杀毒是否拦截 `piano-backend.exe`；或查看 `piano-backend` 目录是否完整 |
| 智能助手 503 | 检查 `resources/piano/.env` 中 `DASHSCOPE_API_KEY` |
| 关闭窗口后端口仍占用 | 结束残留 `piano-backend` 进程后重试 |
| **云端 Beta 启动报无法连接 `/health`，但浏览器能打开** | 请更新到已改用 `electron.net` 做健康检查的桌面壳；旧版用 Node `https` 在部分 Windows/代理环境下会与 `curl`/Schannel 表现不一致 |
| **`npm run beta:pack` 卡在下载 Electron** | 见下文镜像说明；国内可多次重试或手动设 `ELECTRON_MIRROR` |
| **`winCodeSign` / 符号链接权限** | 已设 `signAndEditExecutable: false`；可删 `%LOCALAPPDATA%\electron-builder\Cache\winCodeSign` 后重试 |
| **便携 `portable` 仍拉 NSIS 失败** | 默认已改为 **zip**；或 `npm run dist:portable`（已配国内 mirror） |

## 反馈收集建议

- 版本号：关于页或让用户报「Beta 版本 x.x.x」
- 固定问卷：最难用的 3 步、最想要的 1 个功能

## 相关文档

- 云端最小部署：`docs/CLOUD_DEPLOY_MINIMAL.md`
- 内测发版清单：`docs/BETA_RELEASE_CHECKLIST.md`
