<template>
  <div class="app">
    <div
      v-if="!isAuthenticated"
      class="login-shell"
      :class="{ 'login-shell--handoff-leave': loginHandoffLeaveActive }"
    >
    <main
      class="login-main"
      :class="{ 'login-main--intro-active': loginIntroPhase !== 'done' }"
    >
      <section class="login-card" :style="loginCardMinH ? { minHeight: loginCardMinH } : undefined">
        <div class="login-logo-slot" :style="loginLogoSlotMinH ? { minHeight: loginLogoSlotMinH } : undefined">
          <img
            ref="loginLogoImgRef"
            class="login-logo"
            :style="loginLogoFlyStyle"
            src="/keygent-logo.png"
            alt="keygent logo"
          />
        </div>
        <div class="login-rest" :class="{ 'login-rest--intro-show': loginIntroPhase === 'done' }">
          <h1 class="login-title">钢琴陪练</h1>
          <p class="muted login-sub">登录后可进入首页并使用全部功能</p>
          <div class="form-row">
            <label>用户名</label>
            <input
              v-model="authAccountInput"
              class="score-id-input login-input"
              placeholder="请输入用户名"
              maxlength="128"
              @keyup.enter="focusLoginPassword"
            />
            <p class="muted hint-line">至少 3 个字符</p>
          </div>
          <div class="form-row">
            <label>密码</label>
            <input
              ref="loginPasswordInputEl"
              v-model="authPasswordInput"
              class="score-id-input login-input"
              type="password"
              placeholder="请输入密码"
              maxlength="128"
              @keyup.enter="doAuthEntry"
            />
            <p class="muted hint-line">至少 6 个字符</p>
          </div>
          <button type="button" class="btn primary login-btn" :disabled="authLoading" @click="doAuthEntry">
            {{ authLoading ? '处理中…' : '登录 / 注册' }}
          </button>
          <p v-if="authError" class="error">{{ authError }}</p>
        </div>
      </section>
    </main>
    <button
      type="button"
      class="login-intro-debug-btn"
      @click="replayLoginIntroDebug"
    >
      调试：重放开屏动画
    </button>
    </div>

    <template v-else>
    <div
      class="app-authenticated"
      :class="{ 'app-authenticated--handoff-enter': authAppHandoffEnterActive }"
      @animationend="onAuthAppHandoffEnterEnd"
    >
      <!-- 首次注册成功后：使用说明幻灯片（样式占位，文案后续替换） -->
      <Transition name="onboarding-root" @after-leave="onOnboardingRootAfterLeave">
        <div
          v-if="showPostRegisterOnboarding"
          class="onboarding-root"
          role="dialog"
          aria-modal="true"
          aria-labelledby="onboarding-slide-title"
        >
        <div class="onboarding-backdrop" aria-hidden="true" />
        <div class="onboarding-card">
          <p class="onboarding-welcome-strip">快速了解主要功能</p>
          <Transition name="onboarding-slide" mode="out-in">
            <div :key="onboardingSlideIndex" class="onboarding-slide-inner">
              <div class="onboarding-visual" aria-hidden="true">
                {{ onboardingSlides[onboardingSlideIndex].imageHint }}
              </div>
              <h2 id="onboarding-slide-title" class="onboarding-slide-title">
                {{ onboardingSlides[onboardingSlideIndex].title }}
              </h2>
              <p class="onboarding-slide-body">
                {{ onboardingSlides[onboardingSlideIndex].body }}
              </p>
            </div>
          </Transition>
          <div class="onboarding-dots" role="tablist" aria-label="幻灯片进度">
            <span
              v-for="(_, i) in onboardingSlides"
              :key="i"
              :class="['onboarding-dot', { 'onboarding-dot--active': i === onboardingSlideIndex }]"
              role="presentation"
            />
          </div>
          <div class="onboarding-footer">
            <button type="button" class="onboarding-skip" @click="completePostRegisterOnboarding">跳过</button>
            <div class="onboarding-footer-nav">
              <button
                type="button"
                class="btn small onboarding-prev"
                :disabled="onboardingSlideIndex === 0"
                @click="onboardingPrev"
              >
                上一步
              </button>
              <button type="button" class="btn primary onboarding-next" @click="onboardingNextOrFinish">
                {{ onboardingSlideIndex < onboardingSlides.length - 1 ? '下一步' : '进入首页' }}
              </button>
            </div>
          </div>
        </div>
        </div>
      </Transition>

    <header class="header">
      <div class="header-main">
        <h1>钢琴陪练 · keygent</h1>
        <p v-if="!backendOnline" class="error">后端连接异常：{{ backendStatusText }}</p>
      </div>
      <button type="button" class="btn small header-help-btn" @click="openHelpOnboarding">帮助</button>
    </header>

    <div
      class="app-body-scroll"
      :class="{ 'app-body-scroll--home-locked': routeMode === 'app' && appTab === 'home' }"
    >
    <main
      class="main"
      :class="{ 'main--home-fill': routeMode === 'app' && appTab === 'home' }"
    >
      <section v-if="routeMode === 'app' && appTab === 'profile'" class="card profile-header-card">
        <div class="profile-topbar">
          <button type="button" class="btn small" @click="goAppTab('home')">返回</button>
          <button type="button" class="btn small" :disabled="authLoading || !authToken" @click="doLogoutWithConfirm">
            退出登录
          </button>
        </div>
        <h2>个人主页</h2>
        <div class="profile-header">
          <div class="profile-avatar" aria-label="默认头像">
            <span class="profile-avatar-text">{{ (currentAccount || 'U').slice(0, 1).toUpperCase() }}</span>
          </div>
          <div class="profile-header-right">
            <div class="profile-name">{{ currentAccount || '未登录' }}</div>
          </div>
        </div>
      </section>

      <section
        v-show="showLibraryUnderScoreSlide"
        class="card library-home-section"
        :class="{ 'library-home-section--non-interactive': routeMode === 'score' && libraryUnderlayForScore }"
      >
        <div class="library-home-toolbar">
          <h2>首页 · 曲库</h2>
          <div class="home-search-row">
            <input
              v-model="homeSearchInput"
              class="score-id-input home-search-input"
              placeholder="搜索曲目名称"
              @keyup.enter="searchHomeScores"
            />
            <button type="button" class="btn small" :disabled="scoreLibraryLoading" @click="searchHomeScores">搜索</button>
            <button type="button" class="btn small" @click="showHomeFilters = !showHomeFilters">
              {{ showHomeFilters ? '收起筛选' : '筛选' }}
            </button>
          </div>
          <div v-if="showHomeFilters" class="home-filter-panel">
            <div class="inline-row">
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
              <button type="button" class="btn small" :disabled="scoreLibraryLoading" @click="applyHomeFilters">
                应用筛选
              </button>
            </div>
          </div>
        </div>
        <div class="library-home-list-body">
          <p v-if="scoreLibraryError" class="error">{{ scoreLibraryError }}</p>
          <div v-if="scoreLibraryError" class="inline-row" style="margin-top: 0.5rem">
            <button type="button" class="btn small" :disabled="scoreLibraryLoading" @click="searchHomeScores">重试加载</button>
            <button type="button" class="btn small" :disabled="scoreLibraryLoading" @click="clearHomeFilters">
              清空筛选/返回全部
            </button>
          </div>
          <p v-else-if="scoreLibraryLoading" class="muted">曲库加载中…</p>
          <div v-else-if="!homeScoreCards.length">
            <p class="muted">暂无匹配曲目。</p>
            <button
              v-if="hasHomeFilterApplied"
              type="button"
              class="btn small"
              :disabled="scoreLibraryLoading"
              @click="clearHomeFilters"
            >
              清空筛选/返回全部
            </button>
          </div>
          <div v-else class="home-score-grid">
            <button
              v-for="r in homeScoreCards"
              :key="r.score_id"
              type="button"
              class="home-score-card"
              @click="goScore(r.score_id)"
            >
              <div v-if="r.isPlaceholder" class="home-score-cover home-score-cover-fallback">
                <span class="muted">占位封面</span>
              </div>
              <img
                v-else-if="!homeCoverFailedMap[r.score_id]"
                class="home-score-cover"
                :src="homeCoverSrc(r.score_id)"
                :alt="`${r.title} 封面`"
                loading="lazy"
                @error="handleHomeCoverError(r.score_id)"
              />
              <div v-else class="home-score-cover home-score-cover-fallback">
                <span class="muted">封面加载失败</span>
                <button type="button" class="btn small" @click.stop="retryHomeCover(r.score_id)">重试</button>
              </div>
              <span class="home-score-title">{{ r.title }}</span>
            </button>
          </div>
        </div>
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

      <Transition name="score-slide-from-right" @after-enter="onScoreSlideAfterEnter">
        <section
          v-if="routeMode === 'score'"
          :key="scoreId || 'score'"
          class="card score-detail-page score-detail-page--slide-overlay"
        >
          <div class="score-detail-toolbar">
            <button type="button" class="btn small" @click="goAppTab('home')">返回</button>
          </div>
          <p v-if="scoreMissing" class="error">曲目不存在或已被删除，请返回首页重新选择。</p>
          <template v-else>
            <div class="score-detail-layout">
            <div class="score-detail-left">
              <template v-if="scoreImageError">
                <h2 class="score-detail-title">{{ currentScoreDisplayName }}</h2>
                <p class="error">{{ scoreImageError }}</p>
              </template>
              <div v-else-if="!scorePageList.length" class="score-detail-score-pane">
                <h2 class="score-detail-title">{{ currentScoreDisplayName }}</h2>
                <div class="score-pages-scroll">
                  <p class="muted score-detail-loading-hint">乐谱加载中…</p>
                </div>
              </div>
              <div v-else class="score-detail-score-pane">
                <h2 class="score-detail-title">{{ currentScoreDisplayName }}</h2>
                <div class="score-pages-scroll">
                  <div v-for="page in scorePageList" :key="page" class="score-page-item">
                    <img
                      v-if="!scorePageFailedMap[page]"
                      class="score-page-image"
                      :src="scorePageImageSrc(page)"
                      :alt="`第 ${page} 页`"
                      loading="lazy"
                      @error="handleScorePageError(page)"
                    />
                    <div v-else class="score-page-image score-page-fallback">
                      <span class="muted">第 {{ page }} 页加载失败</span>
                      <button type="button" class="btn small" @click="retryScorePage(page)">重试</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="score-detail-right">
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
                <p v-else class="muted">暂无画像</p>
              </div>
              <button type="button" class="btn primary score-detail-practice-btn" @click="startPracticeFromScore">
                开始练习
              </button>
            </div>
            </div>
          </template>
        </section>
      </Transition>

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
        <h2>练习记录</h2>
        <div class="form-row inline-row summary-profile-controls">
          <label>最近条数</label>
          <input v-model.number="summaryLastN" type="number" min="1" max="200" class="input-narrow" />
          <button type="button" class="btn small" :disabled="summaryLoading" @click="loadPracticeSummary">
            {{ summaryLoading ? '加载中…' : '刷新概况' }}
          </button>
        </div>
        <p v-if="summaryError" class="error">{{ summaryError }}</p>
        <div v-else-if="practiceSummary" class="summary-box">
          <p>
            <strong>窗口内会话数：</strong>{{ practiceSummary.window_sessions }}
            <span class="muted">（请求最近 {{ practiceSummary.last_n_requested }} 条）</span>
          </p>
          <p v-if="practiceSummary.latest_session_at" class="muted">
            最近一条时间：{{ practiceSummary.latest_session_at }}
          </p>
          <template v-if="practiceSummary.window_sessions > 0">
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
        <div class="summary-box summary-box--records">
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

      <section v-if="routeMode === 'app' && appTab === 'assistant'" class="card assistant-section">
        <div class="assistant-topbar">
          <div class="assistant-topbar-left">
            <button type="button" class="btn small" @click="goAppTab('home')">返回</button>
            <button
              v-if="scoreId && !assistantShowScorePanel"
              type="button"
              class="btn small"
              :disabled="assistantOverlayPhase !== 'idle'"
              @click="beginOpenScorePanelAnim"
            >
              显示乐谱
            </button>
          </div>
          <h2 class="assistant-header-title">keygent</h2>
          <div class="assistant-topbar-right">
            <button type="button" class="btn small" @click="refreshAssistantPanel">刷新</button>
          </div>
        </div>

        <input ref="assistantPdfInputEl" type="file" accept=".pdf" style="display: none" @change="onAssistantPdfPicked" />
        <input
          ref="assistantReferenceInputEl"
          type="file"
          accept=".musicxml,.xml,.mxl,.mid,.midi,audio/*"
          style="display: none"
          @change="onAssistantReferencePicked"
        />

        <div
          ref="assistantLayoutEl"
          class="assistant-layout"
          :class="{
            'assistant-layout--with-score': !!scoreId && assistantShowScorePanel,
            'assistant-layout--score-collapsed': !!scoreId && !assistantShowScorePanel,
          }"
        >
          <aside v-if="scoreId && assistantShowScorePanel" ref="assistantScorePaneEl" class="assistant-score-pane">
            <div class="assistant-score-pane-head">
              <strong>{{ currentScoreDisplayName }}</strong>
              <button
                type="button"
                class="assistant-close-btn"
                :disabled="assistantOverlayPhase !== 'idle'"
                @click="beginCloseScorePanelAnim"
              >
                ×
              </button>
            </div>
            <div class="assistant-score-scroll">
              <img
                v-for="page in scorePageList"
                :key="page"
                class="assistant-score-image"
                :src="scorePageImageSrc(page)"
                :alt="`第 ${page} 页`"
                loading="lazy"
              />
            </div>
          </aside>

          <div class="assistant-chat-slot">
            <div
              ref="assistantChatPaneEl"
              class="assistant-chat-pane"
              :class="{ 'assistant-chat-pane--overlay-active': assistantOverlayPhase !== 'idle' }"
              :style="assistantChatOverlayStyle || undefined"
            >
            <div class="assistant-plan" v-if="scoreId">
              <p><strong>练习设置</strong></p>
              <div class="inline-row">
                <button type="button" class="btn small" @click="pickAssistantPerformance">上传您的演奏</button>
                <span class="muted">{{ audioFile ? audioFile.name : '未选择' }}</span>
              </div>
              <div class="inline-row" style="margin-top: 0.45rem">
                <label class="muted">本次练习小节</label>
                <input v-model="focusStartMeasure" type="number" min="1" class="input-narrow" placeholder="起" />
                <span class="muted">到</span>
                <input v-model="focusEndMeasure" type="number" min="1" class="input-narrow" placeholder="止" />
              </div>
              <div class="inline-row" style="margin-top: 0.45rem">
                <button type="button" class="btn primary" :disabled="comparing || !audioFile" @click="runAssistantCompareFlow">
                  {{ comparing ? '比对中…' : '开始比对' }}
                </button>
              </div>
              <p v-if="compareError" class="error">{{ compareError }}</p>
              <input
                ref="assistantPerformanceInputEl"
                type="file"
                accept="audio/*,.wav,.mp3,.flac,.ogg,.mid,.midi"
                style="display: none"
                @change="onAssistantPerformancePicked"
              />
            </div>

            <div v-if="compareResult" class="assistant-plan">
              <p><strong>比对结果</strong></p>
              <p>准确率：{{ (compareResult.accuracy * 100).toFixed(1) }}% · 错音：{{ compareResult.errors?.length || 0 }}</p>
            </div>

            <div class="assistant-chat-shell">
              <div class="chat-box wechat-box" v-if="threadMessages.length">
                <div v-if="assistantEntryPromptVisible" class="chat-line chat-line-assistant">
                  <div class="chat-bubble system-card">
                    <p><strong>从一个曲目开始：</strong></p>
                    <div class="inline-row">
                      <button type="button" class="btn small" @click="goAppTab('home')">从曲库中选择</button>
                      <button type="button" class="btn small" @click="assistantUploadExpanded = !assistantUploadExpanded">
                        上传一个曲目
                      </button>
                    </div>
                    <div v-if="assistantUploadExpanded" class="assistant-upload-panel">
                      <div class="inline-row">
                        <button type="button" class="btn small" @click="pickAssistantPdf">上传 PDF 谱</button>
                        <span class="muted">{{ assistantPdfFile ? assistantPdfFile.name : '未选择' }}</span>
                      </div>
                      <div class="inline-row" style="margin-top: 0.45rem">
                        <button type="button" class="btn small" @click="pickAssistantReference">上传标准演奏音频</button>
                        <span class="muted">{{ assistantReferenceFile ? assistantReferenceFile.name : '未选择' }}</span>
                      </div>
                      <button
                        type="button"
                        class="btn primary"
                        style="margin-top: 0.6rem"
                        :disabled="assistantUploadingScore || !assistantPdfFile || !assistantReferenceFile"
                        @click="uploadAssistantScorePack"
                      >
                        {{ assistantUploadingScore ? '上传中…' : '确认上传曲目' }}
                      </button>
                      <p v-if="assistantUploadError" class="error">{{ assistantUploadError }}</p>
                    </div>
                  </div>
                </div>
                <div
                  v-for="m in displayedThreadMessages"
                  :key="m.id"
                  :class="['chat-line', m.role === 'user' ? 'chat-line-user' : 'chat-line-assistant']"
                >
                  <div class="chat-bubble">{{ m.content }}</div>
                </div>
                <div v-if="assistantSuggestion" class="chat-line chat-line-assistant">
                  <div class="chat-bubble"><pre>{{ assistantSuggestion }}</pre></div>
                </div>
                <div v-if="todayPlan" class="chat-line chat-line-assistant">
                  <div class="chat-bubble"><pre>{{ JSON.stringify(todayPlan, null, 2) }}</pre></div>
                </div>
                <div class="chat-line chat-line-assistant" v-if="scoreId">
                  <div class="chat-bubble action-card">
                    <div class="assistant-actions-in-chat">
                      <button type="button" class="btn primary" :disabled="assistantLoading" @click="loadAssistantSuggestion">
                        {{ assistantLoading ? '生成中…' : '生成建议' }}
                      </button>
                      <button type="button" class="btn primary" :disabled="todayPlanLoading" @click="loadTodayPlan">
                        {{ todayPlanLoading ? '生成中…' : '练习任务' }}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
              <div class="chat-box wechat-box" v-else>
                <div v-if="assistantEntryPromptVisible" class="chat-line chat-line-assistant">
                  <div class="chat-bubble system-card">
                    <p><strong>从一个曲目开始：</strong></p>
                    <div class="inline-row">
                      <button type="button" class="btn small" @click="goAppTab('home')">从曲库中选择</button>
                      <button type="button" class="btn small" @click="assistantUploadExpanded = !assistantUploadExpanded">
                        上传一个曲目
                      </button>
                    </div>
                    <div v-if="assistantUploadExpanded" class="assistant-upload-panel">
                      <div class="inline-row">
                        <button type="button" class="btn small" @click="pickAssistantPdf">上传 PDF 谱</button>
                        <span class="muted">{{ assistantPdfFile ? assistantPdfFile.name : '未选择' }}</span>
                      </div>
                      <div class="inline-row" style="margin-top: 0.45rem">
                        <button type="button" class="btn small" @click="pickAssistantReference">上传标准演奏音频</button>
                        <span class="muted">{{ assistantReferenceFile ? assistantReferenceFile.name : '未选择' }}</span>
                      </div>
                      <button
                        type="button"
                        class="btn primary"
                        style="margin-top: 0.6rem"
                        :disabled="assistantUploadingScore || !assistantPdfFile || !assistantReferenceFile"
                        @click="uploadAssistantScorePack"
                      >
                        {{ assistantUploadingScore ? '上传中…' : '确认上传曲目' }}
                      </button>
                      <p v-if="assistantUploadError" class="error">{{ assistantUploadError }}</p>
                    </div>
                  </div>
                </div>
                <div class="chat-line chat-line-assistant" v-else>
                  <div class="chat-bubble">暂无会话消息，发送第一条消息开始。</div>
                </div>
                <div class="chat-line chat-line-assistant" v-if="scoreId">
                  <div class="chat-bubble action-card">
                    <div class="assistant-actions-in-chat">
                      <button type="button" class="btn primary" :disabled="assistantLoading" @click="loadAssistantSuggestion">
                        {{ assistantLoading ? '生成中…' : '生成建议' }}
                      </button>
                      <button type="button" class="btn primary" :disabled="todayPlanLoading" @click="loadTodayPlan">
                        {{ todayPlanLoading ? '生成中…' : '练习任务' }}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
              <p v-if="assistantError" class="error">{{ assistantError }}</p>
              <p v-if="todayPlanError" class="error">{{ todayPlanError }}</p>
              <p v-if="chatError" class="error">{{ chatError }}</p>

              <div class="assistant-input-row">
                <input
                  v-model="chatInput"
                  class="score-id-input assistant-chat-input"
                  placeholder="和助手对话，回车或点击发送"
                  @keyup.enter="sendChat"
                />
                <button type="button" class="btn small" :disabled="chatLoading" @click="sendChat">
                  {{ chatLoading ? '发送中…' : '发送' }}
                </button>
              </div>
            </div>
            </div>
          </div>
        </div>
      </section>
    </main>
    </div>
    <nav v-if="routeMode === 'app'" class="bottom-tabs">
      <button :class="['tab-btn', appTab === 'home' ? 'active' : '']" @click="goAppTab('home')">首页·曲库</button>
      <button :class="['tab-btn', appTab === 'assistant' ? 'active' : '']" @click="goAppTab('assistant')">keygent</button>
      <button :class="['tab-btn', appTab === 'profile' ? 'active' : '']" @click="goAppTab('profile')">个人主页</button>
    </nav>
    <button
      type="button"
      class="login-intro-debug-btn onboarding-debug-btn"
      @click="replayPostRegisterOnboardingDebug"
    >
      调试：播放引导幻灯片
    </button>
    </div>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
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

