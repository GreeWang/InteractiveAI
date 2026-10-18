using System.IO;
using UnityEditor;
using UnityEngine;

namespace Prompt2Scene.Check
{
    public static class ConstraintCheckerMenu
    {
        const string SampleMenu = "Prompt2Scene/Check/Run Sample F03 Constraints";
        const string FileMenu = "Prompt2Scene/Check/Run Constraints From File...";

        [MenuItem(SampleMenu)]
        public static void RunSample()
        {
            var report = ConstraintChecker.RunDefaultSample();
            EditorUtility.DisplayDialog(
                "Prompt2Scene-Check",
                FormatSummary(report),
                "OK");
        }

        [MenuItem(FileMenu)]
        public static void RunFromFile()
        {
            var start = Path.Combine(Application.dataPath, "Prompt2Scene/Check/Constraints");
            var path = EditorUtility.OpenFilePanel("Prompt2Scene constraint JSON", start, "json");
            if (string.IsNullOrEmpty(path))
                return;
            var report = ConstraintChecker.RunFromPath(path);
            EditorUtility.DisplayDialog(
                "Prompt2Scene-Check",
                FormatSummary(report),
                "OK");
        }

        static string FormatSummary(CheckReport report)
        {
            if (report == null)
                return "No report.";
            return "set=" + report.set_id
                   + "\nsuccess=" + report.success
                   + "\npassed=" + report.passed
                   + " failed=" + report.failed
                   + " skipped=" + report.skipped
                   + "\nreport: " + ConstraintChecker.LastReportRelativePath;
        }
    }
}
