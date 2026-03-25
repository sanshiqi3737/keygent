<template>
  <div class="app">
    <header class="header">
      <h1>钢琴陪练 · 标准乐谱</h1>
      <p class="sub">上传 PDF + MusicXML，展示乐谱并与弹奏比对</p>
      <p v-if="!backendOnline" class="error">后端连接异常：{{ backendStatusText }}</p>
      <div class="nav-row">
        <button type="button" class="btn small" @click="goApp">用户端</button>
        <button
          v-if="scoreId"
          type="button"
          class="btn small"
          @click="goScore(scoreId)"
        >
          当前曲目页
        </button>
        <span class="muted nav-tip">当前路由：{{ routePathLabel }}</span>
      </div>
    </header>

    <main class="main">
      <section v-if="routeMode === 'app' && (appTab === 'home' || appTab === 'profile')" class="card">
        <h2>用户入口</h2>
        <div class="inline-row">
          <strong>当前账号：</strong>
          <code>{{ currentAccount || '未登录' }}</code>
          <strong style="margin-left: 1rem">用户ID：</strong>
          <code>{{ currentUserId }}</code>
          <span class="muted">（按账号隔离练习记录与助手记忆）</span>
        </div>
        <div class="inline-row" style="margin-top: 0.6rem; flex-wrap: wrap">
          <input v-model="authAccountInput" class="score-id-input" placeholder="账号（建议邮箱）" />
          <input v-model="authPasswordInput" class="score-id-input" type="password" placeholder="密码（至少6位）" />
          <button type="button" class="btn small" :disabled="authLoading" @click="doLogin">
            {{ authLoading ? '处理中…' : '登录' }}
          </button>
          <button type="button" class="btn small" :disabled="authLoading" @click="doRegister">
            {{ authLoading ? '处理中…' : '注册' }}
          </button>
          <button type="button" class="btn small" :disabled="authLoading || !authToken" @click="doLogout">
            退出登录
          </button>
        </div>
        <p v-if="authError" class="error">{{ authError }}</p>
      </section>

      <section v-if="routeMode === 'app' && appTab === 'home'" class="card">
        <h2>首页</h2>
        <p class="muted small-margin">欢迎使用钢琴陪练。你可以从下方标签快速进入曲库、练习、助手和我的页面。</p>
        <div class="inline-row">
          <button type="button" class="btn small" @click="goAppTab('library')">去曲库</button>
          <button type="button" class="btn small" @click="goAppTab('practice')">去练习</button>
          <button type="button" class="btn small" @click="goAppTab('assistant')">去助手</button>
          <button type="button" class="btn small" @click="goAppTab('profile')">去我的</button>
        </div>
      </section>

      <section v-if="routeMode === 'app' && appTab === 'home'" class="card">
        <h2>启动自检清单</h2>
        <div class="inline-row" style="margin-bottom: 0.6rem">
          <button type="button" class="btn small" :disabled="startupChecking" @click="runStartupChecklist">
            {{ startupChecking ? '检查中…' : '重新检查' }}
          </button>
        </div>
        <ul class="startup-check-list">
          <li>
            <strong>后端连接</strong>
            <span :class="startupStatus.backendOk ? 'success' : 'error'">
              {{ startupStatus.backendOk ? '正常' : '异常' }}
            </span>
          </li>
          <li>
            <strong>登录状态</strong>
            <span :class="startupStatus.loggedIn ? 'success' : 'muted'">
              {{ startupStatus.loggedIn ? '已登录' : '未登录（可继续浏览）' }}
            </span>
          </li>
          <li>
            <strong>管理端地址</strong>
            <span class="muted">
              {{ startupStatus.adminApiBase || '未配置（本机可不配）' }}
            </span>
          </li>
          <li v-if="startupStatus.adminApiBase">
            <strong>管理端连通</strong>
            <span :class="startupStatus.adminReachable ? 'success' : 'error'">
              {{ startupStatus.adminReachable ? '正常' : '不可达' }}
            </span>
          </li>
          <li>
            <strong>用户端 API 目标</strong>
            <span class="muted">{{ startupStatus.publicApiBase }}</span>
          </li>
        </ul>
        <p v-if="startupChecklistError" class="error">{{ startupChecklistError }}</p>
      </section>

      <section v-if="routeMode === 'app' && appTab === 'library'" class="card library-section">
        <h2>0. 曲目入口（谱库页骨架）</h2>
        <p class="muted small-margin">
          先用轻量路由骨架模拟“谱库 -> 曲目页”。后续接大谱库时可直接替换此入口。
        </p>
        <div class="inline-row">
          <input
            v-model="manualScoreId"
            class="score-id-input"
            placeholder="输入 score_id 后进入曲目页"
          />
          <button type="button" class="btn small" @click="openScoreFromInput">
            进入曲目页
          </button>
          <button type="button" class="btn small" :disabled="scoreLibraryLoading" @click="loadScoreLibrary(manualScoreId)">
            {{ scoreLibraryLoading ? '搜索中…' : '搜索曲库' }}
          </button>
        </div>
        <div class="inline-row" style="margin-top: 0.6rem">
          <label class="muted">难度</label>
          <select v-model="scoreFilterDifficulty" class="score-id-input" style="max-width: 180px">
            <option value="">全部</option>
            <option v-for="d in difficultyOptions" :key="d" :value="d">{{ d }}</option>
          </select>
          <input
            v-model="scoreFilterAbility"
            class="score-id-input"
            style="max-width: 260px"
            placeholder="能力标签，如 rhythm_control"
          />
          <button type="button" class="btn small" :disabled="scoreLibraryLoading" @click="loadScoreLibrary(manualScoreId)">
            应用筛选
          </button>
        </div>
        <p v-if="scoreLibraryError" class="error">{{ scoreLibraryError }}</p>
        <div class="recent-list" style="margin-top: 0.75rem">
          <strong>曲库列表（{{ scoreLibraryRows.length }}）</strong>
          <p v-if="scoreLibraryLoading" class="muted">加载曲库中…</p>
          <div v-else-if="scoreLibraryRows.length">
            <div class="inline-row" style="margin-top: 0.4rem; margin-bottom: 0.6rem">
              <label class="checkbox-label">
                <input
                  type="checkbox"
                  :checked="selectedLibraryScoreIds.length === scoreLibraryRows.length"
                  @change="toggleSelectAllScores($event.target.checked)"
                />
                全选
              </label>
              <button
                type="button"
                class="btn small"
                :disabled="batchDeleting || !selectedLibraryScoreIds.length"
                @click="deleteSelectedScores"
              >
                {{ batchDeleting ? '批量删除中…' : `批量删除(${selectedLibraryScoreIds.length})` }}
              </button>
            </div>
            <div
              v-for="r in scoreLibraryRows.slice(0, 30)"
              :key="r.score_id"
              class="inline-row"
              style="margin-bottom: 0.35rem"
            >
              <label class="checkbox-label">
                <input
                  type="checkbox"
                  :checked="selectedLibraryScoreIds.includes(r.score_id)"
                  @change="toggleScoreSelection(r.score_id, $event.target.checked)"
                />
              </label>
              <button type="button" class="btn small" @click="goScore(r.score_id)">
                {{ scoreDisplayNameByRow(r) }}
              </button>
              <button
                type="button"
                class="btn small"
                :disabled="deletingScoreId === r.score_id || batchDeleting"
                @click="deleteOneScore(r.score_id)"
              >
                {{ deletingScoreId === r.score_id ? '删除中…' : '删除' }}
              </button>
            </div>
          </div>
          <p v-else class="muted">曲库为空，请先上传曲目。</p>
        </div>
        <div v-if="recentScores.length" class="recent-list">
          <strong>最近曲目</strong>
          <div class="inline-row">
            <div
              v-for="sid in recentScores"
              :key="sid"
              class="recent-item"
            >
              <button
                type="button"
                class="btn small recent-item-main"
                @click="goScore(sid)"
              >
                {{ scoreDisplayNameById(sid) }}
              </button>
              <button
                type="button"
                class="recent-item-close"
                title="从最近曲目移除"
                @click="removeRecentScore(sid)"
              >
                ×
              </button>
            </div>
          </div>
        </div>
        <div class="form-row inline-row" style="margin-top: 0.75rem">
          <button type="button" class="btn small" :disabled="reassessAllLoading" @click="runAssessAllScores">
            {{ reassessAllLoading ? '批量评估中…' : '一键批量重评估旧曲目' }}
          </button>
          <span v-if="reassessAllResult" class="muted">
            已处理 {{ reassessAllResult.processed_count }} 首，跳过 {{ reassessAllResult.skipped_count }} 首
          </span>
        </div>
        <p v-if="reassessAllError" class="error">{{ reassessAllError }}</p>
      </section>

      <!-- 上传 -->
      <section v-if="routeMode === 'app' && appTab === 'library'" class="card upload-section">
        <h2>1. 上传标准乐谱（加入曲库）</h2>
        <div class="form-row">
          <label>曲目名称（可选）</label>
          <input
            v-model="uploadTitle"
            class="score-id-input"
            placeholder="例如：小星星 练习版"
          />
        </div>
        <div class="form-row">
          <label>PDF（乐谱图）<span class="req">*</span></label>
          <input type="file" accept=".pdf" @change="pdfFile = $event.target.files?.[0]" />
        </div>
        <div class="form-row">
          <label>MusicXML（标准答案）<span class="req">*</span></label>
          <input type="file" accept=".musicxml,.xml,.mxl" @change="musicxmlFile = $event.target.files?.[0]" />
        </div>
        <button class="btn primary" :disabled="uploading || !pdfFile || !musicxmlFile" @click="doUpload">
          {{ uploading ? '上传中…' : '上传到曲库' }}
        </button>
        <p v-if="uploadError" class="error">{{ uploadError }}</p>
        <p v-if="scoreId" class="success">已加载曲目：{{ currentScoreDisplayName }}</p>
      </section>

      <section
        v-if="routeMode === 'app' && scoreId && (appTab === 'library' || appTab === 'practice')"
        class="card score-page-section"
      >
        <h2>乐谱页 · {{ currentScoreDisplayName }}</h2>
        <div class="inline-row">
          <button type="button" class="btn small" :disabled="scorePage <= 1" @click="scorePage--">上一页</button>
          <span>第 {{ scorePage }} / {{ scorePageCount || '?' }} 页</span>
          <button
            type="button"
            class="btn small"
            :disabled="scorePageCount > 0 && scorePage >= scorePageCount"
            @click="scorePage++"
          >
            下一页
          </button>
        </div>
        <p v-if="scoreImageError" class="error">{{ scoreImageError }}</p>
        <img
          v-else
          class="score-image"
          :src="scoreImageSrc"
          alt="score page"
          @error="handleScoreImageError"
        />
        <div class="score-meta-box">
          <p><strong>曲目画像</strong></p>
          <p v-if="scoreMetaLoading" class="muted">加载中…</p>
          <p v-else-if="scoreMetaError" class="error">{{ scoreMetaError }}</p>
          <template v-else-if="scoreMeta">
            <p><strong>标题：</strong>{{ scoreMeta.title || '未命名' }}</p>
            <p><strong>难度：</strong>{{ scoreMeta.difficulty || 'unknown' }}</p>
            <p v-if="scoreMeta.abilities?.length"><strong>训练能力：</strong>{{ scoreMeta.abilities.join('、') }}</p>
            <p v-if="scoreMeta.assessment?.reason" class="muted">依据：{{ scoreMeta.assessment.reason }}</p>
          </template>
          <p v-else class="muted">暂无画像，请先手动评估或批量重评估。</p>
        </div>
      </section>

      <section v-if="routeMode === 'app' && appTab === 'practice'" class="card">
        <h2>1. 选择练习曲目（搜索曲库）</h2>
        <p class="muted small-margin">已接入后端曲库接口，可按关键词 + 难度 + 能力标签筛选。</p>
        <div class="inline-row">
          <input
            v-model="practiceScoreQuery"
            class="score-id-input"
            placeholder="输入曲名关键词搜索"
          />
          <button type="button" class="btn small" @click="selectPracticeScore(practiceScoreQuery)">设为当前练习曲目</button>
          <button type="button" class="btn small" :disabled="scoreLibraryLoading" @click="loadScoreLibrary(practiceScoreQuery)">
            {{ scoreLibraryLoading ? '搜索中…' : '搜索曲库' }}
          </button>
        </div>
        <div class="inline-row" style="margin-top: 0.6rem">
          <label class="muted">难度</label>
          <select v-model="scoreFilterDifficulty" class="score-id-input" style="max-width: 180px">
            <option value="">全部</option>
            <option v-for="d in difficultyOptions" :key="d" :value="d">{{ d }}</option>
          </select>
          <input
            v-model="scoreFilterAbility"
            class="score-id-input"
            style="max-width: 260px"
            placeholder="能力标签，如 rhythm_control"
          />
        </div>
        <p v-if="scoreLibraryError" class="error">{{ scoreLibraryError }}</p>
        <div class="recent-list" style="margin-top: 0.75rem">
          <strong>曲目库（{{ practiceScoreCandidates.length }}）</strong>
          <p v-if="scoreLibraryLoading" class="muted">加载曲库中…</p>
          <div class="inline-row" v-if="practiceScoreCandidates.length">
            <button
              v-for="item in practiceScoreCandidates"
              :key="item.score_id"
              type="button"
              class="btn small"
              @click="selectPracticeScore(item.score_id)"
            >
              {{ item.title }}
            </button>
          </div>
          <p v-else class="muted">暂无匹配曲目。先去曲库页上传或打开过曲目后，这里会显示。</p>
        </div>
      </section>

      <!-- 本曲技巧 -->
      <section v-if="routeMode === 'app' && appTab === 'practice' && scoreId" class="card techniques-section">
        <h2>2. 本曲技巧</h2>
        <p v-if="techniquesLoading" class="muted">正在解析乐谱技巧…</p>
        <p v-else-if="techniquesError" class="error">{{ techniquesError }}</p>
        <template v-else-if="techniques">
          <div class="technique-summary">
            <p class="summary-line">共解析到以下技巧：</p>
            <ul class="technique-counts">
              <li v-for="(count, type) in techniques.counts" :key="type">
                <strong>{{ techniqueLabel(type) }}</strong> {{ count }} 处
              </li>
            </ul>
            <p v-if="Object.keys(techniques.counts).length === 0" class="muted">该乐谱中未解析到触键/力度等标记。</p>
          </div>
          <details v-if="techniques.events && techniques.events.length" class="technique-detail">
            <summary>查看全部 {{ techniques.events.length }} 条技巧明细</summary>
            <ul class="technique-events">
              <li v-for="(e, i) in techniques.events" :key="i">
                <span v-if="e.measure != null">第{{ e.measure }}小节</span>
                <span v-if="e.beat != null"> 第{{ e.beat }}拍</span>
                <span v-if="e.note_name"> {{ e.note_name }}</span>
                <span class="tech-name">{{ e.name_cn || e.type }}</span>
              </li>
            </ul>
          </details>
        </template>
      </section>

      <!-- 比对 -->
      <section v-if="routeMode === 'app' && appTab === 'practice'" class="card compare-section">
        <h2>3. 上传弹奏并比对</h2>
        <div class="form-row">
          <label>你的弹奏（录音 wav/mp3… 或 MIDI .mid/.midi）</label>
          <input
            type="file"
            accept="audio/*,.wav,.mp3,.flac,.ogg,.mid,.midi"
            @change="audioFile = $event.target.files?.[0]"
          />
        </div>
        <div class="form-row">
          <label>练习模式</label>
          <div class="inline-row">
            <label class="checkbox-label">
              <input type="radio" value="beginner_pitch_only" v-model="compareMode" />
              初级（仅看音准，弱化节奏影响）
            </label>
            <label class="checkbox-label">
              <input type="radio" value="advanced_rhythm" v-model="compareMode" />
              高级（音准 + 节奏）
            </label>
          </div>
        </div>
        <div class="form-row">
          <label class="checkbox-label">
            <input type="checkbox" v-model="useMultipitch" />
            多声部检测（和弦/双手，更准确但需额外依赖）
          </label>
        </div>
        <div class="form-row">
          <label class="checkbox-label">
            <input type="checkbox" v-model="persistSession" />
            保存练习记录（供成长轨迹与智能体使用）
          </label>
        </div>
        <div class="form-row">
          <label>本次仅练习小节（可选，留空=全曲；会影响智能助手建议）</label>
          <div class="inline-row">
            <input
              v-model="focusStartMeasure"
              type="number"
              min="1"
              class="input-narrow"
              placeholder="起"
            />
            <span class="muted">到</span>
            <input
              v-model="focusEndMeasure"
              type="number"
              min="1"
              class="input-narrow"
              placeholder="止"
            />
          </div>
        </div>
        <button
          class="btn primary"
          :disabled="comparing || !scoreId || !audioFile"
          @click="doCompare"
        >
          {{ comparing ? '比对中…' : '开始比对' }}
        </button>
        <p v-if="compareError" class="error">{{ compareError }}</p>
        <div v-if="compareResult" class="result-box">
          <p><strong>准确率：</strong>{{ (compareResult.accuracy * 100).toFixed(1) }}%</p>
          <p><strong>错音数：</strong>{{ compareResult.errors.length }}</p>
          <p v-if="compareResult.session_id" class="success">已保存练习记录 (ID: {{ compareResult.session_id }})</p>
          <p v-if="compareResult.metrics?.rhythm?.available && compareResult.metrics.rhythm.score != null" class="muted">
            节奏得分：{{ (compareResult.metrics.rhythm.score * 100).toFixed(1) }}%
            <span v-if="compareResult.metrics.rhythm.std_abs_onset_ms != null">
              · 起音偏差波动 σ={{ compareResult.metrics.rhythm.std_abs_onset_ms }}ms
            </span>
          </p>
          <div v-if="compareResult.metrics?.stability" class="stability-block">
            <p>
              <strong>弹奏稳定性（本次）</strong>
              <span class="muted">综合分 {{ (compareResult.metrics.stability.composite_stability_score * 100).toFixed(1) }}%</span>
              <span v-if="compareResult.metrics.stability.timing_available" class="muted">
                · 起音稳定分 {{ (compareResult.metrics.stability.timing_stability_score * 100).toFixed(1) }}%
              </span>
            </p>
            <p v-if="compareResult.metrics.stability.timing_available" class="muted small-line">
              起音 σ={{ compareResult.metrics.stability.onset_std_ms }}ms · CV={{ compareResult.metrics.stability.onset_cv }}
              <span v-if="compareResult.metrics.stability.onset_p90_ms != null">
                · P90={{ compareResult.metrics.stability.onset_p90_ms }}ms
              </span>
            </p>
            <p v-else class="muted small-line">起音细项需 DTW 对齐到足够同音高音符对；若为空则综合分主要反映准确率。</p>
            <p v-if="compareResult.metrics.stability.pitch_error_density != null" class="muted small-line">
              错音密度：{{ compareResult.metrics.stability.pitch_error_density }}（错音条数 / 参考音符数）
            </p>
          </div>
          <div
            v-if="compareResult.metrics?.weak_measures_ranked?.length"
            class="weak-block weak-inline"
          >
            <strong>薄弱小节（本次 Top）</strong>
            <ul class="weak-list compact">
              <li v-for="w in compareResult.metrics.weak_measures_ranked.slice(0, 8)" :key="w.measure">
                第 {{ w.measure }} 小节 · {{ w.error_count }} 次
              </li>
            </ul>
          </div>
          <ul class="error-list">
            <li v-for="(e, i) in compareResult.errors.slice(0, 30)" :key="i">
              <span v-if="e.measure != null">第{{ e.measure }}小节 </span>
              {{ errorTypeLabel(e.type) }} —
              <span v-if="e.expected_name">{{ e.expected_name }} → </span>
              <span v-if="e.played_name">{{ e.played_name }}</span>
            </li>
          </ul>
          <p v-if="compareResult.errors.length > 30" class="more">… 还有 {{ compareResult.errors.length - 30 }} 条</p>
        </div>
      </section>

      <!-- 近期练习概况（对接 GET /api/practice/summary） -->
      <section v-if="routeMode === 'app' && appTab === 'profile'" class="card summary-section">
        <h2>4. 近期练习概况</h2>
        <p class="muted small-margin">
          统计已保存的练习记录（当前 <code>user_id={{ currentUserId }}</code>）。可查看全部曲目或仅当前乐谱。
        </p>
        <div class="form-row inline-row">
          <label class="checkbox-label">
            <input type="checkbox" v-model="summaryOnlyCurrentScore" :disabled="!scoreId" />
            仅统计当前乐谱（需先上传得到 ID）
          </label>
        </div>
        <div class="form-row inline-row">
          <label>最近条数</label>
          <input v-model.number="summaryLastN" type="number" min="1" max="200" class="input-narrow" />
          <button type="button" class="btn small" :disabled="summaryLoading" @click="loadPracticeSummary">
            {{ summaryLoading ? '加载中…' : '刷新概况' }}
          </button>
        </div>
        <p v-if="summaryError" class="error">{{ summaryError }}</p>
        <div v-else-if="practiceSummary" class="summary-box">
          <template v-if="practiceSummary.window_sessions === 0">
            <p class="muted">暂无会话（请先勾选「保存练习记录」并完成一次比对）。</p>
          </template>
          <template v-else>
            <p>
              <strong>窗口内会话数：</strong>{{ practiceSummary.window_sessions }}
              <span class="muted">（请求最近 {{ practiceSummary.last_n_requested }} 条）</span>
            </p>
            <p v-if="practiceSummary.latest_session_at" class="muted">
              最近一条时间：{{ practiceSummary.latest_session_at }}
            </p>
            <template v-if="practiceSummary.accuracy">
              <p>
                <strong>准确率</strong> 最新 {{ (practiceSummary.accuracy.latest * 100).toFixed(1) }}% ·
                平均 {{ (practiceSummary.accuracy.mean * 100).toFixed(1) }}%
                <span class="muted">
                  （最低 {{ (practiceSummary.accuracy.min * 100).toFixed(1) }}% / 最高
                  {{ (practiceSummary.accuracy.max * 100).toFixed(1) }}%）
                </span>
              </p>
            </template>
            <template v-if="practiceSummary.errors">
              <p>
                <strong>错音数（pitch 错误条数）</strong> 最近 {{ practiceSummary.errors.latest_error_count }} ·
                平均 {{ practiceSummary.errors.mean_error_count }}
              </p>
            </template>
            <template v-if="practiceSummary.rhythm && practiceSummary.rhythm.sessions_with_rhythm_score > 0">
              <p>
                <strong>节奏</strong>
                <span v-if="practiceSummary.rhythm.score_mean != null">
                  平均得分 {{ (practiceSummary.rhythm.score_mean * 100).toFixed(1) }}%
                </span>
                <span v-if="practiceSummary.rhythm.cv_onset_mean != null" class="muted">
                  · 起音 CV 均值 {{ practiceSummary.rhythm.cv_onset_mean }}
                </span>
                <span class="muted">
                  （{{ practiceSummary.rhythm.sessions_with_rhythm_score }} 条会话含节奏指标）
                </span>
              </p>
            </template>
            <div v-if="practiceSummary.stability_across_sessions" class="stability-block summary-stab">
              <strong>跨次稳定性（窗口内）</strong>
              <p class="muted small-line">
                <span v-if="practiceSummary.stability_across_sessions.accuracy_std != null">
                  准确率标准差 {{ (practiceSummary.stability_across_sessions.accuracy_std * 100).toFixed(2) }}%（≥2 次）
                </span>
                <span v-if="practiceSummary.stability_across_sessions.accuracy_range != null" class="pad-left">
                  极差 {{ (practiceSummary.stability_across_sessions.accuracy_range * 100).toFixed(1) }}%
                </span>
              </p>
              <p v-if="practiceSummary.stability_across_sessions.rhythm_score_std != null" class="muted small-line">
                节奏分标准差 {{ practiceSummary.stability_across_sessions.rhythm_score_std }}（多条含节奏指标时）
              </p>
              <p
                v-if="practiceSummary.stability_across_sessions.composite_stability_mean != null"
                class="muted small-line"
              >
                综合稳定分均值 {{ (practiceSummary.stability_across_sessions.composite_stability_mean * 100).toFixed(1) }}%
                （{{ practiceSummary.stability_across_sessions.sessions_with_composite }} 条会话含 schema≥3）
              </p>
            </div>
            <div v-if="practiceSummary.weak_measures_top?.length" class="weak-block">
              <strong>薄弱小节（窗口内累计错音 Top15）</strong>
              <ul class="weak-list">
                <li v-for="w in practiceSummary.weak_measures_top" :key="w.measure">
                  第 {{ w.measure }} 小节 · {{ w.error_count }} 次
                </li>
              </ul>
            </div>
          </template>
        </div>
        <div class="summary-box" style="margin-top: 0.8rem">
          <div class="inline-row">
            <strong>最近练习记录（可删除音频）</strong>
            <button type="button" class="btn small" :disabled="practiceSessionsLoading" @click="loadPracticeSessionsList">
              {{ practiceSessionsLoading ? '刷新中…' : '刷新记录' }}
            </button>
            <button
              type="button"
              class="btn small"
              :disabled="practiceAudioBatchDeleting || !selectedPracticeSessionIds.length"
              @click="deleteSelectedPracticeAudios"
            >
              {{ practiceAudioBatchDeleting ? '批量删除中…' : `批量删除音频(${selectedPracticeSessionIds.length})` }}
            </button>
          </div>
          <p v-if="practiceSessionsError" class="error">{{ practiceSessionsError }}</p>
          <p v-else-if="!practiceSessionsList.length" class="muted">暂无练习记录。</p>
          <div v-else class="weak-list compact">
            <div class="inline-row" style="margin-bottom: 0.4rem">
              <label class="checkbox-label">
                <input
                  type="checkbox"
                  :checked="selectedPracticeSessionIds.length === practiceSessionsList.length"
                  @change="toggleSelectAllPracticeSessions($event.target.checked)"
                />
                全选
              </label>
            </div>
            <div
              v-for="s in practiceSessionsList"
              :key="s.id"
              class="inline-row"
              style="margin-bottom: 0.3rem; align-items: center"
            >
              <label class="checkbox-label">
                <input
                  type="checkbox"
                  :checked="selectedPracticeSessionIds.includes(s.id)"
                  @change="togglePracticeSessionSelection(s.id, $event.target.checked)"
                />
              </label>
              <span class="muted">
                {{ s.created_at }} · 准确率 {{ ((Number(s.accuracy) || 0) * 100).toFixed(1) }}%
              </span>
              <span class="muted" v-if="s.has_practice_audio">
                · 音频{{ s.practice_audio_deleted ? '已删除' : '可删除' }}
              </span>
              <button
                type="button"
                class="btn small"
                :disabled="!s.has_practice_audio || s.practice_audio_deleted || deletingPracticeAudioSessionId === s.id"
                @click="deleteOnePracticeAudio(s.id)"
              >
                {{ deletingPracticeAudioSessionId === s.id ? '删除中…' : '删除本条音频' }}
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- 智能练习建议（百炼 / 阶段 1：仅文本） -->
      <section v-if="routeMode === 'app' && appTab === 'assistant'" class="card assistant-section">
        <h2>5. 智能练习建议</h2>
        <p class="muted small-margin">
          使用阿里云通义分析近期练习数据（与第 4 节相同的用户与曲目筛选）。需在项目根目录配置
          <code>DASHSCOPE_API_KEY</code>，详见 <strong>如何运行.md</strong>。
        </p>
        <div class="form-row inline-row">
          <button
            type="button"
            class="btn primary"
            :disabled="assistantLoading"
            @click="loadAssistantSuggestion"
          >
            {{ assistantLoading ? '生成中…' : '生成练习建议' }}
          </button>
          <span v-if="assistantModel" class="muted">模型：{{ assistantModel }}</span>
        </div>
        <p v-if="assistantError" class="error">{{ assistantError }}</p>
        <div v-if="assistantPlan" class="assistant-plan">
          <p>
            <strong>今日建议时长：</strong>{{ assistantPlan.today_minutes }} 分钟
            <span class="muted pad-left">推荐模式：{{ assistantPlan.suggested_compare_mode === 'advanced_rhythm' ? '高级（音准+节奏）' : '初级（仅看音准）' }}</span>
          </p>
          <p v-if="assistantPlan.user_level_estimate">
            <strong>用户水平估计：</strong>
            {{ assistantPlan.user_level_estimate.label }}
            <span class="muted">
              （score={{ assistantPlan.user_level_estimate.score }}，rank={{ assistantPlan.user_level_estimate.rank }}/5）
            </span>
          </p>
          <p v-if="assistantPlan.focus_start_measure != null && assistantPlan.focus_end_measure != null">
            <strong>推荐小节：</strong>第 {{ assistantPlan.focus_start_measure }} - {{ assistantPlan.focus_end_measure }} 小节
          </p>
          <p v-if="assistantPlan.relative_difficulty?.current_score">
            <strong>当前曲目相对难度：</strong>{{ assistantPlan.relative_difficulty.current_score.text }}
          </p>
          <p v-if="assistantPlan.relative_difficulty?.recommended_next_score">
            <strong>推荐下一首相对难度：</strong>{{ assistantPlan.relative_difficulty.recommended_next_score.text }}
          </p>
          <ul class="weak-list compact" v-if="assistantPlan.steps?.length">
            <li v-for="(s, i) in assistantPlan.steps" :key="i">{{ s }}</li>
          </ul>
          <div class="inline-row" v-if="assistantPlan.actions?.length">
            <button
              v-for="(a, i) in assistantPlan.actions"
              :key="i"
              type="button"
              class="btn small"
              @click="applyAssistantAction(a)"
            >
              {{ a.label || a.type }}
            </button>
          </div>
          <p v-if="assistantPlan.reasons?.length" class="muted small-line">
            依据：{{ assistantPlan.reasons.join('；') }}
          </p>
        </div>
        <div v-if="assistantSuggestion" class="assistant-reply">
          <pre>{{ assistantSuggestion }}</pre>
        </div>
        <div class="assistant-plan">
          <p><strong>助手会话（按用户长期记忆）</strong></p>
          <div class="inline-row" v-if="threadMessages.length" style="margin-bottom: 0.4rem">
            <span class="muted">共 {{ threadMessages.length }} 条</span>
            <button type="button" class="btn small" @click="showAllThreadMessages = !showAllThreadMessages">
              {{ showAllThreadMessages ? '仅看最近12条' : '查看全部' }}
            </button>
          </div>
          <div class="chat-box" v-if="threadMessages.length">
            <div v-for="m in displayedThreadMessages" :key="m.id" class="chat-line">
              <strong>{{ m.role === 'user' ? '你' : '助手' }}：</strong>{{ m.content }}
            </div>
          </div>
          <p v-else class="muted">暂无会话消息，发送第一条消息开始。</p>
          <div class="inline-row" style="margin-top: 0.5rem">
            <input
              v-model="chatInput"
              class="score-id-input"
              placeholder="给助手发消息，例如：我今天应该先练哪里？"
            />
            <button type="button" class="btn small" :disabled="chatLoading" @click="sendChat">
              {{ chatLoading ? '发送中…' : '发送' }}
            </button>
            <button type="button" class="btn small" :disabled="chatLoading" @click="loadAssistantThread">
              刷新会话
            </button>
          </div>
          <p v-if="chatError" class="error">{{ chatError }}</p>
        </div>
      </section>

      <section v-if="routeMode === 'app' && appTab === 'assistant'" class="card">
        <h2>6. 今日任务单（阶段3）</h2>
        <p class="muted small-margin">
          根据近期练习数据自动生成 3-4 条今日任务（先做生成与展示，下一步再接打卡）。
        </p>
        <div class="form-row inline-row">
          <button
            type="button"
            class="btn primary"
            :disabled="todayPlanLoading"
            @click="loadTodayPlan"
          >
            {{ todayPlanLoading ? '生成中…' : '生成今日任务单' }}
          </button>
        </div>
        <p v-if="todayPlanError" class="error">{{ todayPlanError }}</p>
        <div v-if="todayPlan" class="assistant-plan">
          <p>
            <strong>总时长：</strong>{{ todayPlan.total_minutes }} 分钟
            <span class="muted pad-left">窗口会话：{{ todayPlan.summary_snapshot?.window_sessions || 0 }}</span>
          </p>
          <ol class="task-list">
            <li v-for="t in todayPlan.tasks" :key="t.id">
              <p><strong>{{ t.title }}</strong>（{{ t.minutes }} 分钟）</p>
              <ul class="weak-list compact" v-if="t.steps?.length">
                <li v-for="(s, i) in t.steps" :key="i">{{ s }}</li>
              </ul>
            </li>
          </ol>
        </div>
      </section>
      <nav v-if="routeMode === 'app'" class="bottom-tabs">
        <button :class="['tab-btn', appTab === 'home' ? 'active' : '']" @click="goAppTab('home')">首页</button>
        <button :class="['tab-btn', appTab === 'library' ? 'active' : '']" @click="goAppTab('library')">曲库</button>
        <button :class="['tab-btn', appTab === 'practice' ? 'active' : '']" @click="goAppTab('practice')">练习</button>
        <button :class="['tab-btn', appTab === 'assistant' ? 'active' : '']" @click="goAppTab('assistant')">助手</button>
        <button :class="['tab-btn', appTab === 'profile' ? 'active' : '']" @click="goAppTab('profile')">我的</button>
      </nav>
    </main>
  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import {
  uploadScore,
  getScoreTechniques,
  getScoreInfo,
  getScoreMeta,
  listScores,
  deleteScore,
  deleteScoresBatch,
  getScoreImageUrl,
  assessAllScores,
  compareWithScore,
  submitPracticeSession,
  getPracticeSessions,
  deletePracticeSessionAudio,
  deletePracticeAudioBatch,
  getPracticeSummary,
  getAssistantThread,
  sendAssistantMessage,
  suggestAssistant,
  getTodayPlan,
  authRegister,
  authLogin,
  authMe,
  authLogout,
  checkBackendHealth,
  checkAdminHealth,
  getApiTargets,
  setAuthToken,
} from './api.js'

