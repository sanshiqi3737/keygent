# Piano Tutor 内测发版 Checklist

每次发 Beta 前，按此清单逐项打勾，减少“发出后才发现问题”。

## A. 代码与构建

- [ ] `npm run build --prefix frontend` 成功
- [ ] `npm run beta:bundle-backend` 成功
- [ ] `npm run beta:pack` 成功，产物位于 `desktop/dist-out/`
- [ ] 解压后可双击启动 `Piano Tutor Beta.exe`

## B. 基础功能冒烟

- [ ] 注册 / 登录 / 退出 正常
- [ ] 曲库上传、搜索、删除 正常（权限符合预期）
- [ ] 音频比对成功（至少测 1 个 WAV）
- [ ] 助手建议 / 对话可用（无密钥时 fallback 正常）
- [ ] 练习记录与音频删除功能正常

## C. 分端与配置

- [ ] 用户端入口正常（`index.html`）
- [ ] 管理端入口正常（`admin.html`）
- [ ] `VITE_PUBLIC_API_BASE` 指向正确
- [ ] `VITE_ADMIN_API_BASE` 指向正确（如使用）

## D. 更新机制

- [ ] `desktop/update-config.json` 的 `manifestUrl` 已配置
- [ ] 远端 manifest 可访问（HTTPS）
- [ ] `version` 与本次发版一致
- [ ] 如需强更，`min_supported_version` 已确认

## E. 安全与发布材料

- [ ] `desktop/publisher.env` 未提交到仓库
- [ ] `ADMIN_PASSCODE` 非默认弱口令
- [ ] 给测试用户的说明文档已更新
- [ ] 已准备已知问题与绕过方案（如 SmartScreen）

## F. 回滚准备

- [ ] 保留上一版下载地址
- [ ] 保留上一版 manifest
- [ ] 可在 10 分钟内切回上一版本