function peekAuthToken() {
  try {
    return typeof localStorage !== 'undefined'
      ? String(localStorage.getItem('auth_token') || '').trim()
      : ''
  } catch {
    return ''
  }
}

const pdfFile = ref(null)
const musicxmlFile = ref(null)
const audioFile = ref(null)
const currentUserId = ref('default')
const currentAccount = ref('')
const authToken = ref(peekAuthToken())
const authAccountInput = ref('')
const authPasswordInput = ref('')
const loginPasswordInputEl = ref(null)
const authLoading = ref(false)
const authError = ref('')

/** 登录成功：先淡出登录层，再进入已登录页，与引导蒙层进入动画统一时长与曲线 */
const loginHandoffLeaveActive = ref(false)
const authAppHandoffEnterActive = ref(false)
const AUTH_HANDOFF_LEAVE_MS = 380
const AUTH_HANDOFF_LEAVE_MS_REDUCED = 90

async function waitLoginHandoffLeave() {
  loginHandoffLeaveActive.value = true
  let ms = AUTH_HANDOFF_LEAVE_MS
  try {
    if (typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      ms = AUTH_HANDOFF_LEAVE_MS_REDUCED
    }
  } catch {
    /* ignore */
  }
  await new Promise((resolve) => {
    window.setTimeout(resolve, ms)
  })
  loginHandoffLeaveActive.value = false
}