const pdfFile = ref(null)
const musicxmlFile = ref(null)
const audioFile = ref(null)
const currentUserId = ref('default')
const currentAccount = ref('')
const authToken = ref('')
const authAccountInput = ref('')
const authPasswordInput = ref('')
const authLoading = ref(false)
const authError = ref('')
const scoreId = ref(null)
const manualScoreId = ref('')
const recentScores = ref([])
const practiceScoreQuery = ref('')
const scoreFilterDifficulty = ref('')
const scoreFilterAbility = ref('')
const uploadTitle = ref('')
const scoreLibraryRows = ref([])
const scoreLibraryLoading = ref(false)
const scoreLibraryError = ref('')
const deletingScoreId = ref('')
const batchDeleting = ref(false)
const selectedLibraryScoreIds = ref([])
const uploading = ref(false)
const uploadError = ref('')
const comparing = ref(false)
const compareError = ref('')
const compareResult = ref(null)
const techniques = ref(null)
const techniquesLoading = ref(false)
const techniquesError = ref('')
// 多声部依赖重，且在部分机器上更容易失败；默认关闭，用户按需开启。
const useMultipitch = ref(false)
const compareMode = ref('beginner_pitch_only')
const persistSession = ref(false)
const focusStartMeasure = ref('')
const focusEndMeasure = ref('')

