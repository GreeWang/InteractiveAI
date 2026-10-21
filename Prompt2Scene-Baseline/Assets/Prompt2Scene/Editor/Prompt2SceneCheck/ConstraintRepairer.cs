using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEngine;

namespace Prompt2Scene.Check
{
    /// <summary>
    /// Bounded deterministic repair for clearance / no_overlap / on_top_of / grounding-ish.
    /// Never moves objects listed in constraint set.locked or locked_transform targets.
    /// Callable via Pipeline eval. Stops after maxRounds (default 3).
    /// </summary>
    public static class ConstraintRepairer
    {
        public const string LastRepairRelativePath = "Logs/prompt2scene-repair-last.json";

        public static RepairReport RepairFromPath(string absolutePath, int maxRounds = 3)
        {
            maxRounds = Mathf.Clamp(maxRounds, 1, 5);
            var actions = new List<string>();
            if (string.IsNullOrEmpty(absolutePath) || !File.Exists(absolutePath))
            {
                var miss = new RepairReport
                {
                    set_id = null,
                    attempted = false,
                    success_after = false,
                    rounds = 0,
                    actions = new string[0],
                    message = "constraint file missing: " + absolutePath,
                    repaired_at = DateTimeOffset.Now.ToString("o")
                };
                Write(miss);
                return miss;
            }

            var json = File.ReadAllText(absolutePath, Encoding.UTF8);
            if (json.Length > 0 && json[0] == '\uFEFF') json = json.Substring(1);
            var set = JsonUtility.FromJson<ConstraintSet>(json);
            if (set == null || set.constraints == null)
            {
                var bad = new RepairReport
                {
                    attempted = false,
                    success_after = false,
                    rounds = 0,
                    actions = new string[0],
                    message = "parse failed",
                    repaired_at = DateTimeOffset.Now.ToString("o")
                };
                Write(bad);
                return bad;
            }

            var locked = new HashSet<string>();
            if (set.locked != null)
                foreach (var n in set.locked)
                    if (!string.IsNullOrEmpty(n)) locked.Add(n);
            foreach (var c in set.constraints)
            {
                if (c != null && c.type == "locked_transform" && !string.IsNullOrEmpty(c.target))
                    locked.Add(c.target);
            }

            int round;
            CheckReport last = null;
            for (round = 1; round <= maxRounds; round++)
            {
                last = ConstraintChecker.RunFromPath(absolutePath);
                if (last.success)
                {
                    actions.Add("round" + round + ":already_ok");
                    break;
                }

                bool any = false;
                foreach (var r in last.results)
                {
                    if (r == null || r.passed || r.skipped) continue;
                    var def = FindDef(set, r.id);
                    if (def == null) continue;
                    any |= TryRepairOne(def, locked, actions, round);
                }
                if (!any)
                {
                    actions.Add("round" + round + ":no_deterministic_fix");
                    break;
                }
            }

            last = ConstraintChecker.RunFromPath(absolutePath);
            var report = new RepairReport
            {
                set_id = set.id,
                attempted = true,
                success_after = last != null && last.success,
                rounds = round,
                actions = actions.ToArray(),
                message = last != null
                    ? ("success=" + last.success + " failed=" + last.failed)
                    : "no_report",
                repaired_at = DateTimeOffset.Now.ToString("o")
            };
            Write(report);
            Debug.Log("[Prompt2Scene-Repair] " + report.message + " actions=" + actions.Count);
            return report;
        }

        static ConstraintDef FindDef(ConstraintSet set, string id)
        {
            foreach (var c in set.constraints)
                if (c != null && c.id == id) return c;
            return null;
        }

        static bool IsLocked(HashSet<string> locked, string name)
        {
            return !string.IsNullOrEmpty(name) && locked.Contains(name);
        }

        static bool TryRepairOne(ConstraintDef c, HashSet<string> locked, List<string> actions, int round)
        {
            switch (c.type)
            {
                case "no_overlap":
                    return RepairNoOverlap(c, locked, actions, round);
                case "clearance_volume":
                    return RepairClearance(c, locked, actions, round);
                case "on_top_of":
                    return RepairOnTop(c, locked, actions, round);
                case "same_y":
                    return RepairSameY(c, locked, actions, round);
                case "left_of":
                    return RepairLeftOf(c, locked, actions, round);
                default:
                    return false;
            }
        }

        static bool RepairNoOverlap(ConstraintDef c, HashSet<string> locked, List<string> actions, int round)
        {
            var ga = ConstraintChecker.FindByName(c.a);
            var gb = ConstraintChecker.FindByName(c.b);
            if (ga == null || gb == null) return false;
            var ca = ga.GetComponent<Collider>();
            var cb = gb.GetComponent<Collider>();
            if (ca == null || cb == null) return false;
            Vector3 dir; float dist;
            bool pen = Physics.ComputePenetration(
                ca, ca.transform.position, ca.transform.rotation,
                cb, cb.transform.position, cb.transform.rotation,
                out dir, out dist);
            if (!pen || dist <= 1e-5f) return false;

            // Prefer moving unlocked object; if both unlocked move the second (b)
            GameObject move = null;
            Vector3 push = dir.normalized * (dist + 0.05f);
            if (!IsLocked(locked, c.b)) { move = gb; }
            else if (!IsLocked(locked, c.a)) { move = ga; push = -push; }
            else return false;

            move.transform.position += push;
            actions.Add($"r{round}:no_overlap move={move.name} delta={push}");
            return true;
        }

