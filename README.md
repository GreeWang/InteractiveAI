# InteractiveAI / Prompt2Scene

面向 formative study 的 **Prompt 驱动 Unity 场景编辑** 基线栈，配套约束校验 **Prompt2Scene-Check**。  
当前只使用 **官方 Unity Pipeline CLI + HTTP 服务**（默认端口 **7800**），不依赖第三方 MCP。真 LLM 生成尚未接入；已有自动化是「CLI 编辑冒烟」与「对种子场景跑约束校验」。

详细评测约定见：[EVAL_PROTOCOL.md](./EVAL_PROTOCOL.md)。工具版本与连通记录见：[BASELINE_STACK.txt](./BASELINE_STACK.txt)。

## 目录结构

| 路径 | 说明 |
|------|------|
| `eval/` | Prompt 集、冒烟 / A/B 脚本、结果摘要（`RESULTS_AB.md`、CSV） |
| `eval/prompts/prompts.json` | 评测 prompt（当前 10 条） |
| `eval/scripts/smoke_run.sh` | 单条冒烟（`baseline` / `check`） |
| `eval/scripts/run_ab_batch.sh` | 第一轮 formative A/B 批跑 |
| `check/` | 约束 JSON Schema、样例约束、校验辅助说明 |
| `Prompt2Scene-Baseline/` | Unity 6 URP 工程（Fixture 场景 + Check 的 Editor 脚本） |
| `vendor/` | 离线 `com.unity.pipeline` 包（可选，用于重装） |
| `EVAL_PROTOCOL.md` | 评测协议（Fixture、日志约定、CLI 用法） |
| `BASELINE_STACK.txt` | Unity / CLI / Pipeline 基线笔记 |

仓库内 Unity 工程路径为 `Prompt2Scene-Baseline/`。若本机仍保留旧路径 `~/Projects/Prompt2Scene-Baseline`，冒烟脚本默认会用那个；在本仓库跑时请设置：

```bash
export PROMPT2SCENE_PROJECT="$HOME/Projects/InteractiveAI/Prompt2Scene-Baseline"
```

## 环境要求（Unity 6 + Pipeline）

- **Unity Editor**：6000.x（实测 `6000.0.85f1`），URP 空白模板工程  
- **官方 CLI**：`~/.unity/bin/unity`（建议加入 `PATH`）  
- **Pipeline 包**：`com.unity.pipeline` **0.8.0-exp.1**，以本地嵌入方式安装（`file:com.unity.pipeline`，位于 `Prompt2Scene-Baseline/Packages/com.unity.pipeline`）  
- **服务**：Editor 打开工程后，Pipeline HTTP 应可达（`unity status` → 端口 **7800**）  
- 若 UPM 拉包失败，可用代理，或从 `vendor/com.unity.pipeline-0.8.0-exp.1.tgz` 解压到 `Packages/com.unity.pipeline`

```bash
export PATH="$HOME/.unity/bin:$PATH"
unity status
```

## 快速冒烟

先打开 Unity 工程并确认 Pipeline 已通，再在仓库根目录执行：

```bash
export PATH="$HOME/.unity/bin:$PATH"
export PROMPT2SCENE_PROJECT="$HOME/Projects/InteractiveAI/Prompt2Scene-Baseline"

# baseline：在 F02 上做 CLI 编辑冒烟（移动 SphereB 后还原）
./eval/scripts/smoke_run.sh P02_edit_move_sphere baseline

# check：打开 F03，跑 ConstraintChecker，并落盘 check_report.json
./eval/scripts/smoke_run.sh P04_constraint_left_of check

# 简写
./eval/scripts/smoke_run.sh baseline
./eval/scripts/smoke_run.sh check
```

运行日志目录：`eval/runs/<时间戳>_<prompt_id>_<condition>/`（含 `meta.json`、`commands.ndjson`、`result.json` 等）。  
批跑与摘要：`./eval/scripts/run_ab_batch.sh` → `eval/RESULTS_AB.md`。

Editor 菜单：**Prompt2Scene → Check → Run Sample F03 Constraints**（需先打开 Fixture `F03_ConstraintSandbox`）。

## Fixture 与约束（摘要）

- **F01_EmptyRoom**：从空场景生成类任务  
- **F02_EditBaseline**：编辑类（Floor / CubeA / SphereB）  
- **F03_ConstraintSandbox**：约束类（RedBox / BlueBall / CupOnBox 等种子物体）

约束类型见 `check/README.md`：v0.1（`must_exist`、`left_of`、`same_y`、`bounds`、`no_overlap`）与 v0.2（`on_top_of`、`distance`、`facing`）。  
更多步骤、日志字段与 CLI 参数说明请读 [EVAL_PROTOCOL.md](./EVAL_PROTOCOL.md)。

## Git 说明

已忽略 Unity 的 `Library/`、`Temp/`、`Logs/`、`UserSettings/`，以及生成的 `*.csproj` / `*.sln` 等。  
克隆后请用 Unity 打开一次 `Prompt2Scene-Baseline/`，以重新生成本地缓存与 IDE 工程文件。  
`eval/runs/` 下单次运行产物默认不入库（保留目录占位）；结果摘要在 `eval/RESULTS_AB.md` 与 CSV。
