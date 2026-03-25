# 架构说明（测试阶段 / 无智能体）

本仓库当前聚焦 **客观弹奏数据**：乐谱解析、音频转音符、与标准序列比对、练习指标与本地持久化。**不包含** NLP、情绪、人脸或智能体决策逻辑。

## 数据流（简图）

```
MusicXML/MIDI 文件 ──► 解析为 MidiNote 列表（参考）
用户音频文件       ──► 转录为 MidiNote 列表（演奏）
                              │
                              ▼
                    compare_midi_note_sequences
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
        accuracy + errors            （可选）reference_notes / played_notes
              │                               │
              │                               ▼
              │                    POST /api/practice/sessions
              │                               │
              │                               ▼
              │                    SQLite data/practice/practice.db
              └──────────────────────────────► 前端展示（compare 响应含 `metrics`：稳定性、薄弱小节等）
```

- **核心比对接口**默认只返回轻量结果；需要完整练习指标时再带 `include_note_snapshots=true` 并写入练习 API。
- **MusicXML 解析**在进程内通过 `reference_cache` 按文件 `mtime` 缓存，同一乐谱多次比对可减少 music21 开销。

## 主要模块

| 区域 | 路径 | 职责 |
|------|------|------|
| HTTP 入口 | `backend/app.py` | 挂载 score / practice 等路由 |
| 比对编排 | `backend/score_compare_service.py` | MusicXML+音频比对，无 HTTP |
| 乐谱解析 | `backend/audio_processing/musicxml_parser.py` | music21 |
| 解析缓存 | `backend/reference_cache.py` | 内存缓存 |
| 音频转录 | `backend/audio_processing/note_transcriber.py` | 单音 / multipitch |
| 序列比对 | `backend/audio_processing/comparator.py` | DTW 等 |
| 练习指标 | `backend/audio_processing/performance_metrics.py` | schema_version 2 |
| 练习持久化 | `backend/practice_store.py` | SQLite：sessions + events |
| 练习 API | `backend/routes/practice.py` | CRUD + summary + events |
| 练习建议 | `backend/routes/assistant.py` | `POST /api/assistant/suggest`（百炼通义，读练习概况） |
| 乐谱比对 API | `backend/routes/score.py` | 上传/比对；弹奏可为 **音频** 或 **MIDI** |

## 练习相关 API 一览

（均可通过 `ENABLE_PRACTICE_API=false` 整体关闭，返回 503。）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/practice/sessions` | 写入一次练习会话 |
| GET | `/api/practice/sessions` | 列表 |
| GET | `/api/practice/sessions/{id}` | 详情 |
| GET | `/api/practice/summary` | 最近 N 次会话聚合 |
| POST | `/api/practice/events` | 记录用户/客户端事件 |
| GET | `/api/practice/events` | 事件列表 |

指标字段含义见 **`docs/METRICS.md`**。

## 后续扩展（未实现）

- **智能体**：建议独立服务或模块，只读练习库与事件，失败不影响比对。
- **谱库 / 多端同步**：当前 `score_id` 为字符串占位即可，待产品阶段再设计。