function onAuthAppHandoffEnterEnd(e) {
  if (e.target !== e.currentTarget) return
  const n = String(e.animationName || '')
  if (!n.includes('appAuthHandoffIn')) return
  authAppHandoffEnterActive.value = false
}

/** 首次注册成功后幻灯片；完成后写入 localStorage，同设备不再播放 */
const ONBOARDING_STORAGE_KEY = 'keygent_onboarding_slides_v1_done'
/** 测试用：true 时每次经 doAuthEntry 成功都播放引导且不写完成标记。正式逻辑为 false（仅首次注册路径 + localStorage）。 */
const ONBOARDING_PLAY_EVERY_LOGIN_TEST = false
const onboardingSlides = [
  {
    title: '欢迎使用 keygent',
    body:
      '底部三栏：首页·曲库（浏览与打开乐谱）、keygent（上传演奏、比对与智能助手）、个人主页（练习数据与记录）。',
    imageHint: '三栏导航',
  },
  {
    title: '主要使用流程',
    body:
      '① 曲库找谱并选定 → ② 进入 keygent、上传演奏 → ③ 比对后生成建议与练习任务 → ④ 多轮对话，持续细化练习。',
    imageHint: '流程示意',
  },
  {
    title: '首页·曲库',
    body: '可按曲名搜索，并用难度、能力标签筛选；点封面卡片即可打开乐谱。',
    imageHint: '曲库卡片',
  },
  {
    title: '乐谱页',
    body:
      '多页大图看谱，可缩放、拖拽查看细节；右侧可见曲目画像。点「开始练习」会带上本曲进入 keygent。',
    imageHint: '乐谱大图',
  },
  {
    title: 'keygent 与个人主页',
    body:
      '在 keygent 上传演奏并比对，查看准确率与错音；可与助手多轮对话，使用「生成建议」「练习任务」，也可上传 PDF 与参考演奏补充曲目。在个人主页查看练习摘要、薄弱小节与最近记录，并可管理已保存的练习音频。',
    imageHint: '助手与数据概览',
  },
]
const showPostRegisterOnboarding = ref(false)
const onboardingSlideIndex = ref(0)

function completePostRegisterOnboarding() {
  if (!ONBOARDING_PLAY_EVERY_LOGIN_TEST) {
    try {
      localStorage.setItem(ONBOARDING_STORAGE_KEY, '1')
    } catch {
      /* ignore */
    }
  }
  showPostRegisterOnboarding.value = false
}

/** 蒙层淡出结束后再复位页码、恢复滚动，避免关闭瞬间内容跳回第一页 */
function onOnboardingRootAfterLeave() {
  onboardingSlideIndex.value = 0
  if (typeof document !== 'undefined') document.body.style.overflow = ''
}

function openPostRegisterOnboardingIfNeeded(registeredNewUser) {
  if (ONBOARDING_PLAY_EVERY_LOGIN_TEST) {
    onboardingSlideIndex.value = 0
    showPostRegisterOnboarding.value = true
    return
  }
  if (!registeredNewUser) return
  try {
    if (localStorage.getItem(ONBOARDING_STORAGE_KEY) === '1') return
  } catch {
    return
  }
  onboardingSlideIndex.value = 0
  showPostRegisterOnboarding.value = true
}

function onboardingPrev() {
  if (onboardingSlideIndex.value > 0) {
    onboardingSlideIndex.value -= 1
  }
}

function onboardingNextOrFinish() {
  if (onboardingSlideIndex.value < onboardingSlides.length - 1) {
    onboardingSlideIndex.value += 1
  } else {
    completePostRegisterOnboarding()
  }
}

/** 页眉「帮助」与调试入口：打开引导幻灯片（不校验首次注册、不读 localStorage） */
function openHelpOnboarding() {
  onboardingSlideIndex.value = 0
  showPostRegisterOnboarding.value = true
}

function replayPostRegisterOnboardingDebug() {
  if (!authToken.value) return
  openHelpOnboarding()
}

/** 未登录开屏：prepare → splash（大图居中）→ fly（回卡片位）→ done；已登录为 done */
const LOGIN_INTRO_SPLASH_MS = 320
const LOGIN_INTRO_FLY_MS = 640
const LOGIN_INTRO_FLY_EASE = 'cubic-bezier(0.22, 1, 0.32, 1)'
const loginIntroPhase = ref(authToken.value ? 'done' : 'prepare')
const loginLogoSlotMinH = ref(null)
const loginCardMinH = ref(null)
const loginLogoFlyStyle = ref({})
const loginLogoImgRef = ref(null)
let loginIntroTimers = []
let loginIntroFlyEndCleanup = null

function clearLoginIntroTimers() {
  loginIntroTimers.forEach((id) => window.clearTimeout(id))
  loginIntroTimers = []
  if (loginIntroFlyEndCleanup) {
    loginIntroFlyEndCleanup()
    loginIntroFlyEndCleanup = null
  }
}

function finishLoginIntro() {
  loginIntroPhase.value = 'done'
  loginLogoFlyStyle.value = {}
  /* 保留 slot / 卡片 min-height，避免动画结束撤掉占位后白盒高度跳变 */
}

