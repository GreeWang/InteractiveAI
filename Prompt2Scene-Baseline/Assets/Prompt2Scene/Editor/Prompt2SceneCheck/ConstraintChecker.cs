using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEngine;

namespace Prompt2Scene.Check
{
    /// <summary>
    /// Prompt2Scene-Check: load constraint JSON (schema v0.3) and report pass/fail.
    /// Adds clearance_volume (AABB keep-out) and locked_transform.
    /// Results include object ids + measurement/expected strings.
    /// </summary>
    public static class ConstraintChecker
    {
        public const string DefaultSampleAssetPath =
            "Assets/Prompt2Scene/Check/Constraints/F03_sample.json";

        public const string LastReportRelativePath =
            "Logs/prompt2scene-check-last.json";

        public const string SchemaVersion = "0.3";

        public static CheckReport RunDefaultSample()
        {
            var abs = Path.Combine(Application.dataPath, "Prompt2Scene/Check/Constraints/F03_sample.json");
            return RunFromPath(abs);
        }

        public static CheckReport RunFromPath(string absolutePath)
        {
            if (string.IsNullOrEmpty(absolutePath) || !File.Exists(absolutePath))
            {
                var empty = new CheckReport
                {
                    set_id = null,
                    source_path = absolutePath,
                    success = false,
                    passed = 0,
                    failed = 1,
                    skipped = 0,
                    schema_version = SchemaVersion,
                    results = new[]
                    {
                        new CheckResult
                        {
                            id = "load",
                            type = "load",
                            passed = false,
                            skipped = false,
                            message = "Constraint file not found: " + absolutePath
                        }
                    },
                    checked_at = DateTimeOffset.Now.ToString("o")
                };
                WriteReport(empty);
                return empty;
            }

            var json = File.ReadAllText(absolutePath, Encoding.UTF8);
            if (json.Length > 0 && json[0] == '\uFEFF')
                json = json.Substring(1);
            var set = JsonUtility.FromJson<ConstraintSet>(json);
            if (set == null || set.constraints == null)
            {
                var bad = new CheckReport
                {
                    set_id = null,
                    source_path = absolutePath,
                    success = false,
                    failed = 1,
                    schema_version = SchemaVersion,
                    results = new[]
                    {
                        new CheckResult
                        {
                            id = "parse",
                            type = "parse",
                            passed = false,
                            message = "Failed to parse ConstraintSet JSON"
                        }
                    },
                    checked_at = DateTimeOffset.Now.ToString("o")
                };
                WriteReport(bad);
                return bad;
            }

            // Editor/CLI moves often leave Collider.bounds stale until sync.
            Physics.SyncTransforms();

            var results = new List<CheckResult>();
            int passed = 0, failed = 0, skipped = 0;

            foreach (var c in set.constraints)
            {
                var r = Evaluate(c);
                results.Add(r);
                if (r.skipped) skipped++;
                else if (r.passed) passed++;
                else failed++;
            }

            var report = new CheckReport
            {
                set_id = set.id,
                source_path = absolutePath,
                success = failed == 0,
                passed = passed,
                failed = failed,
                skipped = skipped,
                results = results.ToArray(),
                checked_at = DateTimeOffset.Now.ToString("o"),
                schema_version = SchemaVersion
            };
            WriteReport(report);
            LogReport(report);
            return report;
        }

        static CheckResult Evaluate(ConstraintDef c)
        {
            if (c == null || string.IsNullOrEmpty(c.type))
                return Fail(c, "Missing constraint type");

            switch (c.type)
            {
                case "must_exist": return EvalMustExist(c);
                case "left_of": return EvalLeftOf(c);
                case "same_y": return EvalSameY(c);
                case "bounds": return EvalBounds(c);
                case "no_overlap": return EvalNoOverlap(c);
                case "on_top_of": return EvalOnTopOf(c);
                case "distance": return EvalDistance(c);
                case "facing": return EvalFacing(c);
                case "clearance_volume": return EvalClearanceVolume(c);
                case "locked_transform": return EvalLockedTransform(c);
                default:
                    return new CheckResult
                    {
                        id = c.id,
                        type = c.type,
                        passed = false,
                        skipped = true,
                        message = "Unknown constraint type: " + c.type
                    };
            }
        }

