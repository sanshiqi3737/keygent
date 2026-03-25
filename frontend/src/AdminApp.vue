<template>
  <div class="wrap">
    <header class="card">
      <h1>开发者管理端</h1>
      <p class="muted">
        当前 admin API:
        <code>{{ adminApiBase || '(同源 /api/admin)' }}</code>
      </p>
    </header>

    <section class="card">
      <h2>管理员登录</h2>
      <div class="row">
        <input v-model="passcode" type="password" class="input" placeholder="输入 ADMIN_PASSCODE" />
        <button class="btn" :disabled="authLoading" @click="loginAdmin">
          {{ authLoading ? '验证中…' : '登录' }}
        </button>
        <button class="btn" :disabled="!adminToken" @click="logoutAdmin">退出</button>
      </div>
      <p v-if="authError" class="err">{{ authError }}</p>
      <p v-else-if="adminToken" class="ok">已登录开发者平台</p>
    </section>

    <section class="card">
      <h2>助手模型切换</h2>
      <div class="row">
        <input
          v-model="assistantModel"
          class="input"
          :disabled="!adminToken || runtimeLoading"
          placeholder="如 qwen-turbo / qwen-plus"
        />
        <button class="btn" :disabled="!adminToken || runtimeLoading" @click="loadRuntime">
          刷新
        </button>
        <button class="btn" :disabled="!adminToken || runtimeLoading" @click="saveRuntime">
          {{ runtimeLoading ? '保存中…' : '保存' }}
        </button>
      </div>
      <p v-if="runtimeError" class="err">{{ runtimeError }}</p>
    </section>

    <section class="card">
      <h2>用户状态总览</h2>
      <div class="row">
        <button class="btn" :disabled="!adminToken || usersLoading" @click="loadUsers">
          {{ usersLoading ? '加载中…' : '刷新总览' }}
        </button>
      </div>
      <p v-if="usersError" class="err">{{ usersError }}</p>
      <table v-else-if="rows.length" class="tbl">
        <thead>
          <tr>
            <th>用户ID</th>
            <th>会话数</th>
            <th>准确率均值</th>
            <th>最近练习时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.user_id">
            <td>{{ r.user_id }}</td>
            <td>{{ r.sessions }}</td>
            <td>{{ r.accuracy_mean != null ? `${(r.accuracy_mean * 100).toFixed(1)}%` : '-' }}</td>
            <td>{{ r.latest_session_at || '-' }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else class="muted">暂无数据</p>
    </section>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import {
  adminAuth,
  getAdminUsersOverview,
  getAdminRuntimeConfig,
  updateAdminRuntimeConfig,
} from './api.js'

const adminApiBase = String(import.meta.env.VITE_ADMIN_API_BASE || '').trim()

const passcode = ref('')
const adminToken = ref('')
const authLoading = ref(false)
const authError = ref('')

const assistantModel = ref('')
const runtimeLoading = ref(false)
const runtimeError = ref('')

const rows = ref([])
const usersLoading = ref(false)
const usersError = ref('')

function handleAuthExpired(msg) {
  const s = String(msg || '')
  if (s.includes('403') || s.includes('鉴权')) {
    adminToken.value = ''
    localStorage.removeItem('dev_admin_token')
    authError.value = '管理员会话已失效，请重新登录'
    return true
  }
  return false
}

async function loginAdmin() {
  authLoading.value = true
  authError.value = ''
  try {
    const res = await adminAuth(passcode.value)
    adminToken.value = res.token || ''
    localStorage.setItem('dev_admin_token', adminToken.value)
    passcode.value = ''
    await loadRuntime()
    await loadUsers()
  } catch (e) {
    authError.value = String(e?.message || '登录失败')
  } finally {
    authLoading.value = false
  }
}

function logoutAdmin() {
  adminToken.value = ''
  rows.value = []
  localStorage.removeItem('dev_admin_token')
}

async function loadRuntime() {
  if (!adminToken.value) return
  runtimeLoading.value = true
  runtimeError.value = ''
  try {
    const res = await getAdminRuntimeConfig(adminToken.value)
    assistantModel.value = String(res.assistant_model || '')
  } catch (e) {
    if (!handleAuthExpired(e?.message)) runtimeError.value = String(e?.message || '读取失败')
  } finally {
    runtimeLoading.value = false
  }
}

async function saveRuntime() {
  if (!adminToken.value) return
  runtimeLoading.value = true
  runtimeError.value = ''
  try {
    await updateAdminRuntimeConfig(adminToken.value, { assistantModel: assistantModel.value })
  } catch (e) {
    if (!handleAuthExpired(e?.message)) runtimeError.value = String(e?.message || '保存失败')
  } finally {
    runtimeLoading.value = false
  }
}

async function loadUsers() {
  if (!adminToken.value) return
  usersLoading.value = true
  usersError.value = ''
  try {
    const res = await getAdminUsersOverview(adminToken.value, 100)
    rows.value = Array.isArray(res.rows) ? res.rows : []
  } catch (e) {
    if (!handleAuthExpired(e?.message)) usersError.value = String(e?.message || '加载失败')
  } finally {
    usersLoading.value = false
  }
}

;(function init() {
  const t = localStorage.getItem('dev_admin_token')
  if (t && t.trim()) {
    adminToken.value = t.trim()
    loadRuntime()
    loadUsers()
  }
})()
</script>

<style scoped>
.wrap { max-width: 980px; margin: 0 auto; padding: 16px; font-family: sans-serif; }
.card { border: 1px solid #ddd; border-radius: 10px; padding: 14px; margin-bottom: 12px; background: #fff; }
.row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.input { min-width: 280px; padding: 8px; border: 1px solid #ccc; border-radius: 6px; }
.btn { padding: 8px 12px; border: 1px solid #3b82f6; border-radius: 6px; background: #3b82f6; color: #fff; cursor: pointer; }
.btn:disabled { opacity: .55; cursor: not-allowed; }
.muted { color: #666; }
.err { color: #b42318; }
.ok { color: #067647; }
.tbl { width: 100%; border-collapse: collapse; margin-top: 8px; }
.tbl th, .tbl td { border-bottom: 1px solid #eee; text-align: left; padding: 8px; font-size: 14px; }
</style>

