using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEngine;

namespace Prompt2Scene.Check
{
    /// <summary>
    /// Prompt2Scene-Check: load constraint JSON (schema v0.2) and report pass/fail.
    /// no_overlap uses Physics.ComputePenetration when both objects have Colliders.
    /// </summary>
    public static class ConstraintChecker
    {
        public const string DefaultSampleAssetPath =
            "Assets/Prompt2Scene/Check/Constraints/F03_sample.json";

        public const string LastReportRelativePath =
            "Logs/prompt2scene-check-last.json";

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
                checked_at = DateTimeOffset.Now.ToString("o")
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
                return Fail(c, "GameObject not found: " + c.target);
            return Pass(c, "Found " + c.target);
        }

        static CheckResult EvalLeftOf(ConstraintDef c)
        {
            var ga = FindByName(c.a);
            var gb = FindByName(c.b);
            if (ga == null || gb == null)
                return Fail(c, "Missing object(s) for left_of: a=" + c.a + " b=" + c.b);
            bool ok = ga.transform.position.x < gb.transform.position.x;
            return ok
                ? Pass(c, c.a + ".x=" + ga.transform.position.x + " < " + c.b + ".x=" + gb.transform.position.x)
                : Fail(c, c.a + " is not left of " + c.b);
        }

        static CheckResult EvalSameY(ConstraintDef c)
        {
            var ga = FindByName(c.a);
            var gb = FindByName(c.b);
            if (ga == null || gb == null)
                return Fail(c, "Missing object(s) for same_y");
            float eps = c.epsilon > 0f ? c.epsilon : 0.05f;
            float dy = Mathf.Abs(ga.transform.position.y - gb.transform.position.y);
            return dy <= eps
                ? Pass(c, "|dy|=" + dy + " <= " + eps)
                : Fail(c, "|dy|=" + dy + " > " + eps);
        }

        static CheckResult EvalBounds(ConstraintDef c)
        {
            var go = FindByName(c.target);
            if (go == null)
                return Fail(c, "GameObject not found: " + c.target);
            if (c.min == null || c.max == null)
                return Fail(c, "bounds requires min and max");
            var p = go.transform.position;
            var min = c.min.ToVector3();
            var max = c.max.ToVector3();
            bool inside = p.x >= min.x && p.x <= max.x
                          && p.y >= min.y && p.y <= max.y
                          && p.z >= min.z && p.z <= max.z;
            return inside
                ? Pass(c, c.target + " inside bounds @ " + p)
                : Fail(c, c.target + " outside bounds @ " + p);
        }

        static CheckResult EvalNoOverlap(ConstraintDef c)
        {
            var ga = FindByName(c.a);
            var gb = FindByName(c.b);
            if (ga == null || gb == null)
                return Fail(c, "Missing object(s) for no_overlap");

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
                return Fail(c, "Overlap depth=" + distance + " dir=" + dir);
            return Pass(c, "No penetration (ComputePenetration)");
        }

        static CheckResult EvalOnTopOf(ConstraintDef c)
        {
            var ga = FindByName(c.a);
            var gb = FindByName(c.b);
            if (ga == null || gb == null)
                return Fail(c, "Missing object(s) for on_top_of: a=" + c.a + " b=" + c.b);

            var pa = ga.transform.position;
            var pb = gb.transform.position;
            float dy = pa.y - pb.y;
            float horiz = Vector2.Distance(new Vector2(pa.x, pa.z), new Vector2(pb.x, pb.z));

            float maxH = c.max_horizontal > 0f ? c.max_horizontal : 0.5f;
            float minV = c.min_vertical;
            float maxV = c.max_vertical > 0f ? c.max_vertical : 2f;

            if (dy < minV)
                return Fail(c, "not above enough: dy=" + dy + " < min_vertical=" + minV);
            if (dy > maxV)
                return Fail(c, "too high: dy=" + dy + " > max_vertical=" + maxV);
            if (horiz > maxH)
                return Fail(c, "XZ offset=" + horiz + " > max_horizontal=" + maxH);
            return Pass(c, c.a + " on " + c.b + " dy=" + dy + " horiz=" + horiz);
        }

        static CheckResult EvalDistance(ConstraintDef c)
        {
            var ga = FindByName(c.a);
            var gb = FindByName(c.b);
            if (ga == null || gb == null)
                return Fail(c, "Missing object(s) for distance");

            float d = Vector3.Distance(ga.transform.position, gb.transform.position);
            bool hasMin = c.min_distance >= 0f;
            bool hasMax = c.max_distance >= 0f;
            if (!hasMin && !hasMax)
                return Fail(c, "distance requires min_distance and/or max_distance (>=0)");

            if (hasMin && d < c.min_distance)
                return Fail(c, "dist=" + d + " < min_distance=" + c.min_distance);
            if (hasMax && d > c.max_distance)
                return Fail(c, "dist=" + d + " > max_distance=" + c.max_distance);
            return Pass(c, "dist=" + d + " in [" + (hasMin ? c.min_distance.ToString() : "-inf")
                           + ", " + (hasMax ? c.max_distance.ToString() : "+inf") + "]");
        }

        static CheckResult EvalFacing(ConstraintDef c)
        {
            var go = FindByName(c.target);
            if (go == null)
                return Fail(c, "GameObject not found: " + c.target);

            Vector3 desired;
            if (!string.IsNullOrEmpty(c.toward))
            {
                var other = FindByName(c.toward);
                if (other == null)
                    return Fail(c, "toward object not found: " + c.toward);
                desired = other.transform.position - go.transform.position;
            }
            else if (c.axis != null && !c.axis.IsZero())
            {
                desired = c.axis.ToVector3();
            }
            else
            {
                return Fail(c, "facing requires toward or non-zero axis");
            }

            Vector3 forward = go.transform.forward;
            if (c.ignore_y)
            {
                desired.y = 0f;
                forward.y = 0f;
            }

            if (desired.sqrMagnitude < 1e-8f)
                return Fail(c, "desired facing direction is zero-length");
            if (forward.sqrMagnitude < 1e-8f)
                return Fail(c, "target forward is zero on XZ (ignore_y)");

            float angle = Vector3.Angle(forward.normalized, desired.normalized);
            float maxAng = c.max_angle_deg > 0f ? c.max_angle_deg : 30f;
            return angle <= maxAng
                ? Pass(c, "angle=" + angle + " deg <= " + maxAng)
                : Fail(c, "angle=" + angle + " deg > " + maxAng);
        }

        static GameObject FindByName(string name)
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

        static CheckResult Pass(ConstraintDef c, string msg) => new CheckResult
        {
            id = c.id,
            type = c.type,
            passed = true,
            skipped = false,
            message = msg
        };

        static CheckResult Fail(ConstraintDef c, string msg) => new CheckResult
        {
            id = c != null ? c.id : null,
            type = c != null ? c.type : null,
            passed = false,
            skipped = false,
            message = msg
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
              .Append(" skipped=").Append(report.skipped);
            Debug.Log(sb.ToString());
            if (report.results == null) return;
            foreach (var r in report.results)
            {
                var line = "  [" + r.type + ":" + r.id + "] "
                           + (r.skipped ? "SKIP" : (r.passed ? "PASS" : "FAIL"))
                           + " — " + r.message;
                if (r.skipped) Debug.LogWarning(line);
                else if (r.passed) Debug.Log(line);
                else Debug.LogError(line);
            }
        }
    }
}