const practiceSummary = ref(null)
const summaryLoading = ref(false)
const summaryError = ref('')
const summaryOnlyCurrentScore = ref(false)
const summaryLastN = ref(30)
const practiceSessionsList = ref([])
const practiceSessionsLoading = ref(false)
const practiceSessionsError = ref('')
const selectedPracticeSessionIds = ref([])
const deletingPracticeAudioSessionId = ref('')
const practiceAudioBatchDeleting = ref(false)

const assistantLoading = ref(false)
const assistantError = ref('')
const assistantSuggestion = ref('')
const assistantModel = ref('')
const assistantPlan = ref(null)
const todayPlan = ref(null)
const todayPlanLoading = ref(false)
const todayPlanError = ref('')
const scorePageCount = ref(0)
const scorePage = ref(1)
const scoreImageError = ref('')
const scoreMeta = ref(null)
const scoreMetaLoading = ref(false)
const scoreMetaError = ref('')
const routePathLabel = ref('/')
const backendOnline = ref(true)
const backendStatusText = ref('')
let backendHealthTimer = null
const startupChecking = ref(false)
const startupChecklistError = ref('')
const startupStatus = ref({
  backendOk: true,
  loggedIn: false,
  publicApiBase: '',
  adminApiBase: '',
  adminReachable: null,
})
const reassessAllLoading = ref(false)
const reassessAllResult = ref(null)
const reassessAllError = ref('')
const routeMode = ref('app')
const appTab = ref('home')
const chatLoading = ref(false)
const chatError = ref('')
const chatInput = ref('')
const threadMessages = ref([])
const showAllThreadMessages = ref(false)
const displayedThreadMessages = computed(() => (
  showAllThreadMessages.value ? threadMessages.value : threadMessages.value.slice(-12)
))
const difficultyOptions = ['beginner', 'intermediate', 'advanced', 'expert']

