<!-- 登录后问卷：由 App.vue 在引导幻灯片之前挂载 -->
<template>
  <main class="login-main onboarding-wrap">
    <section class="login-card onboarding-card">
      <div
        v-if="step >= 0 && soundEnabled && audioUsable"
        class="onboarding-card-actions"
      >
        <button
          type="button"
          class="onboarding-sound-icon-btn"
          :class="{ 'onboarding-sound-icon-btn--muted': soundMuted }"
          :aria-pressed="!soundMuted"
          :title="soundMuted ? '打开按键音效' : '静音'"
          :aria-label="soundMuted ? '打开按键音效' : '静音按键音效'"
          @click="toggleSoundMute"
        >
          <svg
            v-if="soundMuted"
            class="onboarding-sound-icon-svg"
            viewBox="0 0 24 24"
            width="22"
            height="22"
            aria-hidden="true"
          >
            <path
              fill="currentColor"
              d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"
            />
          </svg>
          <svg
            v-else
            class="onboarding-sound-icon-svg"
            viewBox="0 0 24 24"
            width="22"
            height="22"
            aria-hidden="true"
          >
            <path
              fill="currentColor"
              d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"
            />
          </svg>
        </button>
      </div>

      <slot name="preview-banner">
        <p v-if="previewMode" class="muted onboarding-dev-banner">
          开发预览 · 无需登录。地址含 <code>#/onboarding-preview</code>；点「进入应用」将关闭预览。
        </p>
      </slot>

      <p class="muted onboarding-progress">步骤 {{ progressIndex }} / {{ totalProgressSteps }}</p>

      <div class="onboarding-slide-stage">
        <Transition :name="slideTransitionName">
          <div
            :key="step"
            :class="[
              'onboarding-slide-pane',
              step === -1 ? 'onboarding-slide-pane--intro' : 'onboarding-slide-pane--question',
            ]"
          >
            <template v-if="step === -1">
              <div class="onboarding-intro-centered">
                <h1 class="login-title onboarding-intro-heading">{{ introTitle }}</h1>
                <div class="onboarding-intro-body">
                  <p v-for="(para, i) in introParagraphs" :key="i" class="onboarding-intro-para">
                    {{ para }}
                  </p>
                </div>
              </div>
            </template>
            <template v-else>
              <h1 class="login-title">{{ currentQuestion.title }}</h1>

              <div class="onboarding-options">
                <button
                  v-for="opt in currentQuestion.options"
                  :key="opt.id"
                  type="button"
                  class="onboarding-chip"
                  :class="{
                    active: selections[step] === opt.id,
                    'onboarding-chip--tap': tapFlashId === opt.id,
                  }"
                  @click="setSelection(step, opt.id)"
                >
                  <span class="onboarding-chip-title">{{ opt.label }}</span>
                </button>
              </div>
            </template>

            <p v-if="formError" class="error onboarding-slide-error">{{ formError }}</p>
          </div>
        </Transition>
      </div>

      <p v-if="persistMessage" class="error">{{ persistMessage }}</p>
      <div class="onboarding-nav">
        <button v-if="step > -1" type="button" class="btn" @click="prevStep">上一步</button>
        <div class="onboarding-nav-spacer" />
        <button
          v-if="step === -1"
          type="button"
          class="btn primary"
          @click="nextStep"
        >
          开始填写
        </button>
        <button
          v-else-if="step < questionCount - 1"
          type="button"
          class="btn primary"
          @click="nextStep"
        >
          下一步
        </button>
        <button v-else type="button" class="btn primary" @click="submit">进入应用</button>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { DEFAULT_POST_LOGIN_ONBOARDING_QUESTIONS } from './defaultQuestions.js'

