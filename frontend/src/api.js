function normalizeBase(base) {
  const raw = String(base || '').trim()
  if (!raw) return ''
  return raw.replace(/\/+$/, '')
}

function joinBase(base, path) {
  const safePath = String(path || '')
  if (!base) return safePath
  return `${base}${safePath}`
}

const PUBLIC_API_BASE = normalizeBase(import.meta.env.VITE_PUBLIC_API_BASE || import.meta.env.VITE_API_BASE)
const API_BASE = joinBase(PUBLIC_API_BASE, '/api/score')
const AUTH_BASE = joinBase(PUBLIC_API_BASE, '/api/auth')
const PRACTICE_BASE = joinBase(PUBLIC_API_BASE, '/api/practice')
const ASSISTANT_BASE = joinBase(PUBLIC_API_BASE, '/api/assistant')
const ADMIN_API_BASE = String(import.meta.env.VITE_ADMIN_API_BASE || '').trim()
let authToken = ''

export async function checkBackendHealth() {
  const healthUrl = joinBase(PUBLIC_API_BASE, '/health') || '/health'
  try {
    const r = await fetch(healthUrl, { method: 'GET' })
    return r.ok
  } catch {
    return false
  }
}

export async function checkAdminHealth() {
  const base = normalizeBase(ADMIN_API_BASE)
  if (!base) return null
  try {
    const r = await fetch(`${base}/health`, { method: 'GET' })
    return r.ok
  } catch {
    return false
  }
}

export function getApiTargets() {
  return {
    publicApiBase: PUBLIC_API_BASE || '(same-origin/proxy)',
    adminApiBase: normalizeBase(ADMIN_API_BASE) || '',
  }
}

export function setAuthToken(token) {
  authToken = String(token || '').trim()
}

function withAuthHeaders(base = {}) {
  if (!authToken) return base
  return { ...base, Authorization: `Bearer ${authToken}` }
}

function adminApiUrl(path) {
  if (!ADMIN_API_BASE) return path
  return `${ADMIN_API_BASE}${path}`
}

function formatApiDetail(detail) {
  if (detail == null) return ''
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail))
    return detail.map((x) => (x && x.msg) || JSON.stringify(x)).join('；')
  return String(detail)
}

export async function authRegister(account, password) {
  const r = await fetch(`${AUTH_BASE}/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      account: String(account || '').trim(),
      password: String(password || ''),
    }),
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    throw new Error(formatApiDetail(err.detail) || '注册失败')
  }
  return r.json()
}

export async function authLogin(account, password) {
  const r = await fetch(`${AUTH_BASE}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      account: String(account || '').trim(),
      password: String(password || ''),
    }),
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    throw new Error(formatApiDetail(err.detail) || '登录失败')
  }
  return r.json()
}

