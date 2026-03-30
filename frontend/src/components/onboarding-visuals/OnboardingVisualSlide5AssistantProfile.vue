<!-- 引导幻灯片第 5 页配图：keygent + 个人主页（无交互） -->
<template>
  <div class="obv5">
    <div class="obv5-shell">
      <div class="obv5-col obv5-col--assistant">
        <div class="obv5-hd">keygent</div>
        <div class="obv5-chat">
          <div class="obv5-bubble obv5-bubble--a" />
          <div class="obv5-bubble obv5-bubble--u" />
          <div class="obv5-bubble obv5-bubble--a obv5-bubble--short" />
        </div>
        <div class="obv5-pills">
          <span class="obv5-pill">生成建议</span>
          <span class="obv5-pill obv5-pill--pri">练习任务</span>
        </div>
        <div class="obv5-stats">
          <div class="obv5-stat-row">
            <span class="obv5-stat-lab">准确率</span>
            <div class="obv5-stat-bar"><div class="obv5-stat-fill" /></div>
          </div>
          <div class="obv5-mini">
            <span class="obv5-mini-ico">PDF</span>
            <span class="obv5-mini-dot" />
            <span class="obv5-mini-wave" aria-hidden="true" />
          </div>
        </div>
      </div>
      <div class="obv5-gutter" aria-hidden="true" />
      <div class="obv5-col obv5-col--profile">
        <div class="obv5-hd">个人主页</div>
        <div class="obv5-donut-wrap">
          <div class="obv5-donut" />
          <div class="obv5-donut-cap">练习摘要</div>
        </div>
        <div class="obv5-weak">薄弱小节</div>
        <div class="obv5-list">
          <div class="obv5-li" />
          <div class="obv5-li obv5-li--mid" />
        </div>
        <div class="obv5-audio">
          <span class="obv5-wave-bar" />
          <span class="obv5-wave-bar obv5-wave-bar--t" />
          <span class="obv5-wave-bar" />
          <span class="obv5-wave-bar obv5-wave-bar--s" />
          <span class="obv5-wave-bar" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/* 无 props、无交互 */
</script>

<style scoped>
.obv5 {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  user-select: none;
}
.obv5-shell {
  display: flex;
  flex-direction: row;
  align-items: stretch;
  width: 100%;
  max-width: 360px;
  padding: 0.45rem 0.4rem;
  border-radius: 12px;
  background: linear-gradient(180deg, #fafbfc 0%, #f1f5f9 100%);
  border: 1px solid #e2e8f0;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    0 2px 10px rgba(15, 23, 42, 0.05);
  box-sizing: border-box;
  gap: 0;
}
.obv5-col {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.32rem;
}
.obv5-gutter {
  width: 1px;
  align-self: stretch;
  margin: 0.15rem 0.35rem;
  background: linear-gradient(180deg, transparent, #cbd5e1 12%, #cbd5e1 88%, transparent);
  flex-shrink: 0;
}
.obv5-hd {
  font-size: 0.58rem;
  font-weight: 700;
  color: #1d4ed8;
  letter-spacing: 0.04em;
  text-align: center;
}
.obv5-col--profile .obv5-hd {
  color: #475569;
}
.obv5-chat {
  display: flex;
  flex-direction: column;
  gap: 0.22rem;
  align-items: flex-start;
}
.obv5-bubble {
  max-width: 92%;
  height: 10px;
  border-radius: 6px;
  background: #e2e8f0;
}
.obv5-bubble--a {
  width: 88%;
  background: linear-gradient(90deg, #dbeafe 0%, #e0e7ff 100%);
  border: 1px solid #bfdbfe;
}
.obv5-bubble--u {
  width: 62%;
  align-self: flex-end;
  background: #fff;
  border: 1px solid #cbd5e1;
}
.obv5-bubble--short {
  width: 72%;
  height: 8px;
}
.obv5-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 0.2rem;
  justify-content: center;
}
.obv5-pill {
  font-size: 0.48rem;
  padding: 0.12rem 0.28rem;
  border-radius: 999px;
  background: #fff;
  border: 1px solid #cbd5e1;
  color: #64748b;
}
.obv5-pill--pri {
  border-color: #93c5fd;
  color: #1d4ed8;
  font-weight: 600;
  background: linear-gradient(180deg, #eff6ff 0%, #dbeafe 100%);
}
.obv5-stats {
  margin-top: 0.05rem;
  padding-top: 0.28rem;
  border-top: 1px dashed #e2e8f0;
}
.obv5-stat-row {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  margin-bottom: 0.25rem;
}
.obv5-stat-lab {
  font-size: 0.48rem;
  color: #64748b;
  flex-shrink: 0;
}
.obv5-stat-bar {
  flex: 1;
  height: 5px;
  border-radius: 3px;
  background: #e2e8f0;
  overflow: hidden;
}
.obv5-stat-fill {
  width: 72%;
  height: 100%;
  border-radius: 3px;
  background: linear-gradient(90deg, #34d399 0%, #2563eb 100%);
}
.obv5-mini {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
}
.obv5-mini-ico {
  font-size: 0.45rem;
  color: #94a3b8;
  padding: 0.08rem 0.2rem;
  border-radius: 4px;
  background: #fff;
  border: 1px solid #e2e8f0;
}
.obv5-mini-dot {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: #cbd5e1;
}
.obv5-mini-wave {
  width: 18px;
  height: 8px;
  background: repeating-linear-gradient(
    90deg,
    #94a3b8 0px,
    #94a3b8 2px,
    transparent 2px,
    transparent 4px
  );
  border-radius: 2px;
  opacity: 0.7;
}
.obv5-donut-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.15rem;
}
.obv5-donut {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  box-sizing: border-box;
  border: 5px solid #e2e8f0;
  border-top-color: #2563eb;
  border-right-color: #3b82f6;
  border-bottom-color: #60a5fa;
  transform: rotate(-35deg);
}
.obv5-donut-cap {
  font-size: 0.48rem;
  color: #64748b;
}
.obv5-weak {
  font-size: 0.48rem;
  color: #94a3b8;
  text-align: center;
}
.obv5-list {
  display: flex;
  flex-direction: column;
  gap: 0.18rem;
  align-items: center;
}
.obv5-li {
  height: 4px;
  width: 90%;
  border-radius: 2px;
  background: #e2e8f0;
}
.obv5-li--mid {
  width: 70%;
}
.obv5-audio {
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 2px;
  height: 14px;
  margin-top: 0.05rem;
}
.obv5-wave-bar {
  width: 3px;
  height: 6px;
  border-radius: 1px;
  background: #93c5fd;
}
.obv5-wave-bar--t {
  height: 12px;
  background: #2563eb;
}
.obv5-wave-bar--s {
  height: 4px;
}
@media (min-width: 400px) {
  .obv5-hd {
    font-size: 0.62rem;
  }
  .obv5-pill {
    font-size: 0.52rem;
  }
}
</style>
