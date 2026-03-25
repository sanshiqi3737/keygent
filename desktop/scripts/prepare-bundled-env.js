#!/usr/bin/env node
/**
 * 发布者密钥：若存在 desktop/publisher.env，则复制为 _bundled_env/publisher-bundled.env，
 * 随 Electron 打进 resources/piano/，用户无需自己填 Key。
 *
 * 由 desktop/package.json 的 predist 在打包前自动执行。
 */
const fs = require('fs')
const path = require('path')

const desktopRoot = path.join(__dirname, '..')
const src = path.join(desktopRoot, 'publisher.env')
const outDir = path.join(desktopRoot, '_bundled_env')
const outFile = path.join(outDir, 'publisher-bundled.env')

fs.mkdirSync(outDir, { recursive: true })

const placeholder = `# 发布者未配置：将 publisher.env.example 复制为 desktop/publisher.env 并填写密钥后再执行打包。
# 用户仍可在 resources/piano/.env 中自行配置（会覆盖本文件中的同名变量）。
`

if (fs.existsSync(src)) {
  fs.copyFileSync(src, outFile)
  console.log(
    '[prepare-bundled-env] 已使用 desktop/publisher.env → 将打入 resources/piano/publisher-bundled.env'
  )
} else {
  fs.writeFileSync(outFile, placeholder, 'utf8')
  console.log(
    '[prepare-bundled-env] 未找到 desktop/publisher.env，已生成占位文件（助手需用户自备 .env，或打包前配置 publisher.env）'
  )
}
