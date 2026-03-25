# 练习记录 metrics 字段说明

供智能体与数据分析使用；核心比对接口不依赖本结构。

当前 **`schema_version`: 3**（旧库中可能仍有 2，无 `stability` / `weak_measures_ranked` 字段）。

## `pitch`

| 字段 | 说明 |
|------|------|
| `accuracy` | 音准相关准确率（与比对器一致） |
| `wrong` / `missed` / `extra` | 错误条数 |
| `error_total` | 错误总数 |
| `wrong_ratio` / `missed_ratio` / `extra_ratio` | 各类型占错误总数比例 |

## `rhythm`（需同时提供 reference_notes + played_notes 存档时才有）

| 字段 | 说明 |
|------|------|
| `available` | 是否具备 DTW 节奏统计 |
| `mean_abs_onset_ms` / `median_abs_onset_ms` | 起音绝对偏差（ms） |
| `std_abs_onset_ms` | 标准差（波动↑常与不稳定相关） |
| `cv_onset` | 变异系数 std/mean |
| `p90_abs_onset_ms` | 90 分位偏差 |
| `score` | 由 mean 映射的 0–1 简分（可作起音稳定分） |
| `matched_timing_pairs` | 参与统计的音符对数 |

仅 `accuracy`+`errors` 存档时：`rhythm.available=false`，`reason=no_note_snapshots`。

## `weak_measures`

`{ "小节号": 该小节错误条数 }`（仅统计带 `measure` 的错误事件）

## `weak_measures_ranked`（schema 3）

按 `error_count` **降序**的列表：`[{ "measure": "7", "error_count": 21 }, ...]`

## `stability`（schema 3，**不含力度**）

单次练习弹奏稳定性，综合 **起音时间一致性** 与 **错音密度**。

| 字段 | 说明 |
|------|------|
| `timing_available` | 是否有可用的节奏/起音统计 |
| `timing_stability_score` | 同 `rhythm.score`（0–1） |
| `onset_std_ms` / `onset_cv` / `onset_p90_ms` | 起音偏差波动 |
| `mean_onset_deviation_ms` | 平均起音偏差 |
| `pitch_error_density` | `error_total / reference_note_count`（有参考音符数时） |
| `composite_stability_score` | 0–1 综合分（越高越稳）；无起音数据时退化为 `accuracy` |
| `note` | 人类可读说明 |

## 概况 API `stability_across_sessions`

窗口内多次会话的波动（**不含力度**）：

| 字段 | 说明 |
|------|------|
| `accuracy_std` | 准确率标准差（≥2 条会话） |
| `accuracy_range` | 准确率 max−min |
| `rhythm_score_std` | 各次 `rhythm.score` 的标准差（≥2 条且含节奏分） |
| `composite_stability_mean` | 各次 `composite_stability_score` 的均值（schema≥3 的会话） |
| `sessions_with_composite` | 参与综合分均值的会话数 |