/** 调试用：强制播完整开屏（忽略 prefers-reduced-motion） */
function replayLoginIntroDebug() {
  if (authToken.value) return
  runLoginIntro({ force: true })
}

function runLoginIntro(opts = {}) {
  const forceAnim = opts.force === true
  if (typeof window === 'undefined') return
  if (authToken.value) {
    finishLoginIntro()
    return
  }
  if (!forceAnim) {
    try {
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        finishLoginIntro()
        return
      }
    } catch {
      finishLoginIntro()
      return
    }
  }

  clearLoginIntroTimers()
  loginIntroPhase.value = 'prepare'
  loginLogoFlyStyle.value = {}
  loginLogoSlotMinH.value = null

  nextTick(() => {
    requestAnimationFrame(() => {
      const img = loginLogoImgRef.value
      if (!img) {
        finishLoginIntro()
        return
      }
      const endRect = img.getBoundingClientRect()
      if (endRect.width < 4 || endRect.height < 4) {
        finishLoginIntro()
        return
      }

      const slotEl = img.parentElement
      const slotH = slotEl ? slotEl.getBoundingClientRect().height : endRect.height
      loginLogoSlotMinH.value = `${Math.ceil(slotH)}px`
      const cardEl = img.closest('.login-card')
      if (cardEl) {
        const h = cardEl.getBoundingClientRect().height
        if (h > 0) loginCardMinH.value = `${Math.ceil(h)}px`
      }
      const splashW = Math.min(300, Math.max(200, window.innerWidth * 0.5))
      const startCenterY = window.innerHeight / 2
      const endCenterY = endRect.top + endRect.height / 2

      loginLogoFlyStyle.value = {
        position: 'fixed',
        left: '50%',
        top: `${startCenterY}px`,
        width: `${splashW}px`,
        transform: 'translate(-50%, -50%)',
        zIndex: '100',
        transition: 'none',
      }
      loginIntroPhase.value = 'splash'
      void img.offsetWidth

      loginIntroTimers.push(
        window.setTimeout(() => {
          loginIntroPhase.value = 'fly'
          loginLogoFlyStyle.value = {
            position: 'fixed',
            left: '50%',
            top: `${endCenterY}px`,
            width: `${endRect.width}px`,
            transform: 'translate(-50%, -50%)',
            zIndex: '100',
            transition: `top ${LOGIN_INTRO_FLY_MS}ms ${LOGIN_INTRO_FLY_EASE}, width ${LOGIN_INTRO_FLY_MS}ms ${LOGIN_INTRO_FLY_EASE}`,
          }

          let settled = false
          let flyDoneTimer = null
          const onTrans = (e) => {
            if (e.target !== img) return
            if (!['top', 'width'].includes(e.propertyName)) return
            settle()
          }
          const settle = () => {
            if (settled) return
            settled = true
            if (flyDoneTimer != null) {
              window.clearTimeout(flyDoneTimer)
              flyDoneTimer = null
            }
            img.removeEventListener('transitionend', onTrans)
            loginIntroFlyEndCleanup = null
            finishLoginIntro()
          }
          loginIntroFlyEndCleanup = () => {
            img.removeEventListener('transitionend', onTrans)
          }
          img.addEventListener('transitionend', onTrans)
          flyDoneTimer = window.setTimeout(settle, LOGIN_INTRO_FLY_MS + 100)
          loginIntroTimers.push(flyDoneTimer)
        }, LOGIN_INTRO_SPLASH_MS),
      )
    })
  })
}
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
/** 从曲库进乐谱时短暂保留曲库 DOM，供滑入层覆盖 */
const libraryUnderlayForScore = ref(false)
const showLibraryUnderScoreSlide = computed(
  () =>
    (routeMode.value === 'app' && appTab.value === 'home') || libraryUnderlayForScore.value,
)

function onScoreSlideAfterEnter() {
  libraryUnderlayForScore.value = false
}
const isAuthenticated = computed(() => Boolean(authToken.value))
watch(isAuthenticated, (ok, was) => {
  if (!ok) {
    if (typeof document !== 'undefined') document.body.style.overflow = ''
    showPostRegisterOnboarding.value = false
    onboardingSlideIndex.value = 0
    loginHandoffLeaveActive.value = false
    authAppHandoffEnterActive.value = false
  }
  if (ok) {
    clearLoginIntroTimers()
    loginCardMinH.value = null
    loginLogoSlotMinH.value = null
    finishLoginIntro()
    return
  }
  if (was) {
    loginIntroPhase.value = 'prepare'
    nextTick(() => runLoginIntro())
  }
})

watch(showPostRegisterOnboarding, (open) => {
  if (typeof document === 'undefined') return
  if (open) document.body.style.overflow = 'hidden'
})
const chatLoading = ref(false)
const chatError = ref('')
const chatInput = ref('')
const threadMessages = ref([])
const showAllThreadMessages = ref(false)
const displayedThreadMessages = computed(() => (
  showAllThreadMessages.value ? threadMessages.value : threadMessages.value.slice(-12)
))
const difficultyOptions = ['beginner', 'intermediate', 'advanced', 'expert']
const homeSearchInput = ref('')
const showHomeFilters = ref(false)
const homeCoverRetryMap = ref({})
const homeCoverFailedMap = ref({})
const scoreMissing = ref(false)
const scorePageRetryMap = ref({})
const scorePageFailedMap = ref({})
const assistantEntryPromptVisible = ref(true)
const assistantUploadExpanded = ref(false)
const assistantPdfFile = ref(null)
const assistantReferenceFile = ref(null)
const assistantUploadError = ref('')
const assistantUploadingScore = ref(false)
const assistantShowScorePanel = ref(true)
/** 乐谱收起/展开：先右栏覆盖延伸，再卸载乐谱；与 CSS 时长一致 */
const ASSISTANT_SCORE_ANIM_MS = 520
const assistantLayoutEl = ref(null)
const assistantScorePaneEl = ref(null)
const assistantChatPaneEl = ref(null)
const assistantOverlayPhase = ref('idle')
const assistantChatOverlayStyle = ref(null)
let assistantOverlayClearTimer = null
function clearAssistantOverlayTimer() {
  if (assistantOverlayClearTimer != null) {
    window.clearTimeout(assistantOverlayClearTimer)
    assistantOverlayClearTimer = null
  }
}
const assistantPdfInputEl = ref(null)
const assistantReferenceInputEl = ref(null)
const assistantPerformanceInputEl = ref(null)

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
  if (low.includes('timeout') || low.includes('timed out') || low.includes('超时')) {
    return '请求超时，请稍后重试。'
  }
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

function withTimeout(promise, timeoutMs = 10000, timeoutMessage = '请求超时') {
  let timer = null
  return Promise.race([
    promise,
    new Promise((_, reject) => {
      timer = window.setTimeout(() => reject(new Error(timeoutMessage)), timeoutMs)
    }),
  ]).finally(() => {
    if (timer) window.clearTimeout(timer)
  })
}

function normalizeAuthText(text) {
  return String(text || '').trim().toLowerCase()
}

function canAutoRegisterFromLoginError(messageText) {
  const low = normalizeAuthText(messageText)
  return (
    low.includes('用户不存在')
    || low.includes('账号不存在')
    || low.includes('account not found')
    || low.includes('user not found')
    || low.includes('not found')
  )
}