const props = defineProps({
  previewMode: { type: Boolean, default: false },
  questions: {
    type: Array,
    default: () => DEFAULT_POST_LOGIN_ONBOARDING_QUESTIONS,
  },
  introTitle: {
    type: String,
    default: '开始之前',
  },
  introParagraphs: {
    type: Array,
    default: () => [
      '接下来有几个简短问题，帮助我们了解您的学琴背景与练琴习惯，便于为您推荐更合适的练习内容。只需点选选项即可。',
    ],
  },
  persistMessage: { type: String, default: '' },
})

const emit = defineEmits(['complete', 'dismiss-persist'])

function dismissPersist() {
  emit('dismiss-persist')
}

const step = ref(-1)
/** 1：前进（下一页从右入）；-1：后退（上一页从左入） */
const slideDir = ref(1)
const slideTransitionName = computed(() =>
  slideDir.value === 1 ? 'onboarding-q-fwd' : 'onboarding-q-back',
)
const selections = ref([])
const formError = ref('')
const tapFlashId = ref('')
let tapClearTimer = null

const audioUsable =
  typeof window !== 'undefined' && !!(window.AudioContext || window.webkitAudioContext)

const soundEnabled = ref(audioUsable)
const soundMuted = ref(false)
let audioContext = null

function initSelections() {
  selections.value = props.questions.map(() => '')
}
initSelections()

watch(
  () => props.questions,
  () => {
    slideDir.value = 1
    step.value = -1
    initSelections()
    formError.value = ''
    soundEnabled.value = audioUsable
    soundMuted.value = false
  },
  { deep: true },
)

const questionCount = computed(() => props.questions.length)
const totalProgressSteps = computed(() => 1 + questionCount.value)
const progressIndex = computed(() => step.value + 2)
const currentQuestion = computed(
  () => props.questions[step.value] || props.questions[0] || { title: '', options: [] },
)

function soundAllowedBySystem() {
  try {
    return !window.matchMedia('(prefers-reduced-motion: reduce)').matches
  } catch {
    return true
  }
}

async function armAudioFromUserGesture() {
  if (!audioUsable) return
  const AC = window.AudioContext || window.webkitAudioContext
  if (!AC) return
  if (!audioContext) {
    audioContext = new AC()
  }
  if (audioContext.state === 'suspended') {
    await audioContext.resume()
  }
}

function playKeySoundInternal(optionIndex, stepIdx) {
  if (
    !soundEnabled.value
    || soundMuted.value
    || !soundAllowedBySystem()
  ) {
    return
  }
  const ctx = audioContext
  if (!ctx || ctx.state !== 'running') return

  const t = ctx.currentTime
  const midi = 59 + optionIndex * 2 + stepIdx * 3
  const clampedMidi = Math.min(84, Math.max(48, midi))
  const f0 = 440 * 2 ** ((clampedMidi - 69) / 12)

  const osc = ctx.createOscillator()
  const g = ctx.createGain()
  osc.type = 'triangle'
  osc.frequency.setValueAtTime(f0, t)

  g.gain.setValueAtTime(0.0001, t)
  g.gain.exponentialRampToValueAtTime(0.1, t + 0.008)
  g.gain.exponentialRampToValueAtTime(0.0001, t + 0.14)

  osc.connect(g)
  g.connect(ctx.destination)
  osc.start(t)
  osc.stop(t + 0.155)
}

function playKeySoundForSelection(stepIdx, optionId) {
  if (!soundEnabled.value || soundMuted.value || !audioUsable) return
  const opts = props.questions[stepIdx]?.options || []
  const idx = Math.max(0, opts.findIndex((o) => o.id === optionId))

  const go = () => playKeySoundInternal(idx, stepIdx)
  if (!audioContext || audioContext.state === 'suspended') {
    void armAudioFromUserGesture().then(() => {
      if (soundEnabled.value) go()
    })
    return
  }
  go()
}

function toggleSoundMute() {
  soundMuted.value = !soundMuted.value
}

