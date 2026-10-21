# P05 on_top harden evidence

Updated: 2026-10-21T15:32:38+08:00 Asia/Shanghai

Checker thresholds unchanged (`max_horizontal=0.5`).
Prompt/system hints + prep CupOnBox→`[0,0.5,0]` before cell.

| run | provider | model | condition | ok | CupOnBox target | rounds |
|---|---|---|---|---|---|---|
| `20261021-153003_P05_constraint_on_top_baseline_llm` | bailian | qwen3.8-max | baseline | ✅ | `[-1.5,1.25,0]` | 1 |
| `20261021-153020_P05_constraint_on_top_baseline_llm` | bailian | deepseek-v4-pro | baseline | ✅ | `[-1.5,1.25,0]` | 1 |
| `20261021-153048_P05_constraint_on_top_check_llm` | deepseek | deepseek-v4-pro | check | ✅ | `[-1.5,1.25,0]` | 1 |
| `20261021-153101_P05_constraint_on_top_check_llm` | bailian | qwen3.8-max | check | ✅ | `[-1.5,1.25,0]` | 1 |

JSON:
```json
{
  "updated": "2026-10-21T15:32:38+08:00",
  "smokes": [
    {
      "run": "20261021-153003_P05_constraint_on_top_baseline_llm",
      "provider": "bailian",
      "model": "qwen3.8-max",
      "condition": "baseline",
      "success": true,
      "cup_position": "[-1.5,1.25,0]",
      "rounds": 1
    },
    {
      "run": "20261021-153020_P05_constraint_on_top_baseline_llm",
      "provider": "bailian",
      "model": "deepseek-v4-pro",
      "condition": "baseline",
      "success": true,
      "cup_position": "[-1.5,1.25,0]",
      "rounds": 1
    },
    {
      "run": "20261021-153048_P05_constraint_on_top_check_llm",
      "provider": "deepseek",
      "model": "deepseek-v4-pro",
      "condition": "check",
      "success": true,
      "cup_position": "[-1.5,1.25,0]",
      "rounds": 1
    },
    {
      "run": "20261021-153101_P05_constraint_on_top_check_llm",
      "provider": "bailian",
      "model": "qwen3.8-max",
      "condition": "check",
      "success": true,
      "cup_position": "[-1.5,1.25,0]",
      "rounds": 1
    }
  ]
}
```
