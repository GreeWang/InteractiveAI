# Prompt2Scene Formative Findings（阶段性小结）

Updated: 2026-10-21T15:51:32+08:00 Asia/Shanghai (UTC+8)

## 研究问题（本阶段）

在 **官方 Unity Pipeline CLI**（无第三方 MCP）上，用 LLM 把自然语言 prompt 变成 CLI 命令计划，能否稳定完成：

1. **编辑**已有 Fixture（F02）
2. **约束**调整（F03 + Prompt2Scene-Check）
3. **生成**空场景物体（F01）
4. **Check 多轮修复**是否优于单次 baseline

对照模型：**DeepSeek V4-Pro** 与 **百炼 Qwen3.8-Max**。

## 已完成栈

| 组件 | 状态 |
|------|------|
| Unity 6 + Pipeline CLI | ✅ |
| Fixture F01/F02/F03 | ✅ |
| ConstraintChecker v0.2 | ✅ |
| LLM harness（DeepSeek + Bailian） | ✅ |
| Multiturn check（≤3 轮） | ✅ |
| Formal R1 / R2(+retry) / R3 generate / multiseed | ✅ |
| Check agent skill | `check/skill/SKILL.md` |

## 主要结果（语义 / ConstraintChecker）

### Formal seed=1（编辑+约束 P02–P09）

| Round | Model | baseline | check |
|-------|-------|----------|-------|
| R1（初跑） | deepseek-v4-pro | 7/8（P05❌） | 7/8（P05❌） |
| R2（初跑） | qwen3.8-max | 7/8（P05❌） | 6/8（P05 API断连 + P08 超时） |
| R2（retry + harden） | qwen3.8-max | **8/8** | **8/8** |
| P05 harden 冒烟 | DS + Qwen | ✅ | ✅（均 1 轮） |

### Generate R3（P01/P10 × baseline/check × 两模型，seed=1）

| Model | baseline | check |
|-------|----------|-------|
| deepseek-v4-pro | 2/2 | 2/2 |
| qwen3.8-max | 2/2 | 2/2 |

### Multiseed（P02–P09，seeds 2–3；seed 1 复用 R1/R2）

| Model | seeds 2–3 baseline | seeds 2–3 check |
|-------|--------------------|-----------------|
| deepseek-v4-pro | 15/16（P09 seed2 baseline 未抬高 y） | 16/16 |
| qwen3.8-max | 16/16 | 16/16 |

汇总表：`eval/RESULTS_FORMAL_MULTISEED.md`。

### 编辑题（P02/P03/P09）

两家模型在明确变换指令 + 已知 F02 种子下整体很稳；唯一 formal 失手是 DS seed=2 的 P09 baseline（SphereB 仍在 y=0.5），同格 check 修复通过。

### 约束题与 P05

- **根因**：模型假设 RedBox 在原点，把 CupOnBox 放到 `[0,1.5,0]` → XZ offset=1.5 > 0.5。
- **未放宽 checker**（`max_horizontal` 仍为 0.5）。
- **硬化**：系统提示 + P05 文案给出 F03 布局；multiturn 反馈带 `failed_messages` / `current_poses`；跑前 prep Cup→`[0,0.5,0]`。
- 硬化后两模型均可 1 轮通过（见 `eval/P05_HARDEN_EVIDENCE.md`）。

### Check vs baseline

- 反馈完整时，check 能修单次失误（如上述 P09）。
- 反馈残缺或 API 超时会把 check 记失败（R2 初跑）；retry 后恢复。
- 编辑题多数 1 轮即过，check 边际收益有限。

### DeepSeek vs Qwen

- 旗舰档在本矩阵上接近；Qwen multiseed 2–3 全过，DS 仅 1 格 baseline 失手。
- Bailian 偶发长尾延迟/超时（R2 初跑），不全是语义差。

## 局限

- 单场景、少物体、短 prompt；未测复杂层级/材质/动画。
- Multiseed 用 API `seed` + 低温（0.2），方差可能偏小。
- Generate 成功标准较简（存在性 + on_top / 间距）。
- 无人类被试；本仓库是 formative 工程 + 自动评测。

## 后续建议

1. 每次 user prompt 注入 Fixture 位姿快照（或先 `eval` 再喂模型）。
2. Check skill 作为默认修复工具；保证 report `message` 进入反馈。
3. 继续「故意错位」prep，避免种子已满足约束导致虚高。
4. 用户研究：轮次、主观可信度与 `sem_ok` 对照。

## 产物索引

- `eval/RESULTS_FORMAL_R1.md` / `RESULTS_FORMAL_R2.md`（含 retry）
- `eval/RESULTS_FORMAL_R3_GEN_DS.md` / `RESULTS_FORMAL_R3_GEN_QWEN.md`
- `eval/RESULTS_FORMAL_MULTISEED.md` (+ per-model `*_DS` / `*_QWEN`)
- `eval/P05_HARDEN_EVIDENCE.md`
- `check/skill/SKILL.md`
- `EVAL_PROTOCOL.md` / 根 `README.md`