function validateAuthInput() {
  const account = String(authAccountInput.value || '').trim()
  const password = String(authPasswordInput.value || '')
  if (!account) throw new Error('账号为空，请填写用户名。')
  if (!password) throw new Error('密码为空，请填写密码。')
  if (account.length < 3 || account.length > 128) {
    throw new Error('账号长度不合法，需为 3-128 位。')
  }
  if (password.length < 6 || password.length > 128) {
    throw new Error('密码长度不合法，需为 6-128 位。')
  }
  return { account, password }
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
const scorePageList = computed(() => {
  const n = Number(scorePageCount.value) || 0
  if (n <= 0) return []
  return Array.from({ length: n }, (_, i) => i + 1)
})

/** 曲库列表占位卡片（仅前端展示密度，不参与接口；点击不进入乐谱） */
const HOME_SCORE_LIBRARY_PLACEHOLDERS = Array.from({ length: 10 }, (_, i) => ({
  score_id: `__placeholder_${i + 1}`,
  title: `【占位 ${i + 1}】演示曲目`,
  isPlaceholder: true,
}))

const homeScoreCards = computed(() => {
  if (!Array.isArray(scoreLibraryRows.value)) return []
  const real = scoreLibraryRows.value
    .filter((r) => String(r?.score_id || '').trim())
    .map((r) => ({
      score_id: String(r.score_id),
      title: scoreDisplayNameByRow(r),
      isPlaceholder: false,
    }))
  return [...real, ...HOME_SCORE_LIBRARY_PLACEHOLDERS]
})
const hasHomeFilterApplied = computed(() => (
  Boolean(String(homeSearchInput.value || '').trim())
  || Boolean(String(scoreFilterDifficulty.value || '').trim())
  || Boolean(String(scoreFilterAbility.value || '').trim())
))

function normalizeAppTab(tab) {
  const t = String(tab || '').toLowerCase()
  if (t === 'library') return 'home'
  if (t === 'practice') return 'assistant'
  return ['home', 'assistant', 'profile'].includes(t) ? t : 'home'
}

function parseHashRoute() {
  if (!authToken.value) {
    libraryUnderlayForScore.value = false
    routeMode.value = 'auth'
    routePathLabel.value = '/login'
    return
  }
  const hash = String(window.location.hash || '')
  if (hash === '#/admin') {
    // Admin 为独立入口；file:// 下不能用根路径 /admin.html，需相对当前页面解析
    window.location.replace(new URL('admin.html', window.location.href).href)
    return
  }
  const appTabMatch = hash.match(/^#\/app\/([a-zA-Z0-9_-]+)/)
  if (appTabMatch && appTabMatch[1]) {
    libraryUnderlayForScore.value = false
    routeMode.value = 'app'
    appTab.value = normalizeAppTab(appTabMatch[1])
    routePathLabel.value = `/app/${appTab.value}`
    return
  }
  if (hash === '#/app' || hash === '#/' || hash === '') {
    libraryUnderlayForScore.value = false
    routeMode.value = 'app'
    appTab.value = 'home'
    routePathLabel.value = '/app/home'
    return
  }
  const m = hash.match(/^#\/score\/([^/?#]+)/)
  if (m && m[1]) {
    const fromHomeLibrary =
      routeMode.value === 'app' && appTab.value === 'home'
    if (fromHomeLibrary) {
      libraryUnderlayForScore.value = true
    }
    routeMode.value = 'score'
    const sid = decodeURIComponent(m[1])
    scoreId.value = sid
    manualScoreId.value = sid
    routePathLabel.value = `/score/${sid}`
    addRecentScore(sid)
    return
  }
  libraryUnderlayForScore.value = false
  routePathLabel.value = '/'
}

function goHome() {
  if (!authToken.value) {
    parseHashRoute()
    return
  }
  window.location.hash = '#/app/home'
}

function goApp() {
  if (!authToken.value) {
    parseHashRoute()
    return
  }
  window.location.hash = '#/app/home'
}

function goAppTab(tab) {
  if (!authToken.value) {
    parseHashRoute()
    return
  }
  const safe = normalizeAppTab(tab)
  window.location.hash = `#/app/${safe}`
}

async function searchHomeScores() {
  await loadScoreLibrary(homeSearchInput.value)
}

async function applyHomeFilters() {
  showHomeFilters.value = false
  await loadScoreLibrary(homeSearchInput.value)
}

function scorePageImageSrc(page) {
  if (!scoreId.value) return ''
  const base = getScoreImageUrl(scoreId.value, page)
  const tick = Number(scorePageRetryMap.value[page] || 0)
  if (!tick) return base
  const sep = base.includes('?') ? '&' : '?'
  return `${base}${sep}retry=${tick}`
}

function handleScorePageError(page) {
  scorePageFailedMap.value = { ...scorePageFailedMap.value, [page]: true }
}

function retryScorePage(page) {
  const next = Number(scorePageRetryMap.value[page] || 0) + 1
  scorePageRetryMap.value = { ...scorePageRetryMap.value, [page]: next }
  scorePageFailedMap.value = { ...scorePageFailedMap.value, [page]: false }
}

function startPracticeFromScore() {
  if (!scoreId.value) return
  assistantEntryPromptVisible.value = false
  assistantShowScorePanel.value = true
  goAppTab('assistant')
}

function refreshAssistantPanel() {
  chatInput.value = ''
  chatError.value = ''
  compareError.value = ''
  compareResult.value = null
  assistantError.value = ''
  assistantSuggestion.value = ''
  todayPlanError.value = ''
  todayPlan.value = null
  threadMessages.value = []
}

function parseAssistantLayoutGapPx(layoutEl) {
  const s = getComputedStyle(layoutEl)
  const g = s.columnGap && s.columnGap !== 'normal' ? s.columnGap : s.gap
  const m = String(g || '').match(/([\d.]+)px/)
  return m ? parseFloat(m[1]) : 13.6
}

function beginCloseScorePanelAnim() {
  if (!scoreId.value || !assistantShowScorePanel.value || assistantOverlayPhase.value !== 'idle') return
  clearAssistantOverlayTimer()
  assistantOverlayPhase.value = 'closing'
  nextTick(() => {
    requestAnimationFrame(() => {
      const layout = assistantLayoutEl.value
      const chat = assistantChatPaneEl.value
      if (!layout || !chat) {
        assistantShowScorePanel.value = false
        assistantOverlayPhase.value = 'idle'
        assistantChatOverlayStyle.value = null
        return
      }
      const lr = layout.getBoundingClientRect()
      const cr = chat.getBoundingClientRect()
      const top = cr.top - lr.top
      const left = cr.left - lr.left
      const right = lr.right - cr.right
      const h = cr.height
      const ease = 'cubic-bezier(0.18, 0.88, 0.22, 1)'
      assistantChatOverlayStyle.value = {
        position: 'absolute',
        top: `${top}px`,
        left: `${left}px`,
        right: `${right}px`,
        height: `${h}px`,
        zIndex: 3,
        boxSizing: 'border-box',
      }
      requestAnimationFrame(() => {
        assistantChatOverlayStyle.value = {
          position: 'absolute',
          top: `${top}px`,
          left: '0px',
          right: '0px',
          height: `${h}px`,
          zIndex: 3,
          boxSizing: 'border-box',
          transition: `left ${ASSISTANT_SCORE_ANIM_MS}ms ${ease}, right ${ASSISTANT_SCORE_ANIM_MS}ms ${ease}`,
        }
      })
    })
  })
  assistantOverlayClearTimer = window.setTimeout(() => {
    assistantOverlayClearTimer = null
    assistantShowScorePanel.value = false
    assistantOverlayPhase.value = 'idle'
    assistantChatOverlayStyle.value = null
  }, ASSISTANT_SCORE_ANIM_MS + 40)
}

function beginOpenScorePanelAnim() {
  if (!scoreId.value || assistantShowScorePanel.value || assistantOverlayPhase.value !== 'idle') return
  clearAssistantOverlayTimer()
  assistantOverlayPhase.value = 'opening'
  assistantShowScorePanel.value = true
  const ease = 'cubic-bezier(0.18, 0.88, 0.22, 1)'
  nextTick(() => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        const layout = assistantLayoutEl.value
        const aside = assistantScorePaneEl.value
        const chat = assistantChatPaneEl.value
        if (!layout || !aside || !chat) {
          assistantOverlayPhase.value = 'idle'
          assistantChatOverlayStyle.value = null
          return
        }
        const lr = layout.getBoundingClientRect()
        const ar = aside.getBoundingClientRect()
        const cr = chat.getBoundingClientRect()
        const gap = parseAssistantLayoutGapPx(layout)
        const endLeft = ar.right - lr.left + gap
        const top = cr.top - lr.top
        const h = cr.height
        assistantChatOverlayStyle.value = {
          position: 'absolute',
          top: `${top}px`,
          left: '0px',
          right: '0px',
          height: `${h}px`,
          zIndex: 3,
          boxSizing: 'border-box',
          transition: 'none',
        }
        void chat.offsetHeight
        requestAnimationFrame(() => {
          assistantChatOverlayStyle.value = {
            position: 'absolute',
            top: `${top}px`,
            left: `${endLeft}px`,
            right: '0px',
            height: `${h}px`,
            zIndex: 3,
            boxSizing: 'border-box',
            transition: `left ${ASSISTANT_SCORE_ANIM_MS}ms ${ease}, right ${ASSISTANT_SCORE_ANIM_MS}ms ${ease}`,
          }
        })
      })
    })
  })
  assistantOverlayClearTimer = window.setTimeout(() => {
    assistantOverlayClearTimer = null
    assistantOverlayPhase.value = 'idle'
    assistantChatOverlayStyle.value = null
  }, ASSISTANT_SCORE_ANIM_MS + 40)
}

function pickAssistantPdf() {
  assistantPdfInputEl.value?.click()
}

function pickAssistantReference() {
  assistantReferenceInputEl.value?.click()
}

function onAssistantPdfPicked(e) {
  assistantPdfFile.value = e?.target?.files?.[0] || null
}

function onAssistantReferencePicked(e) {
  assistantReferenceFile.value = e?.target?.files?.[0] || null
}

function pickAssistantPerformance() {
  assistantPerformanceInputEl.value?.click()
}

function onAssistantPerformancePicked(e) {
  audioFile.value = e?.target?.files?.[0] || null
}

function isMusicxmlFilename(name) {
  const n = String(name || '').toLowerCase()
  return n.endsWith('.musicxml') || n.endsWith('.xml') || n.endsWith('.mxl')
}

async function uploadAssistantScorePack() {
  assistantUploadError.value = ''
  if (!assistantPdfFile.value || !assistantReferenceFile.value) {
    assistantUploadError.value = '请先上传 PDF 谱和标准演奏文件。'
    return
  }
  if (!isMusicxmlFilename(assistantReferenceFile.value.name)) {
    assistantUploadError.value = '当前后端仅支持 MusicXML 作为标准演奏文件，请上传 .musicxml/.xml/.mxl。'
    return
  }
  assistantUploadingScore.value = true
  try {
    const res = await uploadScore(assistantPdfFile.value, assistantReferenceFile.value, '')
    scoreId.value = res.score_id
    assistantEntryPromptVisible.value = false
    assistantUploadExpanded.value = false
    assistantShowScorePanel.value = true
    assistantPdfFile.value = null
    assistantReferenceFile.value = null
  } catch (e) {
    assistantUploadError.value = friendlyErrorMessage(e, '上传曲目失败')
  } finally {
    assistantUploadingScore.value = false
  }
}

async function runAssistantCompareFlow() {
  await doCompare()
  if (!compareError.value && compareResult.value) {
    await Promise.all([
      loadAssistantSuggestion(),
      loadTodayPlan(),
    ])
  }
}

