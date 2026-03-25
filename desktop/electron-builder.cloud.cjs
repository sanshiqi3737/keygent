/**
 * 云端 Beta：不把 PyInstaller 后端打进包，体积小；需先用 VITE_PUBLIC_API_BASE 等构建前端。
 * 使用：npm run dist:cloud --prefix desktop
 */
const pkg = require('./package.json')
const build = JSON.parse(JSON.stringify(pkg.build))
build.productName = 'Piano Tutor Beta (Cloud)'
const filtered = build.extraResources.filter(
  (r) => !String(r.from || '').includes('dist_py/piano-backend'),
)
// 安装包内使用云端示例配置，避免误把开发机 backendMode=local 打进包
build.extraResources = filtered.filter((r) => r.to !== 'piano/app-config.json')
build.extraResources.push({
  from: 'app-config.cloud.example.json',
  to: 'piano/app-config.json',
  filter: ['**/*'],
})
module.exports = build
