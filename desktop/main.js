/**
 * Piano Tutor Beta — Electron 主进程
 * - local：启动本机 FastAPI（PyInstaller 或开发机 Python），窗口加载 http://127.0.0.1:端口
 * - cloud：不启本地后端，前端构建需带 VITE_PUBLIC_API_BASE 等；窗口 loadFile 本地 dist，请求直连云端
 */
const { app, BrowserWindow, dialog, shell, Menu, net } = require('electron')
const path = require('path')
const { spawn } = require('child_process')
const http = require('http')
const updateCheck = require('./update-check')

const BETAPORT = Number(process.env.PIANO_TUTOR_PORT || 8765)
const HEALTH_URL = `http://127.0.0.1:${BETAPORT}/health`
const APP_URL = `http://127.0.0.1:${BETAPORT}/`

let mainWindow = null
let backendProc = null

const fs = require('fs')

function getPianoResourcesDir() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'piano')
  }
  return path.join(__dirname, '..')
}

function resolveAppConfigPath() {
  const piano = getPianoResourcesDir()
  const inPiano = path.join(piano, 'app-config.json')
  if (fs.existsSync(inPiano)) return inPiano
  if (!app.isPackaged) {
    const inDesktop = path.join(__dirname, 'app-config.json')
    if (fs.existsSync(inDesktop)) return inDesktop
  }
  return null
}

function loadAppRuntimeConfig() {
  const p = resolveAppConfigPath()
  const fallback = { backendMode: 'local', cloudPublicApiBase: '', cloudAdminApiBase: '' }
  if (!p) return fallback
  try {
    const raw = JSON.parse(fs.readFileSync(p, 'utf8'))
    const mode = String(raw.backendMode || 'local').toLowerCase()
    const backendMode = mode === 'cloud' ? 'cloud' : 'local'
    return {
      backendMode,
      cloudPublicApiBase: String(raw.cloudPublicApiBase || '').trim(),
      cloudAdminApiBase: String(raw.cloudAdminApiBase || '').trim(),
    }
  } catch (e) {
    console.error('[app-config]', e)
    return fallback
  }
}

function effectiveBackendMode(cfg) {
  const env = String(process.env.PIANO_BACKEND_MODE || '').toLowerCase().trim()
  if (env === 'cloud' || env === 'local') return env
  return cfg.backendMode
}

/** 开发：仓库根；打包+冻结后端：piano-backend.exe 所在目录；打包+源码回退：resources/piano */
function getBackendRoot() {
  const piano = getPianoResourcesDir()
  const bundledDir = path.join(piano, 'piano-backend')
  const exeName = process.platform === 'win32' ? 'piano-backend.exe' : 'piano-backend'
  const bundledExe = path.join(bundledDir, exeName)
  if (app.isPackaged && fs.existsSync(bundledExe)) {
    return bundledDir
  }
  return piano
}

function pickPythonCommand() {
  if (process.platform === 'win32') {
    return 'py'
  }
  return 'python3'
}

function startBackend(cwd) {
  const piano = getPianoResourcesDir()
  const bundledDir = path.join(piano, 'piano-backend')
  const exeName = process.platform === 'win32' ? 'piano-backend.exe' : 'piano-backend'
  const bundledExe = path.join(bundledDir, exeName)
  if (app.isPackaged && fs.existsSync(bundledExe)) {
    const opts = {
      cwd: bundledDir,
      shell: false,
      windowsHide: true,
      env: {
        ...process.env,
        PIANO_TUTOR_PORT: String(BETAPORT),
        PYTHONUTF8: '1',
      },
    }
    backendProc = spawn(bundledExe, [], opts)
  } else {
    const py = pickPythonCommand()
    const args = [
      '-m',
      'uvicorn',
      'backend.app:app',
      '--host',
      '127.0.0.1',
      '--port',
      String(BETAPORT),
    ]
    const opts = {
      cwd,
      shell: true,
      windowsHide: true,
      env: {
        ...process.env,
        PYTHONUTF8: '1',
      },
    }
    backendProc = spawn(py, args, opts)
  }
  backendProc.stderr?.on('data', (d) => {
    const s = d.toString()
    if (s.includes('ERROR') || s.includes('Error')) {
      console.error('[backend]', s)
    }
  })
  backendProc.on('error', (err) => {
    console.error('Failed to start backend:', err)
  })
}