        static CheckResult EvalMustExist(ConstraintDef c)
        {
            var go = FindByName(c.target);
            if (go == null)
                return Fail(c, "GameObject not found: " + c.target, c.target, null, "missing", "exists");
            return Pass(c, "Found " + c.target, c.target, null, "exists=1", "exists");
        }

        static CheckResult EvalLeftOf(ConstraintDef c)
        {
            var ga = FindByName(c.a);
            var gb = FindByName(c.b);
            if (ga == null || gb == null)
                return Fail(c, "Missing object(s) for left_of: a=" + c.a + " b=" + c.b, c.a, c.b, null, "a.x < b.x");
            float ax = ga.transform.position.x, bx = gb.transform.position.x;
            bool ok = ax < bx;
            return ok
                ? Pass(c, c.a + ".x=" + ax + " < " + c.b + ".x=" + bx, c.a, c.b, "ax=" + ax + ";bx=" + bx, "a.x < b.x")
                : Fail(c, c.a + " is not left of " + c.b, c.a, c.b, "ax=" + ax + ";bx=" + bx, "a.x < b.x");
        }

        static CheckResult EvalSameY(ConstraintDef c)
        {
            var ga = FindByName(c.a);
            var gb = FindByName(c.b);
            if (ga == null || gb == null)
                return Fail(c, "Missing object(s) for same_y", c.a, c.b, null, "|dy|<=eps");
            float eps = c.epsilon > 0f ? c.epsilon : 0.05f;
            float dy = Mathf.Abs(ga.transform.position.y - gb.transform.position.y);
            return dy <= eps
                ? Pass(c, "|dy|=" + dy + " <= " + eps, c.a, c.b, "dy=" + dy, "|dy|<=" + eps)
                : Fail(c, "|dy|=" + dy + " > " + eps, c.a, c.b, "dy=" + dy, "|dy|<=" + eps);
        }

        static CheckResult EvalBounds(ConstraintDef c)
        {
            var go = FindByName(c.target);
            if (go == null)
                return Fail(c, "GameObject not found: " + c.target, c.target, null, null, "inside min..max");
            if (c.min == null || c.max == null)
                return Fail(c, "bounds requires min and max", c.target, null, null, "min/max");
            var p = go.transform.position;
            var min = c.min.ToVector3();
            var max = c.max.ToVector3();
            bool inside = p.x >= min.x && p.x <= max.x
                          && p.y >= min.y && p.y <= max.y
                          && p.z >= min.z && p.z <= max.z;
            string meas = "pos=" + p;
            return inside
                ? Pass(c, c.target + " inside bounds @ " + p, c.target, null, meas, "inside AABB")
                : Fail(c, c.target + " outside bounds @ " + p, c.target, null, meas, "inside AABB");
        }

        static CheckResult EvalNoOverlap(ConstraintDef c)
        {
            var ga = FindByName(c.a);
            var gb = FindByName(c.b);
            if (ga == null || gb == null)
                return Fail(c, "Missing object(s) for no_overlap", c.a, c.b, null, "no_penetration");

            var ca = ga.GetComponent<Collider>();
            var cb = gb.GetComponent<Collider>();
            if (ca == null || cb == null)
            {
                return new CheckResult
                {
                    id = c.id,
                    type = c.type,
                    passed = false,
                    skipped = true,
                    object_a = c.a,
                    object_b = c.b,
                    message = "no_overlap needs Colliders on both; missing on "
                              + (ca == null ? c.a : "") + (ca == null && cb == null ? " and " : "")
                              + (cb == null ? c.b : "")
                };
            }

            Vector3 dir;
            float distance;
            bool penetrating = Physics.ComputePenetration(
                ca, ca.transform.position, ca.transform.rotation,
                cb, cb.transform.position, cb.transform.rotation,
                out dir, out distance);

            if (penetrating && distance > 1e-5f)
                return Fail(c, "Overlap depth=" + distance + " dir=" + dir, c.a, c.b,
                    "depth=" + distance + ";dir=" + dir, "depth<=0");
            return Pass(c, "No penetration (ComputePenetration)", c.a, c.b, "depth=0", "depth<=0");
        }

