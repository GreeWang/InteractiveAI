# Run logs

Each formative run writes a directory:

```
runs/<YYYYMMDD-HHMMSS>_<prompt_id>_<condition>/
  meta.json          # prompt id, fixture, condition (baseline|check), timestamps (Asia/Shanghai)
  commands.ndjson    # one line per unity CLI invocation
  stdout.log         # concatenated stdout
  stderr.log         # concatenated stderr
  result.json        # final success + summary
  scene_snapshot/    # optional: exported hierarchy / capture
```

## Naming
- `condition`: `baseline` (official CLI only) or later `check` (Prompt2Scene-Check).
- Timestamp: local Asia/Shanghai (`date +%Y%m%d-%H%M%S`).

## commands.ndjson line schema
```json
{
  "ts": "2026-10-17T15:40:00+08:00",
  "argv": ["unity","command","create_gameobject","--","--name","Cube","--primitive","cube"],
  "exit_code": 0,
  "duration_ms": 120,
  "success": true
}
```

Do not commit large binary captures; keep text logs only in git.
