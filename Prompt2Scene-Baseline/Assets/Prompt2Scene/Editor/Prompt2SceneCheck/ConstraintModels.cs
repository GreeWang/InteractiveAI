using System;
using UnityEngine;

namespace Prompt2Scene.Check
{
    /// <summary>JsonUtility-friendly constraint set (schema v0.2).</summary>
    [Serializable]
    public class ConstraintSet
    {
        public string id;
        public string version;
        public string description;
        public string scene_hint;
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
        public float min_distance = -1f;
        public float max_distance = -1f;
        public float max_horizontal = 0.5f;
        public float min_vertical = 0.05f;
        public float max_vertical = 2f;
        public float max_angle_deg = 30f;
        public bool ignore_y = true;
    }

    [Serializable]
    public class Vec3
    {
        public float x;
        public float y;
        public float z;
        public Vector3 ToVector3() => new Vector3(x, y, z);
        public bool IsZero() => Mathf.Approximately(x, 0f) && Mathf.Approximately(y, 0f) && Mathf.Approximately(z, 0f);
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
    }

    [Serializable]
    public class CheckResult
    {
        public string id;
        public string type;
        public bool passed;
        public bool skipped;
        public string message;
    }
}