export async function authMe(token) {
  const r = await fetch(`${AUTH_BASE}/me`, {
    headers: { Authorization: `Bearer ${String(token || '')}` },
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    throw new Error(formatApiDetail(err.detail) || '登录状态无效')
  }
  return r.json()
}

export async function authLogout(token) {
  const r = await fetch(`${AUTH_BASE}/logout`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${String(token || '')}` },
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    throw new Error(formatApiDetail(err.detail) || '退出失败')
  }
  return r.json()
}

export async function uploadScore(pdfFile, musicxmlFile, title = '') {
  const form = new FormData()
  form.append('pdf', pdfFile)
  form.append('musicxml', musicxmlFile)
  if (String(title || '').trim()) form.append('title', String(title).trim())
  const r = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    headers: withAuthHeaders(),
    body: form,
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    throw new Error(err.detail || '上传失败')
  }
  return r.json()
}

export async function getScoreTechniques(scoreId) {
  const r = await fetch(`${API_BASE}/${scoreId}/techniques`)
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    throw new Error(err.detail || '获取技巧失败')
  }
  return r.json()
}

export async function getScoreInfo(scoreId) {
  const r = await fetch(`${API_BASE}/${scoreId}/info`)
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    throw new Error(err.detail || '获取乐谱信息失败')
  }
  return r.json()
}

export function getScoreImageUrl(scoreId, page = 1) {
  return `${API_BASE}/${scoreId}/image?page=${Number(page) || 1}`
}

export async function getScoreMeta(scoreId) {
  const r = await fetch(`${API_BASE}/${scoreId}/meta`)
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    throw new Error(err.detail || '获取曲目画像失败')
  }
  return r.json()
}

export async function listScores({
  q = '',
  difficulty = '',
  ability = '',
  limit = 200,
  includeMeta = true,
} = {}) {
  const params = new URLSearchParams({
    limit: String(Math.max(1, Number(limit) || 200)),
    include_meta: includeMeta ? 'true' : 'false',
  })
  if (String(q || '').trim()) params.set('q', String(q).trim())
  if (String(difficulty || '').trim()) params.set('difficulty', String(difficulty).trim())
  if (String(ability || '').trim()) params.set('ability', String(ability).trim())
  const r = await fetch(`${API_BASE}/list?${params}`)
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    throw new Error(err.detail || '获取曲库列表失败')
  }
  return r.json()
}

export async function deleteScore(scoreId, adminToken = '') {
  const headers = withAuthHeaders()
  if (adminToken) headers['X-Admin-Token'] = String(adminToken)
  const r = await fetch(`${API_BASE}/${scoreId}`, { method: 'DELETE', headers })
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    throw new Error(err.detail || '删除曲目失败')
  }
  return r.json()
}

export async function deleteScoresBatch(scoreIds = [], adminToken = '') {
  const headers = withAuthHeaders({ 'Content-Type': 'application/json' })
  if (adminToken) headers['X-Admin-Token'] = String(adminToken)
  const r = await fetch(`${API_BASE}/delete-batch`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ score_ids: scoreIds }),
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    throw new Error(err.detail || '批量删除失败')
  }
  return r.json()
}

export async function assessAllScores({ useLlm = true, limit = 200 } = {}) {
  const params = new URLSearchParams({
    use_llm: useLlm ? 'true' : 'false',
    limit: String(Math.max(1, Number(limit) || 200)),
  })
  const r = await fetch(`${API_BASE}/assess-all?${params}`, { method: 'POST' })
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    throw new Error(err.detail || '批量重评估失败')
  }
  return r.json()
}

export async function compareWithScore(
  scoreId,
  audioFile,
  useMultipitch = false,
  includeNoteSnapshots = false,
  startMeasure = null,
  endMeasure = null,
  compareMode = 'beginner_pitch_only'
) {
  const form = new FormData()
  form.append('audio', audioFile)
  const params = new URLSearchParams()
  // Always send explicit mode to avoid backend default ambiguity
  params.set('use_multipitch', useMultipitch ? 'true' : 'false')
  if (includeNoteSnapshots) params.set('include_note_snapshots', 'true')
  if (startMeasure) params.set('start_measure', String(startMeasure))
  if (endMeasure) params.set('end_measure', String(endMeasure))
  if (compareMode) params.set('compare_mode', String(compareMode))
  const qs = params.toString() ? '?' + params.toString() : ''
  const r = await fetch(`${API_BASE}/${scoreId}/compare${qs}`, {
    method: 'POST',
    headers: withAuthHeaders(),
    body: form,
  })
  if (!r.ok) {
    const err = await r
      .json()
      .catch(async () => ({ detail: (await r.text().catch(() => '')) || r.statusText }))
    throw new Error(formatApiDetail(err.detail) || `比对失败（HTTP ${r.status}）`)
  }
  return r.json()
}

/** 独立练习记录接口（与比对解耦）；需先 includeNoteSnapshots 比对拿到音符快照，或仅传 accuracy/errors 存最小指标 */
export async function submitPracticeSession(payload) {
  const r = await fetch(`${PRACTICE_BASE}/sessions`, {
    method: 'POST',
    headers: withAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    throw new Error(err.detail || '保存练习记录失败')
  }
  return r.json()
}

export async function getPracticeSessions(userId = 'default', limit = 20, scoreId = null) {
  const params = new URLSearchParams({ limit: String(limit) })
  if (scoreId) params.set('score_id', scoreId)
  const r = await fetch(`${PRACTICE_BASE}/sessions?${params}`, {
    headers: withAuthHeaders(),
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    throw new Error(err.detail || '获取练习记录失败')
  }
  return r.json()
}

export async function deletePracticeSessionAudio(sessionId) {
  const r = await fetch(`${PRACTICE_BASE}/sessions/${encodeURIComponent(String(sessionId || ''))}/audio`, {
    method: 'DELETE',
    headers: withAuthHeaders(),
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    throw new Error(err.detail || '删除练习音频失败')
  }
  return r.json()
}

export async function deletePracticeAudioBatch(sessionIds = []) {
  const r = await fetch(`${PRACTICE_BASE}/audio/delete-batch`, {
    method: 'POST',
    headers: withAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ session_ids: sessionIds }),
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    throw new Error(err.detail || '批量删除练习音频失败')
  }
  return r.json()
}

export async function getPracticeUsers(limit = 100) {
  const params = new URLSearchParams({ limit: String(Math.max(1, Number(limit) || 100)) })
  const r = await fetch(`${PRACTICE_BASE}/users?${params}`)
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    throw new Error(err.detail || '获取用户列表失败')
  }
  return r.json()
}

export async function adminAuth(passcode) {
  const r = await fetch(adminApiUrl('/api/admin/auth'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ passcode: String(passcode || '') }),
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    throw new Error(err.detail || '管理口令验证失败')
  }
  return r.json()
}

export async function getAdminUsersOverview(adminToken, limit = 50) {
  const params = new URLSearchParams({ limit: String(Math.max(1, Number(limit) || 50)) })
  const r = await fetch(adminApiUrl(`/api/admin/users-overview?${params}`), {
    headers: { 'X-Admin-Token': String(adminToken || '') },
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    throw new Error(err.detail || '获取管理总览失败')
  }
  return r.json()
}

export async function getAdminRuntimeConfig(adminToken) {
  const r = await fetch(adminApiUrl('/api/admin/runtime-config'), {
    headers: { 'X-Admin-Token': String(adminToken || '') },
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    throw new Error(err.detail || '获取运行时配置失败')
  }
  return r.json()
}

export async function updateAdminRuntimeConfig(adminToken, { assistantModel }) {
  const r = await fetch(adminApiUrl('/api/admin/runtime-config'), {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'X-Admin-Token': String(adminToken || ''),
    },
    body: JSON.stringify({
      assistant_model: String(assistantModel || '').trim(),
    }),
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    throw new Error(err.detail || '更新运行时配置失败')
  }
  return r.json()
}

/** 最近 N 次练习聚合（准确率、错误、节奏、薄弱小节 Top） */
export async function getPracticeSummary(userId = 'default', { scoreId = null, lastN = 30 } = {}) {
  const params = new URLSearchParams({ last_n: String(lastN) })
  if (scoreId) params.set('score_id', scoreId)
  const r = await fetch(`/api/practice/summary?${params}`, {
    headers: withAuthHeaders(),
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    throw new Error(err.detail || '获取练习概况失败')
  }
  return r.json()
}

/** 阿里云百炼：根据练习概况生成中文建议（需后端配置 DASHSCOPE_API_KEY） */
export async function suggestAssistant({ userId = 'default', scoreId = null, lastN = 20 } = {}) {
  const r = await fetch(`${ASSISTANT_BASE}/suggest`, {
    method: 'POST',
    headers: withAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      score_id: scoreId || null,
      last_n: lastN,
    }),
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    const d = err.detail
    throw new Error(typeof d === 'string' ? d : JSON.stringify(d) || '智能建议请求失败')
  }
  return r.json()
}

export async function getAssistantThread({ userId = 'default', limit = 40 } = {}) {
  const params = new URLSearchParams({
    limit: String(Math.max(1, Number(limit) || 40)),
  })
  const r = await fetch(`${ASSISTANT_BASE}/thread?${params}`, {
    headers: withAuthHeaders(),
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    const d = err.detail
    throw new Error(typeof d === 'string' ? d : JSON.stringify(d) || '获取助手会话失败')
  }
  return r.json()
}

export async function sendAssistantMessage({
  userId = 'default',
  content,
  scoreId = null,
  lastN = 20,
} = {}) {
  const r = await fetch(`${ASSISTANT_BASE}/message`, {
    method: 'POST',
    headers: withAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      content: String(content || ''),
      score_id: scoreId || null,
      last_n: Math.max(1, Number(lastN) || 20),
    }),
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    const d = err.detail
    throw new Error(typeof d === 'string' ? d : JSON.stringify(d) || '发送消息失败')
  }
  return r.json()
}

/** 阶段3：生成今日任务单（仅生成与展示） */
export async function getTodayPlan({ userId = 'default', scoreId = null, lastN = 20 } = {}) {
  const r = await fetch(`${PRACTICE_BASE}/today-plan`, {
    method: 'POST',
    headers: withAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      score_id: scoreId || null,
      last_n: Math.max(1, Number(lastN) || 20),
    }),
  })
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    const d = err.detail
    throw new Error(typeof d === 'string' ? d : JSON.stringify(d) || '生成今日任务单失败')
  }
  return r.json()
}