        static CheckResult EvalOnTopOf(ConstraintDef c)
        {
            var ga = FindByName(c.a);
            var gb = FindByName(c.b);
            if (ga == null || gb == null)
                return Fail(c, "Missing object(s) for on_top_of: a=" + c.a + " b=" + c.b, c.a, c.b, null, "aligned_on_top");

            var pa = ga.transform.position;
            var pb = gb.transform.position;
            float dy = pa.y - pb.y;
            float horiz = Vector2.Distance(new Vector2(pa.x, pa.z), new Vector2(pb.x, pb.z));

            float maxH = c.max_horizontal > 0f ? c.max_horizontal : 0.5f;
            float minV = c.min_vertical;
            float maxV = c.max_vertical > 0f ? c.max_vertical : 2f;
            string meas = "dy=" + dy + ";horiz=" + horiz;

            if (dy < minV)
                return Fail(c, "not above enough: dy=" + dy + " < min_vertical=" + minV, c.a, c.b, meas,
                    "horiz<=" + maxH + ";dy in [" + minV + "," + maxV + "]");
            if (dy > maxV)
                return Fail(c, "too high: dy=" + dy + " > max_vertical=" + maxV, c.a, c.b, meas,
                    "horiz<=" + maxH + ";dy in [" + minV + "," + maxV + "]");
            if (horiz > maxH)
                return Fail(c, "XZ offset=" + horiz + " > max_horizontal=" + maxH, c.a, c.b, meas,
                    "horiz<=" + maxH + ";dy in [" + minV + "," + maxV + "]");
            return Pass(c, c.a + " on " + c.b + " dy=" + dy + " horiz=" + horiz, c.a, c.b, meas,
                "horiz<=" + maxH + ";dy in [" + minV + "," + maxV + "]");
        }

        static CheckResult EvalDistance(ConstraintDef c)
        {
            var ga = FindByName(c.a);
            var gb = FindByName(c.b);
            if (ga == null || gb == null)
                return Fail(c, "Missing object(s) for distance", c.a, c.b, null, "in_band");

            float d = Vector3.Distance(ga.transform.position, gb.transform.position);
            bool hasMin = c.min_distance >= 0f;
            bool hasMax = c.max_distance >= 0f;
            if (!hasMin && !hasMax)
                return Fail(c, "distance requires min_distance and/or max_distance (>=0)", c.a, c.b, "d=" + d, "band");

            string expected = "[" + (hasMin ? c.min_distance.ToString() : "-inf")
                              + ", " + (hasMax ? c.max_distance.ToString() : "+inf") + "]";
            if (hasMin && d < c.min_distance)
                return Fail(c, "dist=" + d + " < min_distance=" + c.min_distance, c.a, c.b, "d=" + d, expected);
            if (hasMax && d > c.max_distance)
                return Fail(c, "dist=" + d + " > max_distance=" + c.max_distance, c.a, c.b, "d=" + d, expected);
            return Pass(c, "dist=" + d + " in " + expected, c.a, c.b, "d=" + d, expected);
        }

        static CheckResult EvalFacing(ConstraintDef c)
        {
            var go = FindByName(c.target);
            if (go == null)
                return Fail(c, "GameObject not found: " + c.target, c.target, c.toward, null, "angle<=max");

            Vector3 desired;
            if (!string.IsNullOrEmpty(c.toward))
            {
                var other = FindByName(c.toward);
                if (other == null)
                    return Fail(c, "toward object not found: " + c.toward, c.target, c.toward, null, "angle<=max");
                desired = other.transform.position - go.transform.position;
            }
            else if (c.axis != null && !c.axis.IsZero())
            {
                desired = c.axis.ToVector3();
            }
            else
            {
                return Fail(c, "facing requires toward or non-zero axis", c.target, null, null, "toward|axis");
            }

            Vector3 forward = go.transform.forward;
            if (c.ignore_y)
            {
                desired.y = 0f;
                forward.y = 0f;
            }

            if (desired.sqrMagnitude < 1e-8f)
                return Fail(c, "desired facing direction is zero-length", c.target, c.toward, null, "angle<=max");
            if (forward.sqrMagnitude < 1e-8f)
                return Fail(c, "target forward is zero on XZ (ignore_y)", c.target, c.toward, null, "angle<=max");

            float angle = Vector3.Angle(forward.normalized, desired.normalized);
            float maxAng = c.max_angle_deg > 0f ? c.max_angle_deg : 30f;
            string meas = "angle_deg=" + angle;
            return angle <= maxAng
                ? Pass(c, "angle=" + angle + " deg <= " + maxAng, c.target, c.toward, meas, "angle<=" + maxAng)
                : Fail(c, "angle=" + angle + " deg > " + maxAng, c.target, c.toward, meas, "angle<=" + maxAng);
        }

