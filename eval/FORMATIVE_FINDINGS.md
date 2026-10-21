# Prompt2Scene Formative Findings（阶段性小结）

Updated: 2026-10-21 Asia/Shanghai (UTC+8)

## 研究问题（本阶段）

在 **官方 Unity Pipeline CLI**（无第三方 MCP）上，用 LLM 把自然语言 prompt 变成 CLI 命令计划，能否稳定完成：

1. **编辑**已有 Fixture（F02）
2. **约束**调整（F03 + Prompt2Scene-Check）
3. **生成**空场景物体（F01）
4. **Check 多轮修复**是否优于单次 baseline

对照模型：**DeepSeek V4-Pro**（R1）与 **百炼 Qwen3.8-Max**（R2）。

## 已完成栈

| 组件 | 状态 |
|------|------|
| Unity 6 + Pipeline CLI | ✅ |
| Fixture F01/F02/F03 | ✅ |
| ConstraintChecker v0.2 | ✅ |
| LLM harness（OpenAI 兼容：DeepSeek + Bailian） | ✅ |
| Multiturn check（最多 3 轮） | ✅ |
| Formal R1 / R2 / generate R3 / multiseed | 见 `eval/RESULTS_*.md` |
| Check agent skill | `check/skill/SKILL.md` |

## 主要结果（语义 / ConstraintChecker）

> 数字以各 RESULTS 文件为准；此处为 formative 解读。

### 编辑题（P02/P03/P09）

- 两家模型、baseline / check **几乎全过**。短、明确的变换指令 + 已知 F02 种子坐标时，指令遵循很稳。

### 约束题（P04–P08）

- **P04/P06/P07/P08**：多数单次即可。
- **P05 on_top**：R1/R2 初跑时系统失败。根因不是 checker 阈值，而是模型 **默认把 RedBox 当成原点**，把 CupOnBox 放到 `[0,1.5,0]`，相对真实种子 `RedBox≈(-1.5,0.5,0)` 产生 **XZ offset=1.5 > 0.5**。Check 多轮也曾因反馈里缺少失败 `message` 而反复猜原点。
- **硬化后**（系统提示 + P05 文案给出 F03 布局；multiturn 附带 `failed_messages` / `current_poses`；跑前将 Cup 挪到 `[0,0.5,0]`）：DeepSeek 与 Qwen 的 P05 baseline/check **均可 1 轮通过**（冒烟证据见 harden 后 run 目录）。

### Check vs baseline

- 编辑题：check 很少需要 >1 轮，收益有限。
- 约束题：在 **反馈信息完整** 时，check 能修单次失误；反馈残缺或 API 超时（R2 的 P05/P08 check）时，check 反而记失败。
- 结论：Check agent 有价值，但依赖 **可读的失败细节** 与 **稳定的模型 API**。

### DeepSeek vs Qwen

- 编辑：持平、都强。
- 约束：旗舰档接近；R2 初跑 Qwen check 侧多两个 **传输层** 失败（断连 / 读超时），不全是语义差。
- 生成（P01/P10）：见 R3 结果表。

## P05 失败模式（可复现叙事）

1. 模型在 notes 里写「假设 RedBox 在 (0,0.5,0)」。
2. 单次计划里调用 `get_component_properties` **并不能**在同一次计划中读回结果。
3. Checker 正确拒绝 XZ 偏移。
4. 修复：注入 Fixture 种子坐标 + 明确「对齐 support 的 X/Z」；不要放宽 `max_horizontal`（本阶段 **未** 放宽阈值）。

## 局限

- 单场景、少物体、英文/中文短 prompt；未测复杂层级、材质、动画。
- Multiseed 为 API `seed` + 重复跑，温度仍偏低（0.2），方差可能偏小。
- Bailian 偶发长尾延迟 / 超时。
- Generate 成功标准较简（存在性 + 间距 / on_top），未做美学或物理仿真评分。
- 未做人类被试；本仓库是 **formative 工程 + 自动评测**。

## 对课设后续的建议

1. 把 Fixture 布局 **显式写进** 每次 user prompt（或先 `eval` 快照再喂给模型）。
2. Check skill 作为默认修复工具；保证 report `message` 进入反馈。
3. 扩展物体集合与「故意错位」prep，避免种子已满足约束导致虚高。
4. 若做用户研究：记录修改轮次、主观可信度，与自动 sem_ok 对照。

## 产物索引

- `eval/RESULTS_FORMAL_R1.md` — DeepSeek P02–P09
- `eval/RESULTS_FORMAL_R2.md` — Qwen P02–P09（含 retry）
- `eval/RESULTS_FORMAL_R3_GEN_*.md` — P01/P10
- `eval/RESULTS_FORMAL_MULTISEED.md` — 多种子汇总
- `check/skill/SKILL.md` — Check agent skill
- `EVAL_PROTOCOL.md` / 根 `README.md` — 协议与用法