async function clearHomeFilters() {
  homeSearchInput.value = ''
  scoreFilterDifficulty.value = ''
  scoreFilterAbility.value = ''
  showHomeFilters.value = false
  await loadScoreLibrary('')
}

function homeCoverSrc(scoreId) {
  const id = String(scoreId || '').trim()
  const base = getScoreImageUrl(id, 1)
  const retryTick = Number(homeCoverRetryMap.value[id] || 0)
  if (!retryTick) return base
  const sep = base.includes('?') ? '&' : '?'
  return `${base}${sep}retry=${retryTick}`
}

function handleHomeCoverError(scoreId) {
  const id = String(scoreId || '').trim()
  if (!id) return
  homeCoverFailedMap.value = { ...homeCoverFailedMap.value, [id]: true }
}

function retryHomeCover(scoreId) {
  const id = String(scoreId || '').trim()
  if (!id) return
  const nextTick = Number(homeCoverRetryMap.value[id] || 0) + 1
  homeCoverRetryMap.value = { ...homeCoverRetryMap.value, [id]: nextTick }
  homeCoverFailedMap.value = { ...homeCoverFailedMap.value, [id]: false }
}

function goScore(sid) {
  if (!authToken.value) {
    parseHashRoute()
    return
  }
  if (!sid) return
  if (String(sid).startsWith('__placeholder_')) return
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
    await waitLoginHandoffLeave()
    authToken.value = res.access_token || ''
    applyLoggedInUser(res.user)
    setAuthToken(authToken.value)
    localStorage.setItem('auth_token', authToken.value)
    authAppHandoffEnterActive.value = true
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
    await waitLoginHandoffLeave()
    authToken.value = res.access_token || ''
    applyLoggedInUser(res.user)
    setAuthToken(authToken.value)
    localStorage.setItem('auth_token', authToken.value)
    authAppHandoffEnterActive.value = true
  } catch (e) {
    authError.value = friendlyErrorMessage(e, '登录失败')
  } finally {
    authLoading.value = false
  }
}

function focusLoginPassword() {
  loginPasswordInputEl.value?.focus()
}

async function doAuthEntry() {
  authLoading.value = true
  authError.value = ''
  try {
    const { account, password } = validateAuthInput()
    const healthy = await withTimeout(checkBackendHealth(), 8000, '后端健康检查超时')
    if (!healthy) throw new Error('无法连接后端（/health 不通）')
    let res = null
    let cameThroughRegister = false
    try {
      res = await withTimeout(authLogin(account, password), 12000, '登录请求超时')
    } catch (e) {
      // 优先自动注册再登录：即使登录返回“账号或密码错误”，也尝试注册一次。
      try {
        await withTimeout(authRegister(account, password), 12000, '注册请求超时')
        cameThroughRegister = true
        res = await withTimeout(authLogin(account, password), 12000, '登录请求超时')
      } catch (registerErr) {
        if (canAutoRegisterFromLoginError(e?.message)) {
          throw e
        }
        const registerMsg = String(registerErr?.message || '').toLowerCase()
        if (
          registerMsg.includes('已存在')
          || registerMsg.includes('already exists')
          || registerMsg.includes('account exists')
          || registerMsg.includes('409')
        ) {
          throw e
        }
        throw registerErr
      }
    }
    if (!res?.access_token) throw new Error('登录状态异常，请重试。')
    await waitLoginHandoffLeave()
    authToken.value = res.access_token
    applyLoggedInUser(res.user)
    setAuthToken(authToken.value)
    localStorage.setItem('auth_token', authToken.value)
    authAppHandoffEnterActive.value = true
    goAppTab('home')
    await Promise.all([
      loadScoreLibrary(),
      loadPracticeSummary(),
      loadPracticeSessionsList(),
      loadAssistantThread(),
    ])
    openPostRegisterOnboardingIfNeeded(cameThroughRegister)
  } catch (e) {
    authError.value = friendlyErrorMessage(e, '登录/注册失败')
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
    loginHandoffLeaveActive.value = false
    authAppHandoffEnterActive.value = false
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
    parseHashRoute()
  }
}