        /// <summary>
        /// Keep-out AABB: listed objects (or a/b/target) must not have their world AABB
        /// intersecting the volume [min,max] expanded by padding.
        /// </summary>
        static CheckResult EvalClearanceVolume(ConstraintDef c)
        {
            if (c.min == null || c.max == null)
                return Fail(c, "clearance_volume requires min and max", null, null, null, "outside AABB");

            var names = new List<string>();
            if (c.objects != null)
                foreach (var n in c.objects)
                    if (!string.IsNullOrEmpty(n)) names.Add(n);
            if (!string.IsNullOrEmpty(c.target)) names.Add(c.target);
            if (!string.IsNullOrEmpty(c.a)) names.Add(c.a);
            if (!string.IsNullOrEmpty(c.b)) names.Add(c.b);
            // de-dupe while preserving order
            var dedup = new List<string>();
            var seen = new HashSet<string>();
            foreach (var n in names)
            {
                if (seen.Add(n)) dedup.Add(n);
            }
            names = dedup;
            if (names.Count == 0)
                return Fail(c, "clearance_volume needs objects[], target, a, or b", null, null, null, "outside AABB");

            float pad = c.padding;
            var vmin = c.min.ToVector3() - Vector3.one * pad;
            var vmax = c.max.ToVector3() + Vector3.one * pad;
            var violators = new List<string>();
            var details = new List<string>();

            foreach (var name in names)
            {
                var go = FindByName(name);
                if (go == null)
                {
                    violators.Add(name);
                    details.Add(name + "=MISSING");
                    continue;
                }
                Bounds b;
                if (!TryGetWorldBounds(go, out b))
                {
                    // fallback: point bounds at transform
                    b = new Bounds(go.transform.position, Vector3.one * 0.01f);
                }
                bool overlap = AabbOverlap(b.min, b.max, vmin, vmax);
                var tp = go.transform.position;
                bool pointIn = tp.x >= vmin.x && tp.x <= vmax.x
                               && tp.y >= vmin.y && tp.y <= vmax.y
                               && tp.z >= vmin.z && tp.z <= vmax.z;
                if (pointIn) overlap = true;
                details.Add(name + "|bmin=" + b.min + "|bmax=" + b.max + "|pos=" + tp + "|overlap=" + overlap);
                if (overlap) violators.Add(name);
            }

            string meas = string.Join(";", details);
            string expected = "outside keepout [" + vmin + " .. " + vmax + "]";
            if (violators.Count > 0)
                return Fail(c, "clearance violated by: " + string.Join(",", violators),
                    violators[0], names.Count > 1 ? names[1] : null, meas, expected);
            return Pass(c, "all objects clear of keep-out volume", names[0],
                names.Count > 1 ? names[1] : null, meas, expected);
        }

        static CheckResult EvalLockedTransform(ConstraintDef c)
        {
            var go = FindByName(c.target);
            if (go == null)
                return Fail(c, "GameObject not found: " + c.target, c.target, null, null, "locked pose");

            var t = go.transform;
            var parts = new List<string>();
            bool ok = true;

            if (c.check_position)
            {
                if (c.position == null)
                    return Fail(c, "locked_transform check_position needs position", c.target, null, null, "pos");
                float eps = c.pos_epsilon > 0f ? c.pos_epsilon : 0.05f;
                var want = c.position.ToVector3();
                float d = Vector3.Distance(t.position, want);
                parts.Add("pos_err=" + d);
                if (d > eps) ok = false;
            }

            if (c.check_rotation)
            {
                if (c.rotation_euler == null)
                    return Fail(c, "locked_transform check_rotation needs rotation_euler", c.target, null, null, "rot");
                float epsR = c.rot_epsilon_deg > 0f ? c.rot_epsilon_deg : 5f;
                var wantE = c.rotation_euler.ToVector3();
                float ang = Quaternion.Angle(t.rotation, Quaternion.Euler(wantE));
                parts.Add("rot_err_deg=" + ang);
                if (ang > epsR) ok = false;
            }

            if (!c.check_position && !c.check_rotation)
                return Fail(c, "locked_transform needs check_position and/or check_rotation", c.target, null, null, "flags");

            string meas = string.Join(";", parts) + ";pos=" + t.position + ";euler=" + t.eulerAngles;
            string expected = "pos_eps=" + c.pos_epsilon + ";rot_eps_deg=" + c.rot_epsilon_deg;
            return ok
                ? Pass(c, c.target + " locked OK " + meas, c.target, null, meas, expected)
                : Fail(c, c.target + " drifted " + meas, c.target, null, meas, expected);
        }

