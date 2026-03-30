<!-- 引导幻灯片第 2 页配图：四步使用流程（无交互） -->
<template>
  <div class="obv2">
    <div class="obv2-track">
      <div class="obv2-step">
        <div class="obv2-node">
          <svg class="obv2-ico" viewBox="0 0 24 24" aria-hidden="true">
            <path
              fill="currentColor"
              d="M4 6h6v6H4V6zm8 0h8v3h-8V6zM4 14h6v4H4v-4zm8 5v-4h8v4h-8z"
            />
          </svg>
        </div>
        <span class="obv2-num">①</span>
        <span class="obv2-cap">选谱</span>
      </div>
      <div class="obv2-arrow" aria-hidden="true">
        <svg viewBox="0 0 24 12" class="obv2-arrow-svg">
          <path
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
            d="M2 6h16m-4-3l3 3-3 3"
          />
        </svg>
      </div>
      <div class="obv2-step">
        <div class="obv2-node">
          <svg class="obv2-ico" viewBox="0 0 24 24" aria-hidden="true">
            <path
              fill="currentColor"
              d="M12 14a3 3 0 100-6 3 3 0 000 6zm8-1v2H4v-2l4-4V7a4 4 0 118 0v2l4 4z"
            />
          </svg>
        </div>
        <span class="obv2-num">②</span>
        <span class="obv2-cap">上传演奏</span>
      </div>
      <div class="obv2-arrow" aria-hidden="true">
        <svg viewBox="0 0 24 12" class="obv2-arrow-svg">
          <path
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
            d="M2 6h16m-4-3l3 3-3 3"
          />
        </svg>
      </div>
      <div class="obv2-step">
        <div class="obv2-node">
          <svg class="obv2-ico" viewBox="0 0 24 24" aria-hidden="true">
            <path
              fill="currentColor"
              d="M5 9h3v10H5V9zm5.5-4h3v14h-3V5zM16 11h3v8h-3v-8zm5-5h3v13h-3V6z"
            />
          </svg>
        </div>
        <span class="obv2-num">③</span>
        <span class="obv2-cap">比对与任务</span>
      </div>
      <div class="obv2-arrow" aria-hidden="true">
        <svg viewBox="0 0 24 12" class="obv2-arrow-svg">
          <path
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
            d="M2 6h16m-4-3l3 3-3 3"
          />
        </svg>
      </div>
      <div class="obv2-step">
        <div class="obv2-node obv2-node--accent">
          <svg class="obv2-ico" viewBox="0 0 24 24" aria-hidden="true">
            <path
              fill="currentColor"
              d="M20 2H4a2 2 0 00-2 2v12a2 2 0 002 2h4v3l4-3h8a2 2 0 002-2V4a2 2 0 00-2-2z"
            />
          </svg>
        </div>
        <span class="obv2-num">④</span>
        <span class="obv2-cap">多轮对话</span>
      </div>
    </div>
  </div>
</template>

<script setup>
/* 无 props、无交互 */
</script>

<style scoped>
.obv2 {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  user-select: none;
}
.obv2-track {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  justify-content: center;
  flex-wrap: wrap;
  gap: 0.15rem 0.05rem;
  width: 100%;
  max-width: 380px;
  padding: 0.15rem 0;
  box-sizing: border-box;
}
.obv2-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
  min-width: 3.25rem;
  max-width: 4.5rem;
}
.obv2-node {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(145deg, #ffffff 0%, #f1f5f9 100%);
  border: 1px solid #cbd5e1;
  color: #475569;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    0 2px 6px rgba(15, 23, 42, 0.06);
}
.obv2-node--accent {
  background: linear-gradient(145deg, #eff6ff 0%, #dbeafe 100%);
  border-color: #93c5fd;
  color: #2563eb;
}
.obv2-ico {
  width: 20px;
  height: 20px;
}
.obv2-num {
  font-size: 0.65rem;
  font-weight: 600;
  color: #64748b;
  line-height: 1;
}
.obv2-cap {
  font-size: 0.58rem;
  line-height: 1.15;
  color: #475569;
  text-align: center;
  letter-spacing: 0.02em;
}
.obv2-arrow {
  flex-shrink: 0;
  width: 14px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  margin-top: 0;
  align-self: flex-start;
  padding-top: 10px;
}
.obv2-arrow-svg {
  width: 14px;
  height: 8px;
  display: block;
}
@media (min-width: 400px) {
  .obv2-cap {
    font-size: 0.62rem;
  }
  .obv2-arrow {
    width: 18px;
  }
  .obv2-arrow-svg {
    width: 18px;
    height: 10px;
  }
}
</style>