function killBackend() {
  if (!backendProc || backendProc.killed) return
  if (process.platform === 'win32') {
    try {
      spawn('taskkill', ['/PID', String(backendProc.pid), '/T', '/F'], {
        shell: true,
        windowsHide: true,
        detached: true,
      })
    } catch {
      // ignore
    }
  } else {
    try {
      backendProc.kill('SIGTERM')
    } catch {
      // ignore
    }
  }
  backendProc = null
}

function waitForHealth(timeoutMs = 45000) {
  const started = Date.now()
  return new Promise((resolve, reject) => {
    const tryOnce = () => {
      const req = http.get(HEALTH_URL, (res) => {
        res.resume()
        if (res.statusCode === 200) {
          resolve()
          return
        }
        retry()
      })
      req.on('error', () => retry())
      req.setTimeout(2000, () => {
        req.destroy()
        retry()
      })
    }
    const retry = () => {
      if (Date.now() - started > timeoutMs) {
        reject(
          new Error(
            '后端启动超时。若使用安装包：请确认已正确解压且含 piano-backend 文件夹；开发模式请确认已安装 Python 与依赖（见 docs/BETA.md）。'
          )
        )
        return
      }
      setTimeout(tryOnce, 400)
    }
    tryOnce()
  })
}

function joinUrl(base, suffix) {
  const b = String(base || '').replace(/\/+$/, '')
  const s = String(suffix || '').replace(/^\/+/, '')
  if (!b) return `/${s}`
  return `${b}/${s}`
}

/**
 * 使用 Chromium 网络栈（与内置浏览器一致）。在 Windows 上 Node 的 https 偶发与系统代理/Schannel 表现不一致；
 * net.request 对用户「浏览器能开网页」的场景更可靠。
 */
function waitForRemoteHealth(healthUrl, timeoutMs = 35000) {
  const started = Date.now()
  let lastDetail = ''

  return new Promise((resolve, reject) => {
    const scheduleRetry = () => {
      if (Date.now() - started > timeoutMs) {
        reject(
          new Error(
            `无法连接云端 API：${healthUrl}${
              lastDetail ? `\n详情：${lastDetail}` : ''
            }\n请检查网络、系统代理、Nginx 443 与证书；若浏览器能打开同一地址而此处失败，请反馈版本与系统环境。`,
          ),
        )
        return
      }
      setTimeout(tryOnce, 500)
    }

    const tryOnce = () => {
      let settled = false
      const req = net.request({
        method: 'GET',
        url: healthUrl,
      })
      req.setHeader('User-Agent', 'PianoTutorBeta/Electron')
      req.setHeader('Accept', 'application/json, */*;q=0.8')

      const timer = setTimeout(() => {
        if (settled) return
        settled = true
        try {
          req.abort()
        } catch {
          // ignore
        }
        lastDetail = lastDetail || '请求超时'
        scheduleRetry()
      }, 12000)

      const cleanup = () => clearTimeout(timer)

      req.on('response', (res) => {
        res.on('data', () => {})
        res.on('end', () => {
          if (settled) return
          settled = true
          cleanup()
          if (res.statusCode === 200) {
            resolve()
            return
          }
          lastDetail = `HTTP ${res.statusCode}`
          scheduleRetry()
        })
      })
      req.on('error', (err) => {
        if (settled) return
        settled = true
        cleanup()
        lastDetail = String(err?.message || err || '网络错误')
        scheduleRetry()
      })
      req.end()
    }

    tryOnce()
  })
}

function resolveFrontendDistIndex() {
  const backendRoot = getBackendRoot()
  const devRoot = getPianoResourcesDir()
  const distCandidates = [
    path.join(backendRoot, 'frontend', 'dist', 'index.html'),
    path.join(devRoot, 'frontend', 'dist', 'index.html'),
    path.join(devRoot, 'piano', 'frontend', 'dist', 'index.html'),
  ]
  return distCandidates.find((p) => fs.existsSync(p)) || ''
}

