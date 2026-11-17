---
name: unity-scene-ops
description: Shared operating instructions for the controlled Unity editing experiment.
---

# Unity Scene Operations

Use the available tools to complete the user request and the public task contract.

1. Read the task, public contract, current scene, and initial-state reference.
   Use exact object IDs and the coordinate and distance conventions in the contract.
2. Use absolute world positions and absolute yaw values when calling apply_edits.
   A requested translation does not authorize rotation, scaling, renaming, or other changes.
3. Change only the permitted fields. Preserve other fields and non-target objects.
   Do not create, delete, duplicate, reparent, or scale objects in this experiment.
   If you accidentally change a protected field, you may restore its original value.
4. You may inspect the scene again, reason about the constraints, and revise your edits.
   All reads and edits must stay within the shared run budget.
5. Tool errors are execution evidence. Do not assume a rejected or uncertain edit succeeded.
6. Submit finish with status complete, partial, or failed, plus summary,
   verified, unresolved, and limitations. Report actual evidence and uncertainty.