function setSelection(stepIdx, optionId) {
  const next = [...selections.value]
  next[stepIdx] = optionId
  selections.value = next
  formError.value = ''
  dismissPersist()
  tapFlashId.value = optionId
  if (tapClearTimer != null) {
    window.clearTimeout(tapClearTimer)
    tapClearTimer = null
  }
  tapClearTimer = window.setTimeout(() => {
    tapFlashId.value = ''
    tapClearTimer = null
  }, 420)
  playKeySoundForSelection(stepIdx, optionId)
}

function prevStep() {
  if (step.value <= -1) return
  slideDir.value = -1
  if (step.value === 0) {
    step.value = -1
  } else {
    step.value -= 1
  }
  formError.value = ''
  dismissPersist()
}

function nextStep() {
  if (step.value === -1) {
    slideDir.value = 1
    step.value = 0
    formError.value = ''
    dismissPersist()
    return
  }
  if (!selections.value[step.value]) {
    formError.value = '请选择一项。'
    return
  }
  slideDir.value = 1
  formError.value = ''
  dismissPersist()
  if (step.value < questionCount.value - 1) {
    step.value += 1
  }
}

function submit() {
  formError.value = ''
  dismissPersist()
  const last = questionCount.value - 1
  if (!selections.value[last]) {
    formError.value = '请选择一项。'
    return
  }
  emit('complete', { selections: [...selections.value] })
}

onBeforeUnmount(() => {
  if (tapClearTimer != null) {
    window.clearTimeout(tapClearTimer)
    tapClearTimer = null
  }
  if (audioContext) {
    audioContext.close().catch(() => {})
    audioContext = null
  }
})
</script>