function scoreDisplayNameByRow(row) {
  const title = String(row?.meta?.title || '').trim()
  return title || '未命名曲目'
}

function scoreDisplayNameById(sid) {
  const id = String(sid || '').trim()
  if (!id) return '未命名曲目'
  const row = (scoreLibraryRows.value || []).find((r) => String(r?.score_id || '') === id)
  return scoreDisplayNameByRow(row)
}

function friendlyErrorMessage(err, fallbackText) {
  const msg = String(err?.message || '').trim()
  const low = msg.toLowerCase()
  if (
    low.includes('failed to fetch')
    || low.includes('networkerror')
    || low.includes('network request failed')
    || low.includes('load failed')
  ) {
    return '无法连接后端服务，请确认后端已启动，或检查云端地址配置（VITE_PUBLIC_API_BASE）。'
  }
  return msg || fallbackText
}

async function refreshBackendHealth({ silent = false } = {}) {
  const ok = await checkBackendHealth()
  backendOnline.value = ok
  if (ok) {
    backendStatusText.value = ''
    return
  }
  if (!silent || !backendStatusText.value) {
    backendStatusText.value = '请先启动后端（建议执行 npm run backend:split:clean）。'
  }
}

async function runStartupChecklist() {
  startupChecking.value = true
  startupChecklistError.value = ''
  try {
    const targets = getApiTargets()
    const [backendOk, adminReachable] = await Promise.all([
      checkBackendHealth(),
      checkAdminHealth(),
    ])
    startupStatus.value = {
      backendOk: Boolean(backendOk),
      loggedIn: Boolean(authToken.value),
      publicApiBase: targets.publicApiBase,
      adminApiBase: targets.adminApiBase,
      adminReachable,
    }
    if (!backendOk) {
      startupChecklistError.value = '后端不可达，请先启动服务或检查 VITE_PUBLIC_API_BASE。'
    }
    if (targets.adminApiBase && adminReachable === false) {
      startupChecklistError.value = startupChecklistError.value
        ? `${startupChecklistError.value} 管理端也不可达，请检查 VITE_ADMIN_API_BASE。`
        : '管理端不可达，请检查 VITE_ADMIN_API_BASE。'
    }
  } catch (e) {
    startupChecklistError.value = friendlyErrorMessage(e, '启动自检失败')
  } finally {
    startupChecking.value = false
  }
}

