---
name: unity-scene-check
description: Check the public task contract, audit state changes, and repair verified failures.
---

# Unity Scene Check

Use this workflow together with unity-scene-ops.

1. Before editing, read the complete public task contract.
   Identify allowed object-field changes and the fields that must remain unchanged.
2. Plan the smallest edit batch that can satisfy the current requirements.
   Do not edit protected references to make a relation easier to satisfy.
3. After every apply_edits call, call check_constraints for the full public contract,
   then call compare_state against the original task snapshot.
   Both tools are read-only and their costs count against the shared budget.
4. If failures are reported, use their measurements and actual state differences.
   Restore unauthorized changes and correct the responsible permitted fields.
   Do not discard requirements or assume that checking only one object is sufficient.
5. Recheck after a repair. There are at most four edit batches in total.
   If repeated attempts do not resolve an issue, stop within the budget and report it.
6. Before claiming complete, ensure the latest check and diff correspond to the state
   after the last edit and show no unresolved requirement or unauthorized change.
   A tool error or missing check result is not a pass.
7. If evidence is incomplete or requirements remain unmet, use partial or failed
   and list the unresolved issues. Do not claim zero defects or invent measurements.
