<!-- 引导幻灯片第 1 页配图：底部三栏（无交互，纯展示） -->
<template>
  <div class="obv1">
    <div class="obv1-frame">
      <div class="obv1-screen">
        <div class="obv1-screen-inner">
          <div class="obv1-bar obv1-bar--search" />
          <div class="obv1-bar obv1-bar--short" />
          <div class="obv1-cards">
            <div class="obv1-card" />
            <div class="obv1-card obv1-card--accent" />
          </div>
        </div>
      </div>
      <div class="obv1-tabs">
        <div class="obv1-tab">
          <svg class="obv1-ico" viewBox="0 0 24 24" aria-hidden="true">
            <path
              fill="currentColor"
              d="M4 6h7v7H4V6zm9 0h7v4h-7V6zM4 15h7v3H4v-3zm9 3v-5h7v5h-7z"
            />
          </svg>
          <span class="obv1-tab-text">首页·曲库</span>
        </div>
        <div class="obv1-tab obv1-tab--active">
          <svg class="obv1-ico" viewBox="0 0 24 24" aria-hidden="true">
            <path
              fill="currentColor"
              d="M20 2H4a2 2 0 00-2 2v12a2 2 0 002 2h4v3l4-3h8a2 2 0 002-2V4a2 2 0 00-2-2z"
            />
          </svg>
          <span class="obv1-tab-text">keygent</span>
        </div>
        <div class="obv1-tab">
          <svg class="obv1-ico" viewBox="0 0 24 24" aria-hidden="true">
            <path
              fill="currentColor"
              d="M12 12a4 4 0 100-8 4 4 0 000 8zm-7 9a7 7 0 0114 0v1H5v-1z"
            />
          </svg>
          <span class="obv1-tab-text">个人主页</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/* 无 props、无交互 */
</script>

<style scoped>
.obv1 {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  user-select: none;
}
.obv1-frame {
  width: 100%;
  max-width: 300px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
  box-shadow:
    0 4px 16px rgba(15, 23, 42, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
  box-sizing: border-box;
}
.obv1-screen {
  padding: 0.65rem 0.75rem 0.55rem;
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
  border-bottom: 1px solid #e2e8f0;
}
.obv1-screen-inner {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  min-height: 72px;
}
.obv1-bar {
  height: 8px;
  border-radius: 4px;
  background: #e2e8f0;
}
.obv1-bar--search {
  width: 100%;
  max-width: 100%;
  background: linear-gradient(90deg, #e2e8f0 0%, #cbd5e1 100%);
}
.obv1-bar--short {
  width: 55%;
}
.obv1-cards {
  display: flex;
  gap: 0.4rem;
  margin-top: 0.1rem;
}
.obv1-card {
  flex: 1;
  height: 36px;
  border-radius: 8px;
  background: linear-gradient(145deg, #e2e8f0 0%, #cbd5e1 100%);
  border: 1px solid #cbd5e1;
}
.obv1-card--accent {
  background: linear-gradient(145deg, #dbeafe 0%, #bfdbfe 100%);
  border-color: #93c5fd;
}
.obv1-tabs {
  display: flex;
  flex-direction: row;
  align-items: stretch;
  background: linear-gradient(180deg, #fcfcfd 0%, #fafafa 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 1);
}
.obv1-tab {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.15rem;
  padding: 0.45rem 0.2rem 0.5rem;
  border-right: 1px solid rgba(186, 198, 214, 0.45);
  color: #64748b;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
}
.obv1-tab:last-child {
  border-right: none;
}
.obv1-tab--active {
  color: #1d4ed8;
  font-weight: 600;
  background: linear-gradient(180deg, #ffffff 0%, #eff6ff 100%);
  box-shadow: inset 0 3px 0 #2563eb;
}
.obv1-ico {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  opacity: 0.92;
}
.obv1-tab--active .obv1-ico {
  color: #2563eb;
  opacity: 1;
}
.obv1-tab-text {
  font-size: 0.62rem;
  line-height: 1.15;
  text-align: center;
  letter-spacing: 0.01em;
}
@media (min-width: 400px) {
  .obv1-tab-text {
    font-size: 0.68rem;
  }
}
</style>