const currentScoreDisplayName = computed(() => scoreDisplayNameById(scoreId.value))

const practiceScoreCandidates = computed(() => {
  const q = String(practiceScoreQuery.value || '').trim().toLowerCase()
  const libraryRows = Array.isArray(scoreLibraryRows.value)
    ? scoreLibraryRows.value.map((r) => ({
      score_id: String(r?.score_id || ''),
      title: scoreDisplayNameByRow(r),
    })).filter((r) => r.score_id)
    : []
  if (!libraryRows.length) {
    const fallback = (Array.isArray(recentScores.value) ? recentScores.value : []).map((sid) => ({
      score_id: String(sid || ''),
      title: scoreDisplayNameById(sid),
    })).filter((r) => r.score_id)
    if (!q) return fallback
    return fallback.filter((r) => String(r.title || '').toLowerCase().includes(q))
  }
  if (!q) return libraryRows
  return libraryRows.filter((r) => String(r.title || '').toLowerCase().includes(q))
})

const scoreImageSrc = computed(() => {
  if (!scoreId.value) return ''
  return getScoreImageUrl(scoreId.value, scorePage.value)
})

function parseHashRoute() {
  const hash = String(window.location.hash || '')
  if (hash === '#/admin') {
    // Admin 为独立入口；file:// 下不能用根路径 /admin.html，需相对当前页面解析
    window.location.replace(new URL('admin.html', window.location.href).href)
    return
  }
  const appTabMatch = hash.match(/^#\/app\/([a-zA-Z0-9_-]+)/)
  if (appTabMatch && appTabMatch[1]) {
    routeMode.value = 'app'
    const t = String(appTabMatch[1]).toLowerCase()
    appTab.value = ['home', 'library', 'practice', 'assistant', 'profile'].includes(t)
      ? t
      : 'home'
    routePathLabel.value = `/app/${appTab.value}`
    return
  }
  if (hash === '#/app' || hash === '#/' || hash === '') {
    routeMode.value = 'app'
    appTab.value = 'home'
    routePathLabel.value = '/app/home'
    return
  }
  const m = hash.match(/^#\/score\/([^/?#]+)/)
  if (m && m[1]) {
    routeMode.value = 'app'
    appTab.value = 'library'
    const sid = decodeURIComponent(m[1])
    scoreId.value = sid
    manualScoreId.value = sid
    routePathLabel.value = `/score/${sid}`
    addRecentScore(sid)
    return
  }
  routePathLabel.value = '/'
}

function goHome() {
  window.location.hash = '#/app/home'
}

function goApp() {
  window.location.hash = '#/app/home'
}

function goAppTab(tab) {
  const t = String(tab || '').toLowerCase()
  const safe = ['home', 'library', 'practice', 'assistant', 'profile'].includes(t)
    ? t
    : 'home'
  window.location.hash = `#/app/${safe}`
}

function goScore(sid) {
  if (!sid) return
  window.location.hash = `#/score/${encodeURIComponent(String(sid))}`
}

function openScoreFromInput() {
  const sid = String(manualScoreId.value || '').trim()
  if (!sid) return
  goScore(sid)
}

function selectPracticeScore(sid) {
  const id = String(sid || '').trim()
  if (!id) return
  scoreId.value = id
  manualScoreId.value = id
  addRecentScore(id)
}

function applyLoggedInUser(user) {
  if (!user) return
  const uid = String(user.id || '').trim()
  const acc = String(user.account || '').trim()
  // 切换账号时先清空助手展示，避免上一账号历史在新请求返回前短暂残留
  threadMessages.value = []
  showAllThreadMessages.value = false
  assistantSuggestion.value = ''
  assistantPlan.value = null
  chatError.value = ''
  assistantError.value = ''
  if (uid) currentUserId.value = uid
  if (acc) currentAccount.value = acc
}

async function doRegister() {
  authLoading.value = true
  authError.value = ''
  try {
    await authRegister(authAccountInput.value, authPasswordInput.value)
    const res = await authLogin(authAccountInput.value, authPasswordInput.value)
    authToken.value = res.access_token || ''
    applyLoggedInUser(res.user)
    setAuthToken(authToken.value)
    localStorage.setItem('auth_token', authToken.value)
  } catch (e) {
    authError.value = friendlyErrorMessage(e, '注册失败')
  } finally {
    authLoading.value = false
  }
}

async function doLogin() {
  authLoading.value = true
  authError.value = ''
  try {
    const res = await authLogin(authAccountInput.value, authPasswordInput.value)
    authToken.value = res.access_token || ''
    applyLoggedInUser(res.user)
    setAuthToken(authToken.value)
    localStorage.setItem('auth_token', authToken.value)
  } catch (e) {
    authError.value = friendlyErrorMessage(e, '登录失败')
  } finally {
    authLoading.value = false
  }
}

async function doLogout() {
  authLoading.value = true
  authError.value = ''
  try {
    if (authToken.value) {
      await authLogout(authToken.value)
    }
  } catch {
    // ignore logout network errors
  } finally {
    authToken.value = ''
    currentAccount.value = ''
    setAuthToken('')
    threadMessages.value = []
    showAllThreadMessages.value = false
    assistantSuggestion.value = ''
    assistantPlan.value = null
    chatError.value = ''
    assistantError.value = ''
    localStorage.removeItem('auth_token')
    authLoading.value = false
  }
}

function addRecentScore(sid) {
  if (!sid) return
  const old = recentScores.value.filter((x) => x !== sid)
  recentScores.value = [sid, ...old].slice(0, 8)
  try {
    localStorage.setItem('recent_scores', JSON.stringify(recentScores.value))
  } catch {
    // ignore localStorage failures in restricted browsers
  }
}

function removeRecentScore(sid) {
  const id = String(sid || '').trim()
  if (!id) return
  recentScores.value = recentScores.value.filter((x) => x !== id)
  try {
    localStorage.setItem('recent_scores', JSON.stringify(recentScores.value))
  } catch {
    // ignore localStorage failures in restricted browsers
  }
}

function handleScoreImageError() {
  scoreImageError.value = '当前页乐谱图加载失败，请确认该 score_id 是否存在且包含 PDF。'
}

async function loadScoreMeta() {
  if (!scoreId.value) {
    scoreMeta.value = null
    return
  }
  scoreMetaLoading.value = true
  scoreMetaError.value = ''
  try {
    const res = await getScoreMeta(scoreId.value)
    scoreMeta.value = res.meta || null
  } catch (e) {
    scoreMetaError.value = e.message
    scoreMeta.value = null
  } finally {
    scoreMetaLoading.value = false
  }
}

async function runAssessAllScores() {
  reassessAllLoading.value = true
  reassessAllError.value = ''
  reassessAllResult.value = null
  try {
    reassessAllResult.value = await assessAllScores({ useLlm: true, limit: 500 })
    if (scoreId.value) await loadScoreMeta()
  } catch (e) {
    reassessAllError.value = e.message
  } finally {
    reassessAllLoading.value = false
  }
  await loadScoreLibrary()
}

async function loadScoreLibrary(query = '') {
  scoreLibraryLoading.value = true
  scoreLibraryError.value = ''
  try {
    const res = await listScores({
      q: query,
      difficulty: scoreFilterDifficulty.value,
      ability: scoreFilterAbility.value,
      limit: 300,
      includeMeta: true,
    })
    scoreLibraryRows.value = Array.isArray(res.rows) ? res.rows : []
    const existing = new Set(scoreLibraryRows.value.map((x) => x?.score_id).filter(Boolean))
    selectedLibraryScoreIds.value = selectedLibraryScoreIds.value.filter((sid) => existing.has(sid))
  } catch (e) {
    const msg = String(e?.message || '')
    // Backward-compatible fallback: if backend has not reloaded /api/score/list yet,
    // still show recently visited scores so practice flow remains usable.
    if (msg.includes('Not Found') || msg.includes('404')) {
      scoreLibraryError.value = '曲库接口暂不可用（可能后端未重启），已回退显示最近曲目。请重启后端后再试。'
      scoreLibraryRows.value = (recentScores.value || []).map((sid) => ({
        score_id: String(sid),
        updated_at: 0,
        meta: null,
      }))
      selectedLibraryScoreIds.value = []
    } else {
      scoreLibraryError.value = friendlyErrorMessage({ message: msg }, '获取曲库列表失败')
      scoreLibraryRows.value = []
      selectedLibraryScoreIds.value = []
    }
  } finally {
    scoreLibraryLoading.value = false
  }
}

async function loadAssistantSuggestion() {
  assistantLoading.value = true
  assistantError.value = ''
  assistantSuggestion.value = ''
  assistantModel.value = ''
  assistantPlan.value = null
  try {
    const sid = summaryOnlyCurrentScore.value && scoreId.value ? scoreId.value : null
    const lastN = Math.min(100, Math.max(1, Number(summaryLastN.value) || 20))
    const res = await suggestAssistant({
      userId: currentUserId.value,
      scoreId: sid,
      lastN,
    })
    assistantSuggestion.value = res.suggestion || ''
    assistantModel.value = res.model || ''
    assistantPlan.value = res.plan || null
  } catch (e) {
    assistantError.value = friendlyErrorMessage(e, '智能建议请求失败')
  } finally {
    assistantLoading.value = false
  }
}

async function loadAssistantThread() {
  chatLoading.value = true
  chatError.value = ''
  try {
    const res = await getAssistantThread({ userId: currentUserId.value, limit: 200 })
    threadMessages.value = res.messages || []
  } catch (e) {
    chatError.value = friendlyErrorMessage(e, '获取助手会话失败')
    threadMessages.value = []
  } finally {
    chatLoading.value = false
  }
}

async function sendChat() {
  const content = String(chatInput.value || '').trim()
  if (!content) return
  chatLoading.value = true
  chatError.value = ''
  try {
    const sid = summaryOnlyCurrentScore.value && scoreId.value ? scoreId.value : null
    await sendAssistantMessage({
      userId: currentUserId.value,
      content,
      scoreId: sid,
      lastN: Math.min(100, Math.max(1, Number(summaryLastN.value) || 20)),
    })
    chatInput.value = ''
    await loadAssistantThread()
  } catch (e) {
    chatError.value = friendlyErrorMessage(e, '发送消息失败')
  } finally {
    chatLoading.value = false
  }
}

async function loadTodayPlan() {
  todayPlanLoading.value = true
  todayPlanError.value = ''
  todayPlan.value = null
  try {
    const sid = summaryOnlyCurrentScore.value && scoreId.value ? scoreId.value : null
    const lastN = Math.min(100, Math.max(1, Number(summaryLastN.value) || 20))
    todayPlan.value = await getTodayPlan({
      userId: currentUserId.value,
      scoreId: sid,
      lastN,
    })
  } catch (e) {
    todayPlanError.value = e.message
  } finally {
    todayPlanLoading.value = false
  }
}

function applyAssistantAction(action) {
  if (!action || !action.type || !action.payload) return
  const p = action.payload
  if (action.type === 'set_focus_measures') {
    if (p.focus_start_measure != null) focusStartMeasure.value = String(p.focus_start_measure)
    if (p.focus_end_measure != null) focusEndMeasure.value = String(p.focus_end_measure)
  }
  if (action.type === 'set_compare_mode' && p.compare_mode) {
    compareMode.value = p.compare_mode
  }
  if (action.type === 'open_score_page' && p.score_id) {
    goScore(p.score_id)
  }
}

async function loadPracticeSummary() {
  summaryLoading.value = true
  summaryError.value = ''
  try {
    const sid = summaryOnlyCurrentScore.value && scoreId.value ? scoreId.value : null
    practiceSummary.value = await getPracticeSummary(currentUserId.value, {
      scoreId: sid,
      lastN: Math.min(200, Math.max(1, Number(summaryLastN.value) || 30)),
    })
  } catch (e) {
    summaryError.value = e.message
    practiceSummary.value = null
  } finally {
    summaryLoading.value = false
  }
}

async function loadPracticeSessionsList() {
  practiceSessionsLoading.value = true
  practiceSessionsError.value = ''
  try {
    const sid = summaryOnlyCurrentScore.value && scoreId.value ? scoreId.value : null
    const res = await getPracticeSessions(currentUserId.value, 30, sid)
    practiceSessionsList.value = Array.isArray(res.sessions) ? res.sessions : []
    const existing = new Set(practiceSessionsList.value.map((x) => x?.id).filter(Boolean))
    selectedPracticeSessionIds.value = selectedPracticeSessionIds.value.filter((id) => existing.has(id))
  } catch (e) {
    practiceSessionsError.value = String(e?.message || '获取练习记录失败')
    practiceSessionsList.value = []
    selectedPracticeSessionIds.value = []
  } finally {
    practiceSessionsLoading.value = false
  }
}

function togglePracticeSessionSelection(sessionId, checked) {
  const sid = String(sessionId || '').trim()
  if (!sid) return
  if (checked) {
    if (!selectedPracticeSessionIds.value.includes(sid)) {
      selectedPracticeSessionIds.value.push(sid)
    }
  } else {
    selectedPracticeSessionIds.value = selectedPracticeSessionIds.value.filter((id) => id !== sid)
  }
}

function toggleSelectAllPracticeSessions(checked) {
  if (checked) {
    selectedPracticeSessionIds.value = practiceSessionsList.value.map((s) => s.id).filter(Boolean)
  } else {
    selectedPracticeSessionIds.value = []
  }
}

async function deleteOnePracticeAudio(sessionId) {
  const sid = String(sessionId || '').trim()
  if (!sid) return
  deletingPracticeAudioSessionId.value = sid
  practiceSessionsError.value = ''
  try {
    await deletePracticeSessionAudio(sid)
    await loadPracticeSessionsList()
  } catch (e) {
    practiceSessionsError.value = String(e?.message || '删除练习音频失败')
  } finally {
    deletingPracticeAudioSessionId.value = ''
  }
}

async function deleteSelectedPracticeAudios() {
  if (!selectedPracticeSessionIds.value.length) return
  practiceAudioBatchDeleting.value = true
  practiceSessionsError.value = ''
  try {
    await deletePracticeAudioBatch([...selectedPracticeSessionIds.value])
    selectedPracticeSessionIds.value = []
    await loadPracticeSessionsList()
  } catch (e) {
    practiceSessionsError.value = String(e?.message || '批量删除练习音频失败')
  } finally {
    practiceAudioBatchDeleting.value = false
  }
}

onMounted(() => {
  try {
    const uid = localStorage.getItem('current_user_id')
    if (uid && uid.trim()) currentUserId.value = uid.trim()
    const at = localStorage.getItem('auth_token')
    if (at && at.trim()) {
      authToken.value = at.trim()
      setAuthToken(authToken.value)
    }
    const raw = localStorage.getItem('recent_scores')
    if (raw) {
      const arr = JSON.parse(raw)
      if (Array.isArray(arr)) recentScores.value = arr.filter((x) => typeof x === 'string').slice(0, 8)
    }
  } catch {
    // ignore invalid storage
  }
  parseHashRoute()
  window.addEventListener('hashchange', parseHashRoute)
  refreshBackendHealth()
  runStartupChecklist()
  backendHealthTimer = window.setInterval(() => {
    refreshBackendHealth({ silent: true })
  }, 15000)
  if (authToken.value) {
    authMe(authToken.value)
      .then((res) => {
        applyLoggedInUser(res.user)
      })
      .catch(() => {
        authToken.value = ''
        currentAccount.value = ''
        setAuthToken('')
        localStorage.removeItem('auth_token')
      })
  }
  loadScoreLibrary()
  loadPracticeSummary()
  loadPracticeSessionsList()
  loadAssistantThread()
})

watch(currentUserId, async () => {
  try {
    localStorage.setItem('current_user_id', currentUserId.value)
  } catch {
    // ignore localStorage errors
  }
  await loadPracticeSummary()
  await loadPracticeSessionsList()
  await loadAssistantThread()
})

onBeforeUnmount(() => {
  window.removeEventListener('hashchange', parseHashRoute)
  if (backendHealthTimer) {
    clearInterval(backendHealthTimer)
    backendHealthTimer = null
  }
})

watch(scoreId, async (id) => {
  techniques.value = null
  techniquesError.value = ''
  scoreImageError.value = ''
  scorePageCount.value = 0
  scorePage.value = 1
  if (!id) return
  addRecentScore(id)
  techniquesLoading.value = true
  try {
    techniques.value = await getScoreTechniques(id)
  } catch (e) {
    techniquesError.value = e.message
  } finally {
    techniquesLoading.value = false
  }
  try {
    const info = await getScoreInfo(id)
    scorePageCount.value = Number(info.page_count) || 1
  } catch (e) {
    scoreImageError.value = e.message
  }
  await loadScoreMeta()
})

watch(scorePage, (p) => {
  scoreImageError.value = ''
  const n = Number(p) || 1
  if (n < 1) scorePage.value = 1
  if (scorePageCount.value > 0 && n > scorePageCount.value) scorePage.value = scorePageCount.value
})

function errorTypeLabel(type) {
  const map = { wrong: '错音', missed: '漏弹', extra: '多弹' }
  return map[type] || type
}

function techniqueLabel(type) {
  const map = {
    Staccato: '断奏',
    Staccatissimo: '短断奏',
    Accent: '重音',
    Tenuto: '保持',
    Marcato: '顿音',
    Fermata: '延音',
    Piano: '弱',
    Forte: '强',
    MezzoPiano: '中弱',
    MezzoForte: '中强',
    Pianissimo: '很弱',
    Fortissimo: '很强',
    Crescendo: '渐强',
    Diminuendo: '渐弱',
    Decrescendo: '渐弱',
  }
  return map[type] || type
}

async function doUpload() {
  if (!pdfFile.value || !musicxmlFile.value) return
  uploading.value = true
  uploadError.value = ''
  compareResult.value = null
  try {
    const res = await uploadScore(pdfFile.value, musicxmlFile.value, uploadTitle.value)
    scoreId.value = res.score_id
    uploadTitle.value = ''
    addRecentScore(res.score_id)
    await loadScoreLibrary()
    goScore(res.score_id)
  } catch (e) {
    uploadError.value = e.message
  } finally {
    uploading.value = false
  }
}

function toggleScoreSelection(scoreId, checked) {
  const sid = String(scoreId || '').trim()
  if (!sid) return
  if (checked) {
    if (!selectedLibraryScoreIds.value.includes(sid)) {
      selectedLibraryScoreIds.value = [...selectedLibraryScoreIds.value, sid]
    }
    return
  }
  selectedLibraryScoreIds.value = selectedLibraryScoreIds.value.filter((x) => x !== sid)
}

function toggleSelectAllScores(checked) {
  if (!checked) {
    selectedLibraryScoreIds.value = []
    return
  }
  selectedLibraryScoreIds.value = scoreLibraryRows.value.map((r) => r.score_id).filter(Boolean)
}

async function deleteOneScore(scoreIdToDelete) {
  const sid = String(scoreIdToDelete || '').trim()
  if (!sid) return
  const ok = window.confirm(`确认删除曲目「${scoreDisplayNameById(sid)}」吗？此操作不可恢复。`)
  if (!ok) return
  deletingScoreId.value = sid
  scoreLibraryError.value = ''
  try {
    await deleteScore(sid)
    if (scoreId.value === sid) {
      scoreId.value = null
      manualScoreId.value = ''
    }
    selectedLibraryScoreIds.value = selectedLibraryScoreIds.value.filter((x) => x !== sid)
    await loadScoreLibrary(manualScoreId.value || practiceScoreQuery.value || '')
  } catch (e) {
    scoreLibraryError.value = friendlyErrorMessage(e, '删除曲目失败')
  } finally {
    deletingScoreId.value = ''
  }
}

async function deleteSelectedScores() {
  if (!selectedLibraryScoreIds.value.length) return
  const ok = window.confirm(`确认批量删除 ${selectedLibraryScoreIds.value.length} 首曲目吗？此操作不可恢复。`)
  if (!ok) return
  batchDeleting.value = true
  scoreLibraryError.value = ''
  try {
    const ids = [...selectedLibraryScoreIds.value]
    const res = await deleteScoresBatch(ids)
    if (ids.includes(String(scoreId.value || ''))) {
      scoreId.value = null
      manualScoreId.value = ''
    }
    selectedLibraryScoreIds.value = []
    await loadScoreLibrary(manualScoreId.value || practiceScoreQuery.value || '')
    if ((res.failed_count || 0) > 0) {
      scoreLibraryError.value = `已删除 ${res.deleted_count} 首，失败 ${res.failed_count} 首。`
    }
  } catch (e) {
    scoreLibraryError.value = friendlyErrorMessage(e, '批量删除失败')
  } finally {
    batchDeleting.value = false
  }
}

async function doCompare() {
  if (!scoreId.value || !audioFile.value) return
  comparing.value = true
  compareError.value = ''
  try {
    const startM =
      focusStartMeasure.value !== '' ? Number(focusStartMeasure.value) : null
    const endM =
      focusEndMeasure.value !== '' ? Number(focusEndMeasure.value) : null
    const res = await compareWithScore(
      scoreId.value,
      audioFile.value,
      useMultipitch.value,
      persistSession.value,
      startM,
      endM,
      compareMode.value,
    )
    compareResult.value = res
    if (persistSession.value && res.reference_notes && res.played_notes) {
      try {
        const saved = await submitPracticeSession({
          user_id: currentUserId.value,
          score_id: scoreId.value,
          accuracy: res.accuracy,
          errors: res.errors,
          compare_mode: compareMode.value,
          focus_start_measure:
            focusStartMeasure.value !== '' ? Number(focusStartMeasure.value) : null,
          focus_end_measure:
            focusEndMeasure.value !== '' ? Number(focusEndMeasure.value) : null,
          reference_notes: res.reference_notes,
          played_notes: res.played_notes,
          practice_audio_id: res.practice_audio_id || null,
          practice_audio_relpath: res.practice_audio_relpath || null,
        })
        compareResult.value = {
          ...res,
          session_id: saved.session_id,
          metrics: saved.metrics,
        }
        await loadPracticeSummary()
        await loadPracticeSessionsList()
      } catch (e) {
        compareError.value = `比对成功，但保存练习记录失败：${e.message}`
      }
    }
  } catch (e) {
    compareError.value = friendlyErrorMessage(e, '比对失败')
  } finally {
    comparing.value = false
  }
}

</script>

<style>
* {
  box-sizing: border-box;
}
body {
  margin: 0;
  font-family: system-ui, -apple-system, sans-serif;
  background: #f5f5f5;
}
.app {
  min-height: 100vh;
  padding-bottom: 2rem;
}
.header {
  background: #1a1a2e;
  color: #eee;
  padding: 1.25rem 2rem;
}
.header h1 {
  margin: 0 0 0.25rem 0;
  font-size: 1.5rem;
}
.header .sub {
  margin: 0;
  font-size: 0.9rem;
  opacity: 0.85;
}
.nav-row {
  margin-top: 0.65rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.nav-tip {
  margin-left: 0.25rem;
}
.main {
  max-width: 1000px;
  margin: 0 auto;
  padding: 1.5rem 1.5rem 5rem 1.5rem;
}
.score-id-input {
  min-width: 22rem;
  max-width: 100%;
  padding: 0.35rem 0.5rem;
  border: 1px solid #ccc;
  border-radius: 6px;
}
.recent-list {
  margin-top: 0.7rem;
}
.score-image {
  width: 100%;
  max-width: 920px;
  display: block;
  margin-top: 0.7rem;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #fff;
}
.score-meta-box {
  margin-top: 0.8rem;
  padding: 0.7rem 0.85rem;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #f8fafc;
}
.score-meta-box p {
  margin: 0 0 0.35rem 0;
}
.card {
  background: #fff;
  border-radius: 8px;
  padding: 1.25rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}
.card h2 {
  margin: 0 0 1rem 0;
  font-size: 1.1rem;
}
.form-row {
  margin-bottom: 0.75rem;
}
.form-row label {
  display: block;
  margin-bottom: 0.25rem;
  font-weight: 500;
}
.checkbox-label {
  display: flex !important;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-weight: 400;
}
.checkbox-label input[type="checkbox"] {
  width: auto;
  margin: 0;
}
.req {
  color: #c00;
}
.btn {
  padding: 0.5rem 1rem;
  border-radius: 6px;
  border: 1px solid #ccc;
  background: #fff;
  cursor: pointer;
  font-size: 0.95rem;
}
.btn.primary {
  background: #2563eb;
  color: #fff;
  border-color: #2563eb;
}
.btn.primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.btn.small {
  padding: 0.35rem 0.65rem;
  font-size: 0.85rem;
  margin-right: 0.5rem;
}
.error {
  color: #b91c1c;
  margin-top: 0.5rem;
}
.success {
  color: #059669;
  margin-top: 0.5rem;
}
.result-box {
  margin-top: 1rem;
  padding: 1rem;
  background: #f8fafc;
  border-radius: 6px;
}
.result-box p {
  margin: 0 0 0.5rem 0;
}
.error-list {
  margin: 0.5rem 0 0 0;
  padding-left: 1.25rem;
  max-height: 200px;
  overflow-y: auto;
}
.error-list li {
  margin-bottom: 0.25rem;
  font-size: 0.9rem;
}
.more {
  font-size: 0.85rem;
  color: #64748b;
}
.muted {
  color: #64748b;
  margin-top: 0.5rem;
}
.technique-summary {
  margin-bottom: 0.75rem;
}
.technique-summary .summary-line {
  margin: 0 0 0.5rem 0;
}
.technique-counts {
  margin: 0;
  padding-left: 1.25rem;
  list-style: disc;
}
.technique-counts li {
  margin-bottom: 0.25rem;
  font-size: 0.95rem;
}
.technique-detail {
  margin-top: 0.75rem;
}
.technique-detail summary {
  cursor: pointer;
  font-size: 0.9rem;
  color: #2563eb;
}
.technique-events {
  margin: 0.5rem 0 0 0;
  padding-left: 1.25rem;
  max-height: 240px;
  overflow-y: auto;
  font-size: 0.9rem;
  list-style: none;
}
.technique-events li {
  margin-bottom: 0.2rem;
}
.technique-events .tech-name {
  color: #059669;
  font-weight: 500;
  margin-left: 0.25rem;
}
.small-margin {
  margin: 0 0 0.75rem 0;
  font-size: 0.9rem;
}
.inline-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
}
.inline-row label:not(.checkbox-label) {
  margin: 0;
  font-weight: 500;
}
.input-narrow {
  width: 4.5rem;
  padding: 0.35rem 0.5rem;
  border: 1px solid #ccc;
  border-radius: 6px;
}
.summary-box {
  margin-top: 0.75rem;
  padding: 0.75rem 1rem;
  background: #f8fafc;
  border-radius: 6px;
  font-size: 0.95rem;
}
.summary-box p {
  margin: 0 0 0.5rem 0;
}
.overview-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.92rem;
}
.overview-table th,
.overview-table td {
  border-bottom: 1px solid #e2e8f0;
  text-align: left;
  padding: 0.4rem 0.35rem;
}
.overview-table th {
  font-weight: 600;
  color: #334155;
}
.startup-check-list {
  margin: 0.5rem 0 0 0;
  padding-left: 1.25rem;
}
.startup-check-list li {
  margin-bottom: 0.35rem;
}
.startup-check-list strong {
  margin-right: 0.5rem;
}
.weak-block {
  margin-top: 0.5rem;
}
.weak-list {
  margin: 0.35rem 0 0 1.25rem;
  padding: 0;
}
.weak-list li {
  margin-bottom: 0.2rem;
}
.weak-list.compact {
  margin-top: 0.35rem;
  max-height: none;
}
.weak-inline {
  margin-top: 0.75rem;
}
.stability-block {
  margin-top: 0.75rem;
  padding: 0.6rem 0.75rem;
  background: #eef2ff;
  border-radius: 6px;
  font-size: 0.9rem;
}
.stability-block p {
  margin: 0 0 0.35rem 0;
}
.stability-block p:last-child {
  margin-bottom: 0;
}
.small-line {
  font-size: 0.88rem;
}
.summary-stab {
  margin-top: 0.75rem;
  background: #eef2ff;
}
.pad-left {
  margin-left: 0.5rem;
}
.assistant-reply {
  margin-top: 0.75rem;
  padding: 1rem;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  white-space: pre-wrap;
  font-size: 0.95rem;
  line-height: 1.55;
}
.assistant-plan {
  margin-top: 0.75rem;
  padding: 0.85rem 1rem;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
}
.assistant-plan p {
  margin: 0 0 0.45rem 0;
}
.chat-box {
  max-height: 220px;
  overflow-y: auto;
  border: 1px solid #dbeafe;
  border-radius: 6px;
  padding: 0.45rem 0.55rem;
  background: #ffffff;
}
.chat-line {
  font-size: 0.9rem;
  margin-bottom: 0.35rem;
  line-height: 1.45;
}
.recent-item {
  position: relative;
  display: inline-block;
}
.recent-item-main {
  padding-right: 1.35rem;
}
.recent-item-close {
  position: absolute;
  top: -6px;
  right: -6px;
  width: 18px;
  height: 18px;
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  background: #ffffff;
  color: #64748b;
  font-size: 12px;
  line-height: 16px;
  cursor: pointer;
}
.recent-item-close:hover {
  color: #b91c1c;
  border-color: #fecaca;
  background: #fef2f2;
}
.bottom-tabs {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  height: 58px;
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 0;
  border-top: 1px solid #dbeafe;
  background: #ffffff;
  z-index: 30;
}
.tab-btn {
  border: none;
  background: transparent;
  font-size: 0.9rem;
  color: #475569;
}
.tab-btn.active {
  color: #2563eb;
  font-weight: 600;
}
.task-list {
  margin: 0.4rem 0 0 1.2rem;
  padding: 0;
}
.task-list > li {
  margin-bottom: 0.55rem;
}
.task-list p {
  margin: 0 0 0.2rem 0;
}
.assistant-reply pre {
  margin: 0;
  font-family: inherit;
  white-space: pre-wrap;
  word-break: break-word;
}
code {
  font-size: 0.85em;
  background: #e2e8f0;
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
}
</style>
