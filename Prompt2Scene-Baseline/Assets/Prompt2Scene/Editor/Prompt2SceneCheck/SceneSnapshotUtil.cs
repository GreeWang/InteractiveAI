using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Prompt2Scene.Check
{
    /// <summary>
    /// Scene pose snapshot (JSON) and optional .unity copy helper for check runs.
    /// </summary>
    public static class SceneSnapshotUtil
    {
        public static string SnapshotPosesTo(string absoluteJsonPath)
        {
            var scene = SceneManager.GetActiveScene();
            var entries = new List<PoseEntry>();
            foreach (var go in scene.GetRootGameObjects())
                Collect(go.transform, entries);

            var snap = new ScenePoseSnapshot
            {
                scene = scene.path,
                saved_at = DateTimeOffset.Now.ToString("o"),
                poses = entries.ToArray()
            };
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(absoluteJsonPath) ?? ".");
                File.WriteAllText(absoluteJsonPath, JsonUtility.ToJson(snap, true), Encoding.UTF8);
                return "ok path=" + absoluteJsonPath + " count=" + entries.Count;
            }
            catch (Exception e)
            {
                return "fail:" + e.Message;
            }
        }

        static void Collect(Transform t, List<PoseEntry> entries)
        {
            var p = t.position;
            var e = t.eulerAngles;
            var s = t.localScale;
            entries.Add(new PoseEntry
            {
                name = t.name,
                px = p.x, py = p.y, pz = p.z,
                rx = e.x, ry = e.y, rz = e.z,
                sx = s.x, sy = s.y, sz = s.z
            });
            for (int i = 0; i < t.childCount; i++)
                Collect(t.GetChild(i), entries);
        }

        /// <summary>
        /// Save a copy of the active scene to absolutePath (must end with .unity).
        /// </summary>
        public static string SaveSceneCopy(string absoluteUnityPath)
        {
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(absoluteUnityPath) ?? ".");
                var scene = SceneManager.GetActiveScene();
                // Save into Assets temp then File.Copy is awkward; use SaveScene directly if under Assets.
                // For run dirs outside Assets, write pose JSON instead and also SaveScene to a under-Assets mirror if needed.
                if (absoluteUnityPath.Replace('\\', '/').Contains("/Assets/"))
                {
                    bool ok = EditorSceneManager.SaveScene(scene, absoluteUnityPath);
                    return ok ? ("saved:" + absoluteUnityPath) : "save_failed";
                }
                // Outside Assets: dump poses next to requested path
                var jsonPath = Path.ChangeExtension(absoluteUnityPath, ".poses.json");
                return SnapshotPosesTo(jsonPath);
            }
            catch (Exception e)
            {
                return "fail:" + e.Message;
            }
        }
    }
}