async function doLogoutWithConfirm() {
  const ok = window.confirm('确认退出登录吗？')
  if (!ok) return
  await doLogout()
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
    const lastN = Math.min(100, Math.max(1, Number(summaryLastN.value) || 20))
    const res = await suggestAssistant({
      userId: currentUserId.value,
      scoreId: null,
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
    await sendAssistantMessage({
      userId: currentUserId.value,
      content,
      scoreId: null,
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
    const lastN = Math.min(100, Math.max(1, Number(summaryLastN.value) || 20))
    todayPlan.value = await getTodayPlan({
      userId: currentUserId.value,
      scoreId: null,
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
    practiceSummary.value = await getPracticeSummary(currentUserId.value, {
      scoreId: null,
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
    const res = await getPracticeSessions(currentUserId.value, 30, null)
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
        parseHashRoute()
        return Promise.all([
          loadScoreLibrary(),
          loadPracticeSummary(),
          loadPracticeSessionsList(),
          loadAssistantThread(),
        ])
      })
      .catch(() => {
        authToken.value = ''
        currentAccount.value = ''
        setAuthToken('')
        localStorage.removeItem('auth_token')
        parseHashRoute()
      })
    return
  }
  parseHashRoute()
  nextTick(() => runLoginIntro())
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

watch([appTab, routeMode], ([tab, mode]) => {
  if (mode === 'app' && tab === 'assistant') {
    assistantEntryPromptVisible.value = !scoreId.value
    if (scoreId.value) assistantShowScorePanel.value = true
  }
})

onBeforeUnmount(() => {
  clearLoginIntroTimers()
  clearAssistantOverlayTimer()
  assistantChatOverlayStyle.value = null
  assistantOverlayPhase.value = 'idle'
  window.removeEventListener('hashchange', parseHashRoute)
  if (backendHealthTimer) {
    clearInterval(backendHealthTimer)
    backendHealthTimer = null
  }
})

watch(scoreId, async (id) => {
  clearAssistantOverlayTimer()
  assistantChatOverlayStyle.value = null
  assistantOverlayPhase.value = 'idle'
  techniques.value = null
  techniquesError.value = ''
  scoreImageError.value = ''
  scorePageCount.value = 0
  scorePage.value = 1
  scoreMissing.value = false
  scorePageRetryMap.value = {}
  scorePageFailedMap.value = {}
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
    const msg = String(e?.message || '')
    if (msg.includes('404') || msg.toLowerCase().includes('not found')) {
      scoreMissing.value = true
      scoreImageError.value = ''
    } else {
      scoreImageError.value = msg || '乐谱页加载失败，请稍后重试。'
    }
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
  --auth-handoff-dur: 0.38s;
  --auth-handoff-ease: cubic-bezier(0.22, 1, 0.32, 1);
}
.login-shell {
  min-height: 100vh;
  min-height: 100dvh;
  transition:
    opacity var(--auth-handoff-dur) ease,
    transform var(--auth-handoff-dur) var(--auth-handoff-ease);
}
.login-shell--handoff-leave {
  opacity: 0;
  transform: translateY(-12px);
  pointer-events: none;
}
@media (prefers-reduced-motion: reduce) {
  .login-shell {
    transition-duration: 0.12s;
  }
  .login-shell--handoff-leave {
    transform: none;
  }
}
@keyframes appAuthHandoffIn {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.app-authenticated--handoff-enter {
  animation: appAuthHandoffIn var(--auth-handoff-dur) var(--auth-handoff-ease) forwards;
}
@media (prefers-reduced-motion: reduce) {
  .app-authenticated--handoff-enter {
    animation-duration: 0.12s;
  }
  @keyframes appAuthHandoffIn {
    from {
      opacity: 0.55;
    }
    to {
      opacity: 1;
    }
  }
}
.app-authenticated {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  min-height: 100dvh;
  height: 100vh;
  height: 100dvh;
  overflow: hidden;
}
.app-authenticated > .header {
  flex-shrink: 0;
}
.app-body-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  overscroll-behavior-y: contain;
}
/* 首页·曲库：禁止外层滚动，仅曲目列表区域滚动 */
.app-body-scroll--home-locked {
  overflow: hidden;
  overscroll-behavior: none;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.main--home-fill {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.main--home-fill > .library-home-section {
  flex: 1 1 auto;
  min-height: 0;
  margin-bottom: 0;
}
.login-main {
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  background: #f5f5f5;
}
.login-main--intro-active {
  align-items: center;
}
.login-card {
  width: min(460px, 100%);
  background: #fff;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
  box-sizing: border-box;
}
.login-logo-slot {
  position: relative;
}
.login-logo {
  width: min(180px, 52%);
  display: block;
  margin: 0 auto 0.7rem auto;
  transform-origin: center center;
}
.login-rest {
  opacity: 0;
  transform: translateY(14px);
  pointer-events: none;
  transition: none;
}
.login-rest.login-rest--intro-show {
  opacity: 1;
  transform: translateY(0);
  pointer-events: auto;
  transition:
    opacity 0.48s ease,
    transform 0.55s cubic-bezier(0.22, 1, 0.32, 1);
}
/* TODO: 开屏动画调完后删除 */
.login-intro-debug-btn {
  position: fixed;
  left: 50%;
  bottom: max(1rem, env(safe-area-inset-bottom, 0px));
  transform: translateX(-50%);
  z-index: 200;
  padding: 0.4rem 0.75rem;
  font-size: 0.82rem;
  color: #64748b;
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.08);
  cursor: pointer;
}
.login-intro-debug-btn:hover {
  color: #0f172a;
  border-color: #94a3b8;
}
/* 已登录底栏 58px，调试按钮抬高避免遮挡 */
.onboarding-debug-btn {
  bottom: calc(58px + max(0.75rem, env(safe-area-inset-bottom, 0px)));
}
.login-title {
  margin: 0 0 0.35rem 0;
  text-align: center;
  font-size: 1.7rem;
}
.login-sub {
  text-align: center;
  margin-bottom: 1rem;
}
.login-input {
  width: 100%;
  min-width: 0;
}
.hint-line {
  margin: 0.35rem 0 0 0;
  font-size: 0.85rem;
}
.login-btn {
  width: 100%;
}

/* 首次注册后：使用说明幻灯片（与登录卡片风格对齐） */
.onboarding-root {
  position: fixed;
  inset: 0;
  z-index: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: max(1rem, env(safe-area-inset-top, 0px)) max(1rem, env(safe-area-inset-right, 0px))
    max(1rem, env(safe-area-inset-bottom, 0px)) max(1rem, env(safe-area-inset-left, 0px));
  box-sizing: border-box;
  pointer-events: auto;
}
.onboarding-root-enter-active,
.onboarding-root-leave-active {
  transition:
    opacity var(--auth-handoff-dur) ease,
    transform var(--auth-handoff-dur) var(--auth-handoff-ease);
}
.onboarding-root-leave-active {
  pointer-events: none;
}
.onboarding-root-enter-from,
.onboarding-root-leave-to {
  opacity: 0;
  transform: translateY(12px);
}
@media (prefers-reduced-motion: reduce) {
  .onboarding-root-enter-active,
  .onboarding-root-leave-active {
    transition-duration: 0.12s;
  }
  .onboarding-root-enter-from,
  .onboarding-root-leave-to {
    transform: none;
  }
}
.onboarding-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(4px);
}
.onboarding-card {
  position: relative;
  width: min(460px, 100%);
  max-height: min(90vh, 640px);
  overflow: auto;
  background: #fff;
  border-radius: 12px;
  padding: 1.25rem 1.5rem 1.35rem;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.12);
  box-sizing: border-box;
}
.onboarding-welcome-strip {
  margin: 0 0 0.75rem 0;
  font-size: 0.82rem;
  color: #64748b;
  text-align: center;
}
.onboarding-slide-inner {
  min-height: 300px;
}
.onboarding-visual {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  margin-bottom: 1.75rem;
  border-radius: 10px;
  background: linear-gradient(145deg, #f1f5f9 0%, #e2e8f0 100%);
  color: #94a3b8;
  font-size: 0.9rem;
  text-align: center;
  padding: 1.5rem 1.25rem;
  box-sizing: border-box;
}
.onboarding-slide-title {
  margin: 0 0 0.5rem 0;
  font-size: 1.25rem;
  line-height: 1.35;
  color: #0f172a;
  text-align: center;
}
.onboarding-slide-body {
  margin: 0;
  font-size: 0.95rem;
  line-height: 1.55;
  color: #475569;
  text-align: center;
}
.onboarding-dots {
  display: flex;
  justify-content: center;
  gap: 0.45rem;
  margin: 1.15rem 0 0.85rem;
}
.onboarding-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #cbd5e1;
  transition: background 0.2s ease, transform 0.2s ease;
}
.onboarding-dot--active {
  background: #1a1a2e;
  transform: scale(1.15);
}
.onboarding-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
}
.onboarding-skip {
  border: none;
  background: transparent;
  color: #64748b;
  font-size: 0.9rem;
  cursor: pointer;
  padding: 0.35rem 0.25rem;
}
.onboarding-skip:hover {
  color: #0f172a;
}
.onboarding-footer-nav {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.onboarding-prev:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.onboarding-next {
  min-width: 7.5rem;
}
.onboarding-slide-enter-active,
.onboarding-slide-leave-active {
  transition:
    opacity 0.28s ease,
    transform 0.32s cubic-bezier(0.22, 1, 0.32, 1);
}
.onboarding-slide-enter-from {
  opacity: 0;
  transform: translateY(10px);
}
.onboarding-slide-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
@media (prefers-reduced-motion: reduce) {
  .onboarding-slide-enter-active,
  .onboarding-slide-leave-active {
    transition: opacity 0.12s ease;
  }
  .onboarding-slide-enter-from,
  .onboarding-slide-leave-to {
    transform: none;
  }
  .onboarding-dot {
    transition: none;
  }
}

.header {
  background: #1a1a2e;
  color: #eee;
  padding: 1.25rem 2rem;
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem 1rem;
}
.header-main {
  min-width: 0;
  flex: 1 1 auto;
}
.header-main .error {
  margin-top: 0.35rem;
  margin-bottom: 0;
}
.header h1 {
  margin: 0 0 0.25rem 0;
  font-size: 1.75rem;
}
.header .sub {
  margin: 0;
  font-size: 0.9rem;
  opacity: 0.85;
}
.header-help-btn {
  flex-shrink: 0;
  margin: 0;
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(255, 255, 255, 0.35);
  color: inherit;
}
.header-help-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.5);
  color: inherit;
}
.main {
  max-width: 1000px;
  margin: 0 auto;
  padding: 1.5rem;
}
.home-search-row {
  display: flex;
  gap: 0.6rem;
  align-items: center;
  flex-wrap: wrap;
}
.home-search-input {
  flex: 1;
  min-width: 0;
}
.home-filter-panel {
  margin-top: 0.75rem;
  padding: 0.7rem 0.8rem;
  background: #f8fafc;
  border: 1px solid #dbeafe;
  border-radius: 8px;
}
.home-score-grid {
  margin-top: 0.9rem;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 0.9rem;
}
.home-score-card {
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  text-align: left;
  padding: 0.5rem;
}
.home-score-card:hover {
  border-color: #93c5fd;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.12);
}
.home-score-cover {
  width: 100%;
  aspect-ratio: 3 / 4;
  object-fit: cover;
  border-radius: 6px;
  background: #f1f5f9;
}
.home-score-cover-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 0.4rem;
  border: 1px dashed #cbd5e1;
  background: #f8fafc;
}
.home-score-title {
  margin-top: 0.45rem;
  display: block;
  color: #0f172a;
  font-size: 0.92rem;
}
.score-detail-page {
  /* 关键：锁住外层滚动，只让左侧谱面滚动 */
  height: calc(100vh - 240px);
  min-height: 520px;
  overflow: hidden;
}
/* 从曲库滑入覆盖：固定层 + 内层布局可伸缩 */
.score-detail-page.score-detail-page--slide-overlay {
  position: fixed;
  top: 5.75rem;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 40;
  width: 100%;
  max-width: 1000px;
  margin: 0 auto;
  padding: 0.75rem 1.5rem 1.5rem;
  box-sizing: border-box;
  height: auto;
  min-height: 0;
  max-height: none;
  overflow-x: hidden;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  /* 不单独设背景，沿用 .card 的 #fff，与曲库白卡片一致 */
  box-shadow: -8px 0 32px rgba(15, 23, 42, 0.12);
  border-radius: 0;
  display: flex;
  flex-direction: column;
}
.score-detail-page--slide-overlay .score-detail-layout {
  flex: 1;
  min-height: 0;
  height: auto !important;
}
.score-detail-toolbar {
  flex-shrink: 0;
  margin-bottom: 0.15rem;
}
.score-detail-page h2.score-detail-title {
  margin: 0 0 0.75rem 0;
  font-size: clamp(1.15rem, 2vw, 1.38rem);
  line-height: 1.32;
  font-weight: 600;
  color: #0f172a;
  letter-spacing: -0.02em;
}
.score-detail-score-pane > .score-detail-title {
  flex-shrink: 0;
  margin: 0 0 0.5rem 0;
  padding: 0 0.08rem;
}
.score-detail-left > .score-detail-title {
  margin: 0 0 0.5rem 0;
}
.score-detail-loading-hint {
  margin: 0;
}
.library-home-section--non-interactive {
  pointer-events: none;
  user-select: none;
}
/* 曲库：顶栏固定在上；列表在卡片内滚动（高度由 main flex 填满，避免 vh 裁切） */
.library-home-section {
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.library-home-toolbar {
  flex-shrink: 0;
  padding-bottom: 0.65rem;
  margin-bottom: 0.35rem;
  border-bottom: 1px solid #e2e8f0;
  background: #fff;
}
.library-home-toolbar h2 {
  margin: 0 0 0.65rem 0;
  font-size: 1.35rem;
}
.library-home-toolbar .home-filter-panel {
  margin-top: 0.65rem;
}
.library-home-list-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
  padding: 0 0.15rem 1rem 0;
}
.score-slide-from-right-enter-active,
.score-slide-from-right-leave-active {
  transition: transform 0.36s cubic-bezier(0.22, 1, 0.32, 1);
}
.score-slide-from-right-enter-from,
.score-slide-from-right-leave-to {
  transform: translateX(100%);
}
.score-slide-from-right-enter-to,
.score-slide-from-right-leave-from {
  transform: translateX(0);
}
.score-detail-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) minmax(260px, 1fr);
  gap: 1.15rem;
  align-items: stretch;
  height: 100%;
  min-height: 0;
}
.score-detail-left {
  min-width: 0;
  width: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: visible;
}
/* 与智能助手侧乐谱区一致：明显外层边框与浅底 */
.assistant-score-pane,
.score-detail-score-pane {
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #f8fafc;
  padding: 0.55rem;
  display: flex;
  flex-direction: column;
  min-height: 0;
  box-sizing: border-box;
}
.score-detail-score-pane {
  width: 100%;
  max-width: 100%;
  min-height: 0;
}
/* 乐谱详情滚动区（仅此模板使用 .score-pages-scroll）；窄屏保留 A4 比例上限，宽屏与右侧「开始练习」底对齐时由 flex 撑满 */
.score-pages-scroll {
  width: 100%;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 0.25rem;
  overscroll-behavior: contain;
}
@media (min-width: 901px) {
  .score-detail-left {
    height: 100%;
    align-self: stretch;
  }
  .score-detail-score-pane {
    flex: 1 1 auto;
    min-height: 0;
  }
  .score-detail-score-pane .score-pages-scroll {
    flex: 1 1 auto;
    min-height: 0;
    max-height: none;
  }
}
@media (max-width: 900px) {
  .score-pages-scroll {
    flex: none;
    aspect-ratio: 210 / 297;
    max-height: min(68vh, calc(100dvh - 320px));
  }
}
.score-page-item {
  margin-bottom: 0.8rem;
}
.score-page-image {
  width: 100%;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #fff;
}
.score-page-fallback {
  aspect-ratio: 3 / 4;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 0.45rem;
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
}
.score-detail-right {
  align-self: stretch;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}
.score-detail-right .score-meta-box {
  margin-top: 0;
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  overscroll-behavior: contain;
}
.score-detail-practice-btn {
  margin-top: 0;
  width: 100%;
  flex-shrink: 0;
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
  font-size: 1.35rem;
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
.summary-section .summary-profile-controls {
  margin-top: 0.15rem;
  margin-bottom: 0;
}
.summary-section > .summary-box {
  margin-top: 0.65rem;
}
.summary-section .summary-box--records {
  margin-top: 0.95rem;
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
/* 1fr | auto | 1fr：左右等分余量，标题几何居中，不受左侧「显示乐谱」显隐挤压 */
.assistant-topbar {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.6rem;
}
.assistant-section .assistant-topbar h2.assistant-header-title {
  margin: 0;
  font-size: 1.35rem;
  text-align: center;
  justify-self: center;
  min-width: 0;
  grid-column: 2;
}
.assistant-upload-panel {
  margin-top: 0.6rem;
}
.assistant-layout {
  /* 乐谱区 / 右侧栏（含双列时整列）统一高度，略增高便于单页 PDF 一屏展示 */
  --assistant-pane-vh: 78vh;
  position: relative;
  margin-top: 0.5rem;
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.85rem;
  align-items: start;
  min-height: var(--assistant-pane-vh);
}
/* 有曲目且展开乐谱：双列（延伸动画由右栏 absolute 覆盖完成，不挤压左栏） */
.assistant-layout--with-score:not(.assistant-layout--score-collapsed) {
  grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
}
/* 有左侧乐谱栏且展开时：首个卡片（练习设置）顶边与左侧乐谱面板顶边对齐 */
.assistant-layout--with-score:not(.assistant-layout--score-collapsed)
  > .assistant-chat-slot
  > .assistant-chat-pane
  > .assistant-plan:first-of-type {
  margin-top: 0;
}
/* 乐谱关闭后：与关闭前右栏一致，避免默认 .assistant-plan 上外边距导致整块下移、动画结束跳一下 */
.assistant-layout--score-collapsed > .assistant-chat-slot > .assistant-chat-pane > .assistant-plan:first-of-type {
  margin-top: 0;
}
.assistant-chat-slot {
  min-width: 0;
  min-height: 0;
}
.assistant-layout--with-score:not(.assistant-layout--score-collapsed) > .assistant-chat-slot {
  height: var(--assistant-pane-vh);
  display: flex;
  flex-direction: column;
}
.assistant-layout--with-score:not(.assistant-layout--score-collapsed) > .assistant-chat-slot > .assistant-chat-pane {
  flex: 1;
  min-height: 0;
  height: 100%;
}
.assistant-chat-pane--overlay-active {
  overflow-y: auto;
  overscroll-behavior: contain;
  background: #fff;
  box-shadow: -10px 0 40px rgba(15, 23, 42, 0.12);
  border-radius: 10px;
}
.assistant-topbar-left {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  min-width: 0;
  grid-column: 1;
}
.assistant-topbar-right {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  min-width: 0;
  grid-column: 3;
}
.assistant-score-pane {
  position: static;
  height: var(--assistant-pane-vh);
  min-width: 0;
}
.assistant-score-pane-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.45rem;
}
.assistant-close-btn {
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  width: 24px;
  height: 24px;
  line-height: 20px;
  cursor: pointer;
  background: #fff;
}
.assistant-close-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.assistant-score-scroll {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
}
.assistant-score-image {
  width: 100%;
  border-radius: 6px;
  border: 1px solid #dbeafe;
  background: #fff;
  margin-bottom: 0.55rem;
}
.assistant-chat-pane {
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.assistant-chat-shell {
  display: flex;
  flex-direction: column;
  min-height: var(--assistant-pane-vh);
  height: var(--assistant-pane-vh);
  border: 1px solid #dbeafe;
  border-radius: 10px;
  background: #f8fafc;
  padding: 0.65rem;
}
/* 有左侧乐谱且展开时：右侧整列总高与左侧乐谱区一致，底边对齐 */
.assistant-layout--with-score:not(.assistant-layout--score-collapsed) > .assistant-chat-slot > .assistant-chat-pane > .assistant-chat-shell {
  flex: 1;
  min-height: 0;
  height: auto;
}
.assistant-layout--with-score:not(.assistant-layout--score-collapsed) .assistant-chat-shell .wechat-box {
  min-height: 0;
}
/* 无乐谱列或乐谱已收起：对话气泡与练习设置同宽 */
.assistant-layout:not(.assistant-layout--with-score) .assistant-chat-shell .chat-bubble,
.assistant-layout--score-collapsed .assistant-chat-shell .chat-bubble {
  max-width: 100%;
}
.assistant-layout:not(.assistant-layout--with-score) .assistant-chat-shell .system-card,
.assistant-layout:not(.assistant-layout--with-score) .assistant-chat-shell .action-card,
.assistant-layout--score-collapsed .assistant-chat-shell .system-card,
.assistant-layout--score-collapsed .assistant-chat-shell .action-card {
  max-width: 100%;
}
.wechat-box {
  flex: 1;
  min-height: 320px;
  background: #eef2ff;
}
.chat-line-user {
  display: flex;
  justify-content: flex-end;
}
.chat-line-assistant {
  display: flex;
  justify-content: flex-start;
}
.chat-bubble {
  max-width: min(82%, 560px);
  padding: 0.5rem 0.65rem;
  border-radius: 10px;
  background: #fff;
  border: 1px solid #e2e8f0;
  white-space: pre-wrap;
  word-break: break-word;
}
.chat-line-assistant .chat-bubble {
  background: #eff6ff;
  border-color: #bfdbfe;
  color: #0f172a;
}
.chat-line-user .chat-bubble {
  background: #95ec69;
  border-color: #86df5e;
}
.system-card,
.action-card {
  max-width: min(92%, 640px);
  background: #f8fafc;
  border-color: #dbeafe;
}
.system-card p,
.action-card p {
  margin: 0 0 0.35rem 0;
}
.assistant-actions-in-chat {
  margin-top: 0.15rem;
  display: flex;
  gap: 0.45rem;
  flex-wrap: wrap;
}
.assistant-input-row {
  margin-top: 0.6rem;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.5rem;
  align-items: center;
}
.assistant-chat-input {
  width: 100%;
  min-width: 0;
}
.profile-header-card {
  padding: 1rem 1.1rem;
}
.profile-topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.9rem;
}
.profile-header {
  display: flex;
  align-items: center;
  gap: 0.85rem;
}
.profile-avatar {
  width: 72px;
  height: 72px;
  border-radius: 999px;
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  display: grid;
  place-items: center;
  color: #fff;
  border: 2px solid #dbeafe;
}
.profile-avatar-text {
  font-weight: 700;
  font-size: 1.4rem;
}
.profile-header-right {
  min-width: 0;
}
.profile-name {
  font-size: 1.35rem;
  font-weight: 700;
  color: #0f172a;
}
.profile-subline {
  margin-top: 0.25rem;
}
.chat-box {
  max-height: 220px;
  overflow-y: auto;
  border: 1px solid #dbeafe;
  border-radius: 6px;
  padding: 0.45rem 0.55rem;
  background: #ffffff;
}

/* 助手页：聊天区应独立滚动，占满可用高度 */
.assistant-chat-shell .chat-box {
  flex: 1;
  min-height: 0;
  max-height: none;
  overflow-y: auto;
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
  flex-shrink: 0;
  width: 100%;
  height: 58px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
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
@media (max-width: 900px) {
  .score-detail-layout {
    grid-template-columns: 1fr;
  }
  .score-detail-right {
    height: auto;
    max-height: none;
    overflow: visible;
  }
  .score-detail-right .score-meta-box {
    overflow-y: visible;
  }
  .assistant-layout--with-score:not(.assistant-layout--score-collapsed) {
    grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
  }
  .assistant-layout {
    --assistant-pane-vh: 64vh;
  }
  .assistant-score-scroll {
    max-height: none;
  }
  .assistant-layout--with-score:not(.assistant-layout--score-collapsed) > .assistant-chat-slot > .assistant-chat-pane > .assistant-chat-shell {
    flex: 1;
    min-height: 0;
    height: auto;
  }
}
code {
  font-size: 0.85em;
  background: #e2e8f0;
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
}
</style>