        static bool RepairClearance(ConstraintDef c, HashSet<string> locked, List<string> actions, int round)
        {
            if (c.min == null || c.max == null) return false;
            float pad = c.padding;
            var vmin = c.min.ToVector3() - Vector3.one * pad;
            var vmax = c.max.ToVector3() + Vector3.one * pad;
            var center = (vmin + vmax) * 0.5f;
            var names = new List<string>();
            if (c.objects != null) foreach (var n in c.objects) if (!string.IsNullOrEmpty(n)) names.Add(n);
            if (!string.IsNullOrEmpty(c.target)) names.Add(c.target);
            if (!string.IsNullOrEmpty(c.a)) names.Add(c.a);
            if (!string.IsNullOrEmpty(c.b)) names.Add(c.b);

            bool any = false;
            foreach (var name in names)
            {
                if (IsLocked(locked, name)) continue;
                var go = ConstraintChecker.FindByName(name);
                if (go == null) continue;
                var p = go.transform.position;
                // If center of object inside keepout, push to nearest face + margin
                if (p.x >= vmin.x && p.x <= vmax.x && p.y >= vmin.y && p.y <= vmax.y && p.z >= vmin.z && p.z <= vmax.z)
                {
                    float dxL = p.x - vmin.x, dxR = vmax.x - p.x;
                    float dzB = p.z - vmin.z, dzF = vmax.z - p.z;
                    // prefer XZ push (keep y)
                    float best = dxL; Vector3 np = new Vector3(vmin.x - 0.1f, p.y, p.z);
                    if (dxR < best) { best = dxR; np = new Vector3(vmax.x + 0.1f, p.y, p.z); }
                    if (dzB < best) { best = dzB; np = new Vector3(p.x, p.y, vmin.z - 0.1f); }
                    if (dzF < best) { np = new Vector3(p.x, p.y, vmax.z + 0.1f); }
                    go.transform.position = np;
                    actions.Add($"r{round}:clearance move={name} to={np}");
                    any = true;
                }
            }
            return any;
        }

        static bool RepairOnTop(ConstraintDef c, HashSet<string> locked, List<string> actions, int round)
        {
            if (IsLocked(locked, c.a)) return false;
            var ga = ConstraintChecker.FindByName(c.a);
            var gb = ConstraintChecker.FindByName(c.b);
            if (ga == null || gb == null) return false;
            var pb = gb.transform.position;
            float dy = c.min_vertical > 0f ? Mathf.Max(0.75f, c.min_vertical + 0.2f) : 0.75f;
            var np = new Vector3(pb.x, pb.y + dy, pb.z);
            ga.transform.position = np;
            actions.Add($"r{round}:on_top snap={c.a} onto={c.b} pos={np}");
            return true;
        }

        static bool RepairSameY(ConstraintDef c, HashSet<string> locked, List<string> actions, int round)
        {
            // Move unlocked a to match b.y (or vice versa)
            var ga = ConstraintChecker.FindByName(c.a);
            var gb = ConstraintChecker.FindByName(c.b);
            if (ga == null || gb == null) return false;
            if (!IsLocked(locked, c.a))
            {
                var p = ga.transform.position; p.y = gb.transform.position.y;
                ga.transform.position = p;
                actions.Add($"r{round}:same_y set={c.a}.y={p.y}");
                return true;
            }
            if (!IsLocked(locked, c.b))
            {
                var p = gb.transform.position; p.y = ga.transform.position.y;
                gb.transform.position = p;
                actions.Add($"r{round}:same_y set={c.b}.y={p.y}");
                return true;
            }
            return false;
        }

        static bool RepairLeftOf(ConstraintDef c, HashSet<string> locked, List<string> actions, int round)
        {
            var ga = ConstraintChecker.FindByName(c.a);
            var gb = ConstraintChecker.FindByName(c.b);
            if (ga == null || gb == null) return false;
            if (ga.transform.position.x < gb.transform.position.x) return false;
            if (!IsLocked(locked, c.a))
            {
                var p = ga.transform.position;
                p.x = gb.transform.position.x - 1.0f;
                ga.transform.position = p;
                actions.Add($"r{round}:left_of move={c.a} x={p.x}");
                return true;
            }
            if (!IsLocked(locked, c.b))
            {
                var p = gb.transform.position;
                p.x = ga.transform.position.x + 1.0f;
                gb.transform.position = p;
                actions.Add($"r{round}:left_of move={c.b} x={p.x}");
                return true;
            }
            return false;
        }

        static void Write(RepairReport report)
        {
            try
            {
                var path = Path.GetFullPath(Path.Combine(Application.dataPath, "..", LastRepairRelativePath));
                Directory.CreateDirectory(Path.GetDirectoryName(path) ?? ".");
                File.WriteAllText(path, JsonUtility.ToJson(report, true), Encoding.UTF8);
            }
            catch (Exception e)
            {
                Debug.LogWarning("[Prompt2Scene-Repair] write failed: " + e.Message);
            }
        }
    }
}
