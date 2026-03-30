<!-- 引导幻灯片第 4 页配图：乐谱页（大图、侧栏、开始练习，无交互） -->
<template>
  <div class="obv4">
    <div class="obv4-shell">
      <div class="obv4-layout">
        <div class="obv4-score">
          <div class="obv4-score-hint" aria-hidden="true">
            <svg class="obv4-hint-ico" viewBox="0 0 24 24">
              <path
                fill="currentColor"
                d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0016 9.5 6.5 6.5 0 109.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"
              />
            </svg>
            <span class="obv4-hint-txt">缩放 · 拖拽</span>
          </div>
          <div class="obv4-staff-wrap">
            <div class="obv4-staff">
              <div class="obv4-staff-line" />
              <div class="obv4-staff-line" />
              <div class="obv4-staff-line" />
              <div class="obv4-staff-line" />
              <div class="obv4-staff-line" />
            </div>
            <div class="obv4-notes" aria-hidden="true">
              <span class="obv4-note" style="top: 18%; left: 12%" />
              <span class="obv4-note" style="top: 42%; left: 28%" />
              <span class="obv4-note" style="top: 30%; left: 52%" />
              <span class="obv4-note" style="top: 55%; left: 72%" />
            </div>
          </div>
        </div>
        <aside class="obv4-aside">
          <div class="obv4-aside-cap">曲目</div>
          <div class="obv4-aside-block" />
          <div class="obv4-aside-line" />
          <div class="obv4-aside-line obv4-aside-line--mid" />
          <div class="obv4-aside-line obv4-aside-line--short" />
        </aside>
      </div>
      <div class="obv4-cta">开始练习</div>
    </div>
  </div>
</template>

<script setup>
/* 无 props、无交互 */
</script>

<style scoped>
.obv4 {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  user-select: none;
}
.obv4-shell {
  width: 100%;
  max-width: 340px;
  padding: 0.5rem 0.55rem 0.5rem;
  border-radius: 12px;
  background: #fff;
  border: 1px solid #e2e8f0;
  box-shadow: 0 2px 12px rgba(15, 23, 42, 0.06);
  box-sizing: border-box;
}
.obv4-layout {
  display: flex;
  flex-direction: row;
  align-items: stretch;
  gap: 0.45rem;
  margin-bottom: 0.45rem;
}
.obv4-score {
  flex: 1;
  min-width: 0;
  border-radius: 8px;
  background: linear-gradient(180deg, #fafbfc 0%, #f1f5f9 100%);
  border: 1px solid #e2e8f0;
  padding: 0.35rem 0.4rem 0.4rem;
  position: relative;
  overflow: hidden;
}
.obv4-score-hint {
  display: flex;
  align-items: center;
  gap: 0.2rem;
  margin-bottom: 0.3rem;
  color: #94a3b8;
}
.obv4-hint-ico {
  width: 12px;
  height: 12px;
  flex-shrink: 0;
  opacity: 0.9;
}
.obv4-hint-txt {
  font-size: 0.52rem;
  letter-spacing: 0.04em;
  line-height: 1;
}
.obv4-staff-wrap {
  position: relative;
  min-height: 72px;
}
.obv4-staff {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  height: 68px;
  padding: 0.15rem 0.25rem 0;
}
.obv4-staff-line {
  height: 2px;
  border-radius: 1px;
  background: linear-gradient(90deg, #cbd5e1 0%, #94a3b8 50%, #cbd5e1 100%);
  opacity: 0.85;
}
.obv4-notes {
  position: absolute;
  inset: 0.5rem 0.2rem 0.15rem 0.2rem;
  pointer-events: none;
}
.obv4-note {
  position: absolute;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #475569;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.6);
}
.obv4-aside {
  width: 3.4rem;
  flex-shrink: 0;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  padding: 0.35rem 0.3rem;
  display: flex;
  flex-direction: column;
  gap: 0.28rem;
}
.obv4-aside-cap {
  font-size: 0.52rem;
  font-weight: 600;
  color: #64748b;
  text-align: center;
  margin-bottom: 0.05rem;
}
.obv4-aside-block {
  height: 28px;
  border-radius: 6px;
  background: linear-gradient(145deg, #e2e8f0 0%, #cbd5e1 100%);
  border: 1px solid #cbd5e1;
}
.obv4-aside-line {
  height: 4px;
  border-radius: 2px;
  background: #e2e8f0;
  width: 100%;
}
.obv4-aside-line--mid {
  width: 80%;
  align-self: center;
}
.obv4-aside-line--short {
  width: 60%;
  align-self: center;
}
.obv4-cta {
  width: 100%;
  text-align: center;
  padding: 0.38rem 0.5rem;
  border-radius: 8px;
  font-size: 0.72rem;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(180deg, #3b82f6 0%, #2563eb 100%);
  border: 1px solid #1d4ed8;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.2),
    0 2px 6px rgba(37, 99, 235, 0.25);
  letter-spacing: 0.06em;
}
@media (min-width: 400px) {
  .obv4-hint-txt {
    font-size: 0.56rem;
  }
  .obv4-cta {
    font-size: 0.78rem;
  }
  .obv4-aside {
    width: 3.75rem;
  }
}
</style>