function createWindow({ loadLocalDist, distIndexPath }) {
  mainWindow = new BrowserWindow({
    width: 1100,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })
  if (loadLocalDist && distIndexPath) {
    mainWindow.loadFile(distIndexPath)
  } else {
    mainWindow.loadURL(APP_URL)
  }
  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

function dialogParent() {
  if (mainWindow && !mainWindow.isDestroyed()) return mainWindow
  return undefined
}

async function runUpdateCheck(manual) {
  const piano = getPianoResourcesDir()
  const manifestUrl = updateCheck.resolveManifestUrl(piano)
  if (!manifestUrl) {
    if (manual) {
      await dialog.showMessageBox(dialogParent(), {
        type: 'info',
        title: '检查更新',
        message: '未配置更新检查地址',
        detail:
          '发布者可在打包前编辑 desktop/update-config.json 填写 manifestUrl，或设置环境变量 PIANO_UPDATE_MANIFEST_URL（指向 release.json 的 HTTPS 链接）。未配置时不影响正常使用。',
      })
    }
    return
  }

  const userData = app.getPath('userData')
  const state = updateCheck.readState(userData)
  const currentVersion = app.getVersion()
  const result = await updateCheck.checkRemote({
    manifestUrl,
    currentVersion,
    skippedVersion: state.skippedVersion,
    ignoreSkipped: manual,
  })

  if (result.checkFailed) {
    if (manual) {
      await dialog.showMessageBox(dialogParent(), {
        type: 'warning',
        title: '检查更新',
        message: '暂时无法获取版本信息',
        detail: '请检查网络，或稍后在「帮助 → 检查更新」重试。',
      })
    }
    return
  }

  if (!result.hasUpdate) {
    if (manual) {
      await dialog.showMessageBox(dialogParent(), {
        type: 'info',
        title: '检查更新',
        message: '当前已是最新版本',
        detail: `版本：${currentVersion}`,
      })
    }
    return
  }

  if (result.forceUpdate) {
    const hasUrl = Boolean(result.downloadUrl)
    const buttons = hasUrl ? ['前往下载并退出', '退出'] : ['退出']
    const detailParts = []
    if (result.minSupportedVersion) {
      detailParts.push(`该版本已低于最低支持版本 ${result.minSupportedVersion}。`)
    }
    if (result.notes) {
      detailParts.push(result.notes)
    }
    if (hasUrl) {
      detailParts.push(`下载地址：${result.downloadUrl}`)
    }

    const { response } = await dialog.showMessageBox(dialogParent(), {
      type: 'warning',
      title: '需要更新',
      message: `当前版本 ${currentVersion} 已停止支持，请更新后继续使用`,
      detail: detailParts.join('\n\n') || '请联系发布者获取最新版本。',
      buttons,
      defaultId: 0,
      cancelId: buttons.length - 1,
      noLink: true,
    })

    if (hasUrl && response === 0) {
      try {
        await shell.openExternal(result.downloadUrl)
      } catch (e) {
        console.error(e)
      }
    }
    app.quit()
    return
  }

  const hasUrl = Boolean(result.downloadUrl)
  const buttons = hasUrl
    ? ['前往下载', '稍后提醒', '不再提示此版本']
    : ['确定', '不再提示此版本']

  const { response } = await dialog.showMessageBox(dialogParent(), {
    type: 'info',
    title: '发现新版本',
    message: `新版本 ${result.latest} 已发布（当前 ${currentVersion}）`,
    detail: result.notes
      ? result.notes
      : hasUrl
        ? `点击「前往下载」在浏览器中打开下载页。\n${result.downloadUrl}`
        : '请联系发布者获取安装包。',
    buttons,
    defaultId: 0,
    cancelId: hasUrl ? 1 : 0,
  })

  if (hasUrl) {
    if (response === 0) {
      try {
        await shell.openExternal(result.downloadUrl)
      } catch (e) {
        console.error(e)
      }
    }
    if (response === 2) {
      updateCheck.writeState(userData, { skippedVersion: result.latest })
    }
  } else if (response === 1) {
    updateCheck.writeState(userData, { skippedVersion: result.latest })
  }
}

function buildApplicationMenu() {
  const helpSub = [
    {
      label: '检查更新',
      click: async () => {
        try {
          await runUpdateCheck(true)
        } catch (e) {
          console.error(e)
        }
      },
    },
    { type: 'separator' },
    {
      label: `当前版本 ${app.getVersion()}`,
      enabled: false,
    },
  ]

  const template =
    process.platform === 'darwin'
      ? [
          {
            label: app.name,
            submenu: [
              { role: 'about' },
              { type: 'separator' },
              { role: 'services' },
              { type: 'separator' },
              { role: 'hide' },
              { role: 'hideOthers' },
              { role: 'unhide' },
              { type: 'separator' },
              { role: 'quit' },
            ],
          },
          {
            label: '帮助',
            submenu: helpSub,
          },
        ]
      : [
          {
            label: '帮助',
            submenu: helpSub,
          },
        ]

  Menu.setApplicationMenu(Menu.buildFromTemplate(template))
}

app.whenReady().then(async () => {
  const cfg = loadAppRuntimeConfig()
  const mode = effectiveBackendMode(cfg)
  const distIndex = resolveFrontendDistIndex()

  if (!distIndex) {
    const backendRoot = getBackendRoot()
    const devRoot = getPianoResourcesDir()
    await dialog.showMessageBox({
      type: 'error',
      title: 'Piano Tutor Beta',
      message: '未找到前端构建文件',
      detail: `请先执行：npm run beta:build-web 或 npm run beta:build-web:cloud（见 docs/BETA.md）\n期望 index.html 位于：\n${path.join(backendRoot, 'frontend', 'dist')}\n或\n${path.join(devRoot, 'frontend', 'dist')}`,
    })
    app.quit()
    return
  }

  const backendRoot = getBackendRoot()
  try {
    fs.mkdirSync(path.join(backendRoot, 'data', 'scores'), { recursive: true })
    fs.mkdirSync(path.join(backendRoot, 'data', 'practice'), { recursive: true })
  } catch (e) {
    console.error(e)
  }

  if (mode === 'cloud') {
    const base = cfg.cloudPublicApiBase
    if (!base) {
      await dialog.showMessageBox({
        type: 'error',
        title: 'Piano Tutor Beta',
        message: '云端模式未配置 API 地址',
        detail:
          '请在 desktop/app-config.json（或打包后的 resources/piano/app-config.json）中设置 backendMode 为 cloud，并填写 cloudPublicApiBase（HTTPS 根地址，无尾斜杠）。也可设置环境变量 PIANO_BACKEND_MODE=cloud 并保留配置文件中的地址。',
      })
      app.quit()
      return
    }
    const healthUrl = joinUrl(base, '/health')
    try {
      await waitForRemoteHealth(healthUrl)
    } catch (e) {
      await dialog.showMessageBox({
        type: 'error',
        title: 'Piano Tutor Beta',
        message: '无法连接云端服务',
        detail: String(e.message || e),
      })
      app.quit()
      return
    }
    createWindow({ loadLocalDist: true, distIndexPath: distIndex })
  } else {
    const devRoot = getPianoResourcesDir()
    startBackend(devRoot)
    try {
      await waitForHealth()
    } catch (e) {
      killBackend()
      await dialog.showMessageBox({
        type: 'error',
        title: 'Piano Tutor Beta',
        message: '无法连接本地服务',
        detail: String(e.message || e),
      })
      app.quit()
      return
    }
    createWindow({ loadLocalDist: false, distIndexPath: distIndex })
  }

  buildApplicationMenu()

  setTimeout(() => {
    runUpdateCheck(false).catch((e) => console.error('[update-check]', e))
  }, 3000)

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      if (mode === 'cloud') {
        createWindow({ loadLocalDist: true, distIndexPath: distIndex })
      } else {
        createWindow({ loadLocalDist: false, distIndexPath: distIndex })
      }
    }
  })
})

app.on('window-all-closed', () => {
  killBackend()
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', () => {
  killBackend()
})
