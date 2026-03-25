# Piano Tutor 云端部署最小步骤

目标：用最少步骤把 `public_app` 和 `admin_app` 部署到云端，可供 Beta 用户直接连接。

## 1) 服务器准备

- 一台 Linux 云主机（2C4G 起步）
- 一个主域名（如 `api.example.com`）
- 可选一个管理子域名（如 `admin-api.example.com`）
- 已安装：`python3.10+`、`nginx`、`git`

## 2) 拉代码与安装依赖

```bash
git clone <your-repo-url> piano_project_2
cd piano_project_2
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

## 3) 配置环境变量

在项目根创建 `.env`（或用系统环境变量），至少包含：

```env
DASHSCOPE_API_KEY=xxx
DASHSCOPE_MODEL=qwen-turbo
ADMIN_PASSCODE=replace_me
```

## 4) 启动两个后端进程

### 用户端 API（8765）

```bash
python -m uvicorn backend.app:public_app --host 127.0.0.1 --port 8765
```

### 管理端 API（8766）

```bash
python -m uvicorn backend.app:admin_app --host 127.0.0.1 --port 8766
```

生产环境建议用 `systemd` 守护进程，避免断线后服务退出。

## 5) Nginx 反向代理 + HTTPS

- `https://api.example.com` -> `http://127.0.0.1:8765`
- `https://admin-api.example.com` -> `http://127.0.0.1:8766`

并用 Let's Encrypt 配置 TLS 证书。

### 音频比对上传（必配）

Nginx 默认 `client_max_body_size` 仅约 1MB，上传 wav/mp3 会失败。在两个 `server` 的 `location /` 内增加：

```nginx
client_max_body_size 100M;
proxy_read_timeout 300s;
proxy_send_timeout 300s;
```

改完后执行 `nginx -t && systemctl reload nginx`。

## 6) 前端接入云端

用户端启动/构建时配置：

```env
VITE_PUBLIC_API_BASE=https://api.example.com
VITE_ADMIN_API_BASE=https://admin-api.example.com
```

说明：
- 用户页面请求会走 `VITE_PUBLIC_API_BASE`
- 管理页面请求会走 `VITE_ADMIN_API_BASE`

## 6.1) 性能（Beta 连云、比对「特别慢」时）

- **网络**：每次比对会上传整段录音；wav 越大越慢。可引导用户录短一点、或导出 **MIDI** 比对（不经转录）。
- **CPU**：音频默认走 `librosa.pyin` 转录，时长越长越慢；**多声部**（`use_multipitch=true`）会跑 PyTorch，在小规格 ECS 上非常重。公开 API 默认已关多声部；前端勿勾选「多声部」除非必要。
- **环境变量**（写入服务器 `/opt/piano_project_2/.env` 后重启 `piano-public`）：
  - `PIANO_UPLOAD_ASSESSMENT_LLM=false`：上传曲谱时不再调用百炼微调难度（仍保留规则评估），上传会快一截。
  - `PIANO_TRANSCRIBE_HOP_LENGTH=384` 或 `512`：转录略加快、精度略降，可试。

## 7) 上线前自检

- `GET https://api.example.com/health` 返回 `{"status":"ok"}`
- `GET https://admin-api.example.com/health` 返回 `{"status":"ok","scope":"admin"}`
- 用户端可登录、上传、比对、助手可用
- 管理端可登录并读取/修改 runtime config

## 8) 最低运维建议

- 每日备份 `backend/data/`（SQLite 与上传文件）
- 保留 Nginx 与应用日志（至少 7 天）
- 对 `ADMIN_PASSCODE` 做周期轮换
