# 钢琴陪练 - 标准乐谱前端

Vue 3 + Vite，与后端 `/api/score` 配合使用。

## 运行

1. 安装依赖：`npm install`
2. 启动后端：在项目根目录 `cd backend && uvicorn app:app --reload --port 8000`
3. 启动前端：`npm run dev`，浏览器打开 http://localhost:5173
4. 前端通过 Vite 代理将 `/api` 请求转发到 8000 端口

## 功能

- 上传标准乐谱：PDF（乐谱图）+ MusicXML（标准答案）+ 可选 OMR（错音高亮）
- 大图展示乐谱，支持放大/缩小（按钮与滚轮）、拖拽平移
- 上传弹奏音频并比对，显示准确率与错音列表；若有 OMR 则在小节上红框高亮

## 构建

```bash
npm run build
```

产出在 `dist/`，可部署到任意静态服务器，需配置 API 代理或后端 CORS。
