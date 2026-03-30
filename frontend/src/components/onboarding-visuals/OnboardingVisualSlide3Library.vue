<!-- 引导幻灯片第 3 页配图：首页·曲库（搜索、筛选、卡片网格，无交互） -->
<template>
  <div class="obv3">
    <div class="obv3-panel">
      <div class="obv3-search">
        <svg class="obv3-search-ico" viewBox="0 0 24 24" aria-hidden="true">
          <path
            fill="currentColor"
            d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0016 9.5 6.5 6.5 0 109.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"
          />
        </svg>
        <span class="obv3-search-ph">搜索曲名…</span>
      </div>
      <div class="obv3-chips">
        <span class="obv3-chip obv3-chip--active">难度</span>
        <span class="obv3-chip">能力</span>
        <span class="obv3-chip">全部</span>
      </div>
      <div class="obv3-grid">
        <div class="obv3-card">
          <div class="obv3-card-art" />
          <div class="obv3-card-line" />
        </div>
        <div class="obv3-card obv3-card--pick">
          <div class="obv3-card-art obv3-card-art--accent" />
          <div class="obv3-card-line obv3-card-line--short" />
        </div>
        <div class="obv3-card">
          <div class="obv3-card-art" />
          <div class="obv3-card-line" />
        </div>
        <div class="obv3-card">
          <div class="obv3-card-art" />
          <div class="obv3-card-line obv3-card-line--mid" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/* 无 props、无交互 */
</script>

<style scoped>
.obv3 {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  user-select: none;
}
.obv3-panel {
  width: 100%;
  max-width: 320px;
  padding: 0.5rem 0.55rem 0.45rem;
  border-radius: 12px;
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
  border: 1px solid #e2e8f0;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.85),
    0 2px 10px rgba(15, 23, 42, 0.05);
  box-sizing: border-box;
}
.obv3-search {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.38rem 0.55rem;
  border-radius: 8px;
  background: #fff;
  border: 1px solid #cbd5e1;
  margin-bottom: 0.45rem;
}
.obv3-search-ico {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  color: #94a3b8;
}
.obv3-search-ph {
  font-size: 0.68rem;
  color: #94a3b8;
  letter-spacing: 0.02em;
}
.obv3-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  margin-bottom: 0.5rem;
}
.obv3-chip {
  padding: 0.2rem 0.45rem;
  border-radius: 999px;
  font-size: 0.58rem;
  color: #64748b;
  background: #fff;
  border: 1px solid #e2e8f0;
}
.obv3-chip--active {
  color: #1d4ed8;
  border-color: #93c5fd;
  background: linear-gradient(180deg, #eff6ff 0%, #dbeafe 100%);
  font-weight: 600;
}
.obv3-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.4rem;
}
.obv3-card {
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
}
.obv3-card--pick {
  border-color: #2563eb;
  box-shadow:
    0 0 0 1px rgba(37, 99, 235, 0.35),
    0 2px 8px rgba(37, 99, 235, 0.12);
}
.obv3-card-art {
  height: 48px;
  background: linear-gradient(145deg, #e2e8f0 0%, #cbd5e1 100%);
}
.obv3-card-art--accent {
  background: linear-gradient(145deg, #bfdbfe 0%, #93c5fd 100%);
}
.obv3-card-line {
  height: 6px;
  margin: 0.35rem 0.4rem 0.4rem;
  border-radius: 3px;
  background: #e2e8f0;
  max-width: 85%;
}
.obv3-card-line--short {
  max-width: 55%;
}
.obv3-card-line--mid {
  max-width: 70%;
}
@media (min-width: 400px) {
  .obv3-search-ph {
    font-size: 0.72rem;
  }
  .obv3-chip {
    font-size: 0.62rem;
  }
  .obv3-card-art {
    height: 52px;
  }
}
</style>
