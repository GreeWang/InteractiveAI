# Week-2 Decision Gate — Prompt2Scene Formative

Updated: 2026-10-21 Asia/Shanghai (UTC+8)

依据课设 proposal（2026-10-15）Week-2 gate：至少 2 人提到 / ≥2 briefs / ≥3 次 baseline 复现后，才继续空间约束方向。本仓库**无真人访谈**；以下用自动化 formative 证据代替「人数」门槛，并显式标出仍属 human-only 的部分。

## 1. Evidence (existing automated formative)

| Source | What it showed |
|--------|----------------|
| Formal R1 `deepseek-v4-pro` P02–P09 | baseline/check 各 **7/8**；唯一系统失败 **P05 on_top**（XZ 偏到原点） |
| Formal R2 `qwen3.8-max` + retry + P05 harden | 重跑后 baseline/check **8/8** |
| Formal R3 generate P01/P10 | DS + Qwen 各 **4/4** |
| Multiseed 1–3（P02–P09） | Qwen **24/24·24/24**；DS **23/24·24/24**（仅 P09 seed2 baseline 失手，check 修好） |
| P05 harden (`eval/P05_HARDEN_EVIDENCE.md`) | 未放宽 checker；强化 prompt + 反馈位姿后两模型 1 轮通过 |
| 失败归因（编码） | `on_top_xz_origin_assumption`、偶发 API/超时、少数 raise 漏改 y |

对应 proposal 判据的自动化替代：

- **≥2 briefs 复现**：P02–P10 共 10 个 brief；约束类 P04–P08 多次复现。
- **≥3 次 baseline 复现**：multiseed × 双模型 × 多格。
- **「至少 2 人提到」**：❌ 未做访谈 → **不宣称满足真人门槛**；决策仅绑定「工具栈 + 约束失败可复现」。

## 2. Decision

**继续空间 Prompt2Scene-Check MVP：YES。**

理由：

1. 官方 Unity 6 Pipeline CLI 栈已可复现；无第三方 MCP。
2. 空间约束失败可稳定复现（尤其 on_top XZ），且 Check 多轮在反馈完整时能兜底。
3. 编辑/生成在短 brief 上已够用；边际价值在 **确定性检查 + 有界修复**，与 proposal 主线一致。
4. 未满足真人访谈门槛 → 本决策标记为 **agent-gate / formative-automation**，不是完整 Week-2 human gate。

## 3. Frozen evaluation task list (subsequent automated work)

锁定以下任务族（ID 可扩展，语义不变）：

| ID | Family | Fixture | Notes |
|----|--------|---------|-------|
| P01 | generate | F01 | Table+Cup on_top |
| P02 | edit | F02 | SphereB above CubeA |
| P03 | edit | F02 | CubeC ~1.5m |
| P04 | constraint | F03 | left_of + same_y |
| P05 | constraint | F03 | on_top_of |
| P06 | constraint | F03 | distance band |
| P07 | constraint | F03 | facing |
| P08 | constraint | F03 | no_overlap |
| P09 | edit | F02 | raise y=2 |
| P10 | generate | F01 | A/B/C row |
| P11 | constraint | F03 | **clearance_volume** (keep-out AABB) |
| P12 | constraint | F03 | **locked_transform** + edit others |

Held-out briefs（`H01+`）不得与上表训练/调试文案相同；A/B 主实验固定 **单一模型**（默认 `qwen3.8-max`）以保证条件公平。

## 4. Explicitly human-only (out of agent closeout)

- 6 名场景作者 think-aloud / 访谈
- 6–8 人 counterbalanced A/B + 易用性评分
- 独立第二评估者 audit（本仓库 checker P/R 为 **single-annotator**）
- 真实工作流招募、知情同意、匿名化
- Unity 内置 Assistant 对照（需账号开通）

## 5. Sign-off

- Gate owner: agent closeout on behalf of Green Wong (repo automation)
- Date: 2026-10-21 Asia/Shanghai
- Next: Check schema v0.3（clearance / locked）、~20 catalog、task matrix、held-out A/B、checker P/R、skill ablation、文档收口
