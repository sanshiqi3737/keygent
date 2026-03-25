/**
 * 轻量更新检查：拉取远程 JSON，与当前版本比较，弹窗提醒（不自动下载安装包）。
 * 见 docs/release-manifest.example.json
 */
const fs = require('fs')
const path = require('path')
const semver = require('semver')

const FETCH_TIMEOUT_MS = 8000

function statePath(userDataPath) {
  return path.join(userDataPath, 'piano-tutor-beta-update-state.json')
}

function readState(userDataPath) {
  const p = statePath(userDataPath)
  try {
    if (!fs.existsSync(p)) return {}
    return JSON.parse(fs.readFileSync(p, 'utf8'))
  } catch {
    return {}
  }
}

function writeState(userDataPath, patch) {
  const p = statePath(userDataPath)
  const prev = readState(userDataPath)
  const next = { ...prev, ...patch }
  try {
    fs.mkdirSync(path.dirname(p), { recursive: true })
    fs.writeFileSync(p, JSON.stringify(next, null, 2), 'utf8')
  } catch (e) {
    console.error('[update-check] write state failed', e)
  }
}

/**
 * @param {string} pianoResourcesDir 打包后 resources/piano 或开发时项目根
 */
function resolveManifestUrl(pianoResourcesDir) {
  const envUrl = (process.env.PIANO_UPDATE_MANIFEST_URL || '').trim()
  if (envUrl) return envUrl

  const candidates = [
    path.join(pianoResourcesDir, 'update-config.json'),
    path.join(__dirname, 'update-config.json'),
  ]
  for (const p of candidates) {
    try {
      if (!fs.existsSync(p)) continue
      const j = JSON.parse(fs.readFileSync(p, 'utf8'))
      const u = (j.manifestUrl || '').trim()
      if (u) return u
    } catch {
      // ignore
    }
  }
  return ''
}

async function fetchManifest(url) {
  const controller = new AbortController()
  const t = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)
  try {
    const res = await fetch(url, {
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        'User-Agent': 'PianoTutorBeta/1.0',
      },
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return await res.json()
  } finally {
    clearTimeout(t)
  }
}

function pickRemoteVersion(data) {
  const v = data.version || data.latest || data.tag
  return typeof v === 'string' ? v.trim() : ''
}

function pickDownloadUrl(data) {
  const u = data.downloadUrl || data.url || data.zipUrl
  return typeof u === 'string' ? u.trim() : ''
}

function pickMinSupportedVersion(data) {
  const v = data.min_supported_version || data.minSupportedVersion
  return typeof v === 'string' ? v.trim() : ''
}

/**
 * @returns {Promise<{ hasUpdate: boolean, forceUpdate?: boolean, latest?: string, minSupportedVersion?: string, downloadUrl?: string, notes?: string }>}
 */
async function checkRemote({ manifestUrl, currentVersion, skippedVersion, ignoreSkipped }) {
  if (!manifestUrl) return { hasUpdate: false }

  const cur = semver.coerce(currentVersion)
  if (!cur) {
    console.warn('[update-check] invalid current version:', currentVersion)
    return { hasUpdate: false }
  }

  let data
  try {
    data = await fetchManifest(manifestUrl)
  } catch (e) {
    console.warn('[update-check] fetch failed:', e.message || e)
    return { hasUpdate: false, checkFailed: true }
  }

  const latestRaw = pickRemoteVersion(data)
  const latestSemver = semver.coerce(latestRaw)
  if (!latestSemver) {
    console.warn('[update-check] invalid remote version:', latestRaw)
    return { hasUpdate: false }
  }

  const minSupportedRaw = pickMinSupportedVersion(data)
  const minSupportedSemver = semver.coerce(minSupportedRaw)
  const forceUpdate = Boolean(minSupportedSemver && semver.lt(cur, minSupportedSemver))

  // 强制更新优先：即使 latest 解析失败，也可以仅用最低支持版本拦截老客户端。
  if (forceUpdate && !latestSemver) {
    return {
      hasUpdate: true,
      forceUpdate: true,
      minSupportedVersion: minSupportedRaw,
      downloadUrl: pickDownloadUrl(data),
      notes: typeof data.notes === 'string' ? data.notes : typeof data.changelog === 'string' ? data.changelog : '',
    }
  }

  if (!semver.gt(latestSemver, cur)) {
    if (forceUpdate) {
      return {
        hasUpdate: true,
        forceUpdate: true,
        latest: latestRaw,
        minSupportedVersion: minSupportedRaw,
        downloadUrl: pickDownloadUrl(data),
        notes: typeof data.notes === 'string' ? data.notes : typeof data.changelog === 'string' ? data.changelog : '',
      }
    }
    return { hasUpdate: false }
  }

  if (!ignoreSkipped && skippedVersion) {
    const skip = semver.coerce(skippedVersion)
    if (skip && semver.eq(latestSemver, skip)) {
      return { hasUpdate: false }
    }
  }

  const downloadUrl = pickDownloadUrl(data)
  const notes = typeof data.notes === 'string' ? data.notes : typeof data.changelog === 'string' ? data.changelog : ''

  return {
    hasUpdate: true,
    forceUpdate,
    latest: latestRaw,
    minSupportedVersion: minSupportedRaw || undefined,
    downloadUrl,
    notes,
  }
}

module.exports = {
  resolveManifestUrl,
  checkRemote,
  readState,
  writeState,
}