        static bool TryGetWorldBounds(GameObject go, out Bounds bounds)
        {
            var cols = go.GetComponentsInChildren<Collider>();
            if (cols != null && cols.Length > 0)
            {
                bounds = cols[0].bounds;
                for (int i = 1; i < cols.Length; i++)
                    bounds.Encapsulate(cols[i].bounds);
                return true;
            }
            var rends = go.GetComponentsInChildren<Renderer>();
            if (rends != null && rends.Length > 0)
            {
                bounds = rends[0].bounds;
                for (int i = 1; i < rends.Length; i++)
                    bounds.Encapsulate(rends[i].bounds);
                return true;
            }
            bounds = default;
            return false;
        }

        static bool AabbOverlap(Vector3 amin, Vector3 amax, Vector3 bmin, Vector3 bmax)
        {
            return amin.x <= bmax.x && amax.x >= bmin.x
                   && amin.y <= bmax.y && amax.y >= bmin.y
                   && amin.z <= bmax.z && amax.z >= bmin.z;
        }

        public static GameObject FindByName(string name)
        {
            if (string.IsNullOrEmpty(name))
                return null;
            var all = UnityEngine.Object.FindObjectsByType<GameObject>(FindObjectsInactive.Exclude, FindObjectsSortMode.None);
            foreach (var go in all)
            {
                if (go.name == name)
                    return go;
            }
            return GameObject.Find(name);
        }

        static CheckResult Pass(ConstraintDef c, string msg, string oa = null, string ob = null, string meas = null, string exp = null) => new CheckResult
        {
            id = c.id,
            type = c.type,
            passed = true,
            skipped = false,
            message = msg,
            object_a = oa,
            object_b = ob,
            measurement = meas,
            expected = exp
        };

        static CheckResult Fail(ConstraintDef c, string msg, string oa = null, string ob = null, string meas = null, string exp = null) => new CheckResult
        {
            id = c != null ? c.id : null,
            type = c != null ? c.type : null,
            passed = false,
            skipped = false,
            message = msg,
            object_a = oa,
            object_b = ob,
            measurement = meas,
            expected = exp
        };

        static void WriteReport(CheckReport report)
        {
            try
            {
                var path = Path.GetFullPath(Path.Combine(Application.dataPath, "..", LastReportRelativePath));
                Directory.CreateDirectory(Path.GetDirectoryName(path) ?? ".");
                File.WriteAllText(path, JsonUtility.ToJson(report, true), Encoding.UTF8);
            }
            catch (Exception e)
            {
                Debug.LogWarning("[Prompt2Scene-Check] Failed to write report: " + e.Message);
            }
        }

        static void LogReport(CheckReport report)
        {
            var sb = new StringBuilder();
            sb.Append("[Prompt2Scene-Check] set=").Append(report.set_id)
              .Append(" success=").Append(report.success)
              .Append(" passed=").Append(report.passed)
              .Append(" failed=").Append(report.failed)
              .Append(" skipped=").Append(report.skipped)
              .Append(" schema=").Append(report.schema_version);
            Debug.Log(sb.ToString());
            if (report.results == null) return;
            foreach (var r in report.results)
            {
                var line = "  [" + r.type + ":" + r.id + "] "
                           + (r.skipped ? "SKIP" : (r.passed ? "PASS" : "FAIL"))
                           + " — " + r.message
                           + (string.IsNullOrEmpty(r.measurement) ? "" : " meas=" + r.measurement);
                if (r.skipped) Debug.LogWarning(line);
                else if (r.passed) Debug.Log(line);
                else Debug.LogError(line);
            }
        }
    }
}
