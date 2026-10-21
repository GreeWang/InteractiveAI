using System;
using UnityEngine;

namespace Prompt2Scene.Check
{
    /// <summary>JsonUtility-friendly constraint set (schema v0.3).</summary>
    [Serializable]
    public class ConstraintSet
    {
        public string id;
        public string version;
        public string description;
        public string scene_hint;
        public string[] locked;
        public ConstraintDef[] constraints;
    }

    [Serializable]
    public class ConstraintDef
    {
        public string id;
        public string type;
        public string target;
        public string a;
        public string b;
        public string toward;
        public float epsilon = 0.05f;
        public Vec3 min;
        public Vec3 max;
        public Vec3 axis;
        public Vec3 position;
        public Vec3 rotation_euler;
        public float min_distance = -1f;
        public float max_distance = -1f;
        public float max_horizontal = 0.5f;
        public float min_vertical = 0.05f;
        public float max_vertical = 2f;
        public float max_angle_deg = 30f;
        public bool ignore_y = true;
        public float pos_epsilon = 0.05f;
        public float rot_epsilon_deg = 5f;
        public bool check_position = true;
        public bool check_rotation = false;
        public string[] objects;
        public float padding = 0f;
    }

    [Serializable]
    public class Vec3
    {
        public float x;
        public float y;
        public float z;
        public Vector3 ToVector3() => new Vector3(x, y, z);
        public bool IsZero() => Mathf.Approximately(x, 0f) && Mathf.Approximately(y, 0f) && Mathf.Approximately(z, 0f);
        public static Vec3 From(Vector3 v) => new Vec3 { x = v.x, y = v.y, z = v.z };
    }

    [Serializable]
    public class CheckReport
    {
        public string set_id;
        public string source_path;
        public bool success;
        public int passed;
        public int failed;
        public int skipped;
        public CheckResult[] results;
        public string checked_at;
        public string schema_version;
    }

    [Serializable]
    public class CheckResult
    {
        public string id;
        public string type;
        public bool passed;
        public bool skipped;
        public string message;
        // Machine-readable enrichment (v0.3)
        public string object_a;
        public string object_b;
        public string measurement;
        public string expected;
    }

    [Serializable]
    public class RepairReport
    {
        public string set_id;
        public bool attempted;
        public bool success_after;
        public int rounds;
        public string[] actions;
        public string message;
        public string repaired_at;
    }

    [Serializable]
    public class ScenePoseSnapshot
    {
        public string scene;
        public string saved_at;
        public PoseEntry[] poses;
    }

    [Serializable]
    public class PoseEntry
    {
        public string name;
        public float px, py, pz;
        public float rx, ry, rz;
        public float sx, sy, sz;
    }
}