<style scoped>
.login-main {
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  box-sizing: border-box;
}
.login-card {
  width: min(430px, 100%);
  background: #fff;
  border-radius: 12px;
  padding: 1.5rem;
  border: 1px solid #dbeafe;
  box-shadow: 0 10px 30px rgba(37, 99, 235, 0.08);
  box-sizing: border-box;
}
.login-title {
  margin: 0 0 0.35rem 0;
  text-align: center;
  font-size: 1.7rem;
  color: #0f172a;
}
.btn {
  padding: 0.5rem 1rem;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  background: #fff;
  color: #334155;
  cursor: pointer;
  font-size: 0.95rem;
}
.btn.primary {
  background: #2563eb;
  color: #fff;
  border-color: #2563eb;
}
.error {
  color: #b91c1c;
  margin-top: 0.5rem;
}
.onboarding-wrap .muted {
  color: #64748b;
  margin-top: 0;
}
.onboarding-wrap .onboarding-progress {
  margin-bottom: 0.5rem;
}
.onboarding-slide-pane--intro {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  min-height: clamp(232px, 38vh, 360px);
  padding: 0.5rem 0.35rem 0.85rem;
  box-sizing: border-box;
}
.onboarding-slide-pane--question {
  padding-top: 0.1rem;
}
.onboarding-intro-centered {
  width: 100%;
  max-width: 22rem;
  margin: 0 auto;
  text-align: center;
}
.onboarding-intro-heading {
  margin: 0 0 1.05rem 0;
  font-size: 1.62rem;
  font-weight: 700;
  letter-spacing: 0.03em;
  line-height: 1.3;
}
.onboarding-intro-body {
  margin: 0;
  text-align: center;
}
.onboarding-slide-pane--intro .onboarding-intro-para {
  margin: 0 0 0.8rem 0;
  font-size: 0.94rem;
  line-height: 1.62;
  color: #475569;
  text-align: center;
  text-wrap: balance;
}
.onboarding-slide-pane--intro .onboarding-intro-para:last-child {
  margin-bottom: 0;
}
.onboarding-slide-error {
  margin-top: 0.65rem;
  margin-bottom: 0;
}
.onboarding-slide-stage {
  position: relative;
  overflow: hidden;
  width: 100%;
  min-height: clamp(232px, 38vh, 360px);
}
.onboarding-slide-pane {
  width: 100%;
  box-sizing: border-box;
}
/* 前进：当前页左移离开，下一页从右侧进入 */
.onboarding-q-fwd-enter-active,
.onboarding-q-fwd-leave-active,
.onboarding-q-back-enter-active,
.onboarding-q-back-leave-active {
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  box-sizing: border-box;
  transition: transform 0.38s cubic-bezier(0.22, 1, 0.32, 1);
  will-change: transform;
}
.onboarding-q-fwd-enter-from {
  transform: translateX(100%);
}
.onboarding-q-fwd-enter-to {
  transform: translateX(0);
}
.onboarding-q-fwd-leave-from {
  transform: translateX(0);
}
.onboarding-q-fwd-leave-to {
  transform: translateX(-100%);
}
/* 后退：当前页右移离开，上一页从左侧进入 */
.onboarding-q-back-enter-from {
  transform: translateX(-100%);
}
.onboarding-q-back-enter-to {
  transform: translateX(0);
}
.onboarding-q-back-leave-from {
  transform: translateX(0);
}
.onboarding-q-back-leave-to {
  transform: translateX(100%);
}
.onboarding-wrap {
  background: linear-gradient(165deg, #eff6ff 0%, #f8fafc 42%, #dbeafe 100%);
}
.onboarding-card {
  position: relative;
  width: min(430px, 100%);
  max-width: 100%;
}
.onboarding-card-actions {
  position: absolute;
  top: 0.65rem;
  right: 0.65rem;
  z-index: 8;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.4rem;
}
.onboarding-sound-icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  margin: 0;
  padding: 0;
  color: #64748b;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid #e2e8f0;
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
  transition:
    color 0.18s ease,
    background 0.18s ease,
    border-color 0.18s ease,
    transform 0.12s ease;
}
.onboarding-sound-icon-btn:hover {
  color: #1d4ed8;
  border-color: #bfdbfe;
  background: #eff6ff;
}
.onboarding-sound-icon-btn--muted {
  color: #94a3b8;
}
.onboarding-sound-icon-btn--muted:hover {
  color: #2563eb;
}
.onboarding-sound-icon-btn:active {
  transform: scale(0.94);
}
.onboarding-sound-icon-svg {
  display: block;
  flex-shrink: 0;
}
.onboarding-progress {
  text-align: center;
  font-size: 0.88rem;
  letter-spacing: 0.02em;
}
.onboarding-dev-banner {
  font-size: 0.82rem;
  margin: 0 0 0.85rem 0;
  padding: 0.5rem 0.65rem;
  background: #fef3c7;
  border: 1px solid #fcd34d;
  border-radius: 8px;
  color: #78350f;
  line-height: 1.45;
  text-align: left;
}
.onboarding-dev-banner code {
  font-size: 0.78em;
  padding: 0.1em 0.35em;
  background: rgba(255, 255, 255, 0.7);
  border-radius: 4px;
}
.onboarding-options {
  display: flex;
  flex-direction: column;
  gap: 0.72rem;
  width: 100%;
  margin: 0 0 0.25rem 0;
}
.onboarding-chip {
  position: relative;
  width: 100%;
  display: block;
  text-align: left;
  padding: 1.05rem 1.2rem 1.05rem 1.35rem;
  margin: 0;
  border-radius: 12px;
  cursor: pointer;
  font: inherit;
  color: #1e3a8a;
  border: 1px solid #bfdbfe;
  background: linear-gradient(180deg, #f8fafc 0%, #eff6ff 40%, #dbeafe 100%);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.85) inset,
    0 5px 0 #93c5fd,
    0 8px 20px rgba(37, 99, 235, 0.12);
  transform: translateY(0);
  transition:
    transform 0.1s cubic-bezier(0.22, 1, 0.32, 1),
    box-shadow 0.1s cubic-bezier(0.22, 1, 0.32, 1),
    border-color 0.18s ease,
    background 0.2s ease,
    color 0.15s ease;
  -webkit-tap-highlight-color: transparent;
}
.onboarding-chip::before {
  content: '';
  position: absolute;
  left: 10%;
  right: 10%;
  top: 4px;
  height: 32%;
  max-height: 1.35rem;
  border-radius: 6px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.72) 0%, rgba(255, 255, 255, 0) 100%);
  pointer-events: none;
}
.onboarding-chip:hover {
  border-color: #60a5fa;
  background: linear-gradient(180deg, #ffffff 0%, #eff6ff 50%, #dbeafe 100%);
  color: #1d4ed8;
}
.onboarding-chip:active {
  transform: translateY(4px);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.45) inset,
    0 1px 0 #60a5fa,
    0 3px 10px rgba(37, 99, 235, 0.18);
}
.onboarding-chip.active {
  font-weight: 600;
  color: #1e3a8a;
  border-color: #2563eb;
  background: linear-gradient(180deg, #dbeafe 0%, #bfdbfe 55%, #93c5fd 100%);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.6) inset,
    0 3px 0 #2563eb,
    0 6px 18px rgba(37, 99, 235, 0.25);
}
.onboarding-chip.active::before {
  opacity: 0.55;
}
.onboarding-chip-title {
  position: relative;
  z-index: 1;
  display: block;
  font-size: 1.05rem;
  line-height: 1.45;
  letter-spacing: 0.02em;
}
@keyframes onboarding-key-tap {
  0% {
    transform: translateY(0) scale(1, 1);
    box-shadow:
      0 1px 0 rgba(255, 255, 255, 0.85) inset,
      0 5px 0 #93c5fd,
      0 8px 20px rgba(37, 99, 235, 0.12);
  }
  28% {
    transform: translateY(6px) scale(0.99, 0.96);
    box-shadow:
      0 1px 0 rgba(255, 255, 255, 0.35) inset,
      0 0 0 #60a5fa,
      0 2px 8px rgba(37, 99, 235, 0.2);
  }
  55% {
    transform: translateY(-2px) scale(1.01, 1.02);
    box-shadow:
      0 1px 0 rgba(255, 255, 255, 0.8) inset,
      0 6px 0 #93c5fd,
      0 10px 22px rgba(37, 99, 235, 0.16);
  }
  100% {
    transform: translateY(0) scale(1, 1);
  }
}
.onboarding-chip.onboarding-chip--tap:not(.active) {
  animation: onboarding-key-tap 0.4s cubic-bezier(0.34, 1.35, 0.64, 1) forwards;
}
.onboarding-chip.onboarding-chip--tap.active {
  animation: onboarding-key-tap-active 0.4s cubic-bezier(0.34, 1.35, 0.64, 1) forwards;
}
@keyframes onboarding-key-tap-active {
  0% {
    transform: translateY(0) scale(1, 1);
  }
  28% {
    transform: translateY(5px) scale(0.99, 0.97);
  }
  55% {
    transform: translateY(-2px) scale(1.008, 1.015);
  }
  100% {
    transform: translateY(0) scale(1, 1);
  }
}
.onboarding-nav {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin-top: 1.35rem;
  padding-top: 0.25rem;
}
.onboarding-nav-spacer {
  flex: 1;
  min-width: 0.5rem;
}
@media (prefers-reduced-motion: reduce) {
  .onboarding-chip,
  .onboarding-chip:active {
    transition: none;
  }
  .onboarding-chip.onboarding-chip--tap,
  .onboarding-chip.onboarding-chip--tap.active {
    animation: none;
  }
  .onboarding-q-fwd-enter-active,
  .onboarding-q-fwd-leave-active,
  .onboarding-q-back-enter-active,
  .onboarding-q-back-leave-active {
    transition-duration: 0.01ms;
  }
  .onboarding-q-fwd-enter-from,
  .onboarding-q-fwd-leave-to,
  .onboarding-q-back-enter-from,
  .onboarding-q-back-leave-to {
    transform: none;
  }
}
</style>
