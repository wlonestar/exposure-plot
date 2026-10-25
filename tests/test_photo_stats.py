import csv
import io
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import photo_stats as stats


class StatisticsTests(unittest.TestCase):
    def test_grouping_and_missing_fields(self):
        groups, failed = stats.aggregate([
            {"LensModel": "Zoom", "FocalLengthIn35mmFormat": 35, "ISO": 100, "FNumber": 2.8, "ExposureTime": "1/125"},
            {"LensModel": "Zoom", "FocalLengthIn35mmFormat": "35", "ISO": 200},
            {"Lens": "Prime", "FocalLengthIn35mmFormat": 50},
            {},
            {"Error": "corrupt file"},
        ])
        self.assertEqual(failed, 1)
        self.assertEqual(groups["Zoom"]["count"], 2)
        self.assertEqual(groups["Zoom"]["metrics"]["FocalLengthIn35mmFormat"][35], 2)
        self.assertEqual(groups["Zoom"]["metrics"]["FNumber"][None], 1)
        self.assertEqual(groups["未知镜头"]["count"], 1)

    def test_raw_jpeg_pair_prefers_raw_and_fills_missing(self):
        records, removed = stats.deduplicate([
            {"SourceFile": "/photos/DSC001.JPG", "LensModel": "JPEG lens", "ISO": 100, "FNumber": 4},
            {"SourceFile": "/photos/dsc001.ARW", "LensID": "RAW lens", "ISO": 200, "FNumber": 0},
        ])
        self.assertEqual(removed, 1)
        self.assertEqual(len(records), 1)
        self.assertEqual(stats.lens_name(records[0]), "RAW lens")
        self.assertEqual(records[0]["ISO"], 200)
        self.assertEqual(records[0]["FNumber"], 4)
        groups, failed = stats.aggregate(records)
        self.assertEqual(groups["RAW lens"]["count"], 1)
        self.assertEqual(failed, 0)

    def test_pair_scope_and_standalone_files(self):
        records, removed = stats.deduplicate([
            {"SourceFile": "/a/one.jpg"},
            {"SourceFile": "/b/one.arw"},
            {"SourceFile": "/a/two.jpg"},
            {"SourceFile": "/a/two.jpeg"},
            {"SourceFile": "/a/three.tif"},
            {"SourceFile": "/a/three.nef"},
            {},
        ])
        self.assertEqual(len(records), 7)
        self.assertEqual(removed, 0)

    def test_pair_read_failure_falls_back(self):
        records, removed = stats.deduplicate([
            {"SourceFile": "/a/one.cr3", "Error": "bad RAW"},
            {"SourceFile": "/a/one.jpg", "ISO": 100},
        ])
        self.assertEqual(removed, 1)
        self.assertEqual(records[0]["ISO"], 100)
        self.assertNotIn("Error", records[0])
        records, _ = stats.deduplicate([
            {"SourceFile": "/a/one.cr3", "Error": "bad RAW"},
            {"SourceFile": "/a/one.jpg", "Error": "bad JPEG"},
        ])
        self.assertEqual(stats.aggregate(records), ({}, 1))

    def test_equivalent_focal_length_not_actual(self):
        groups, _ = stats.aggregate([
            {"FocalLength": 23, "FocalLengthIn35mmFormat": 34},
            {"FocalLength": 23},
        ])
        counts = groups["未知镜头"]["metrics"]["FocalLengthIn35mmFormat"]
        self.assertEqual(counts, {34: 1, None: 1})
        records, _ = stats.deduplicate([
            {"SourceFile": "/a/one.nef", "FocalLength": 23},
            {"SourceFile": "/a/one.jpg", "FocalLengthIn35mmFormat": 34},
        ])
        self.assertEqual(records[0]["FocalLengthIn35mmFormat"], 34)

    def test_invalid_values(self):
        for value in (None, "", "unknown", 0, -1, "nan", "inf", "1/0", True, [100]):
            with self.subTest(value=value):
                self.assertIsNone(stats.positive_number(value))
        self.assertEqual(stats.positive_number("1/250"), .004)

    def test_lens_precedence(self):
        self.assertEqual(stats.lens_name({"LensModel": "Model", "LensID": "ID"}), "Model")
        self.assertEqual(stats.lens_name({"LensModel": "", "LensID": "ID"}), "ID")
        self.assertEqual(stats.lens_name({}), "未知镜头")

    def test_labels(self):
        self.assertEqual(stats.format_value("ExposureTime", .008), "1/125 s")
        self.assertEqual(stats.format_value("ExposureTime", 2), "2 s")
        self.assertEqual(stats.format_value("FNumber", 2.8), "f/2.8")
        self.assertEqual(stats.format_value("FocalLengthIn35mmFormat", None), "未知")
        self.assertEqual(stats.format_value("FocalLengthIn35mmFormat", 34), "34 mm")

    def test_csv_and_report(self):
        groups, _ = stats.aggregate([{"LensModel": "镜头 A", "ISO": 100}, {"LensModel": "镜头 A"}])
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "stats.csv"
            stats.write_csv(output, groups)
            with output.open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream))
            iso = [row for row in rows if row["参数"] == "ISO"]
            self.assertEqual(len(iso), 2)
            self.assertEqual(float(iso[0]["组内占比"]), .5)
            self.assertEqual(iso[1]["显示值"], "未知")
        with redirect_stdout(io.StringIO()) as stream:
            stats.print_report(groups)
        self.assertIn("50.0%", stream.getvalue())

    def test_empty_report(self):
        with redirect_stdout(io.StringIO()) as stream:
            stats.print_report({})
        self.assertIn("0 张照片", stream.getvalue())

    @patch("photo_stats.shutil.which", return_value="/usr/bin/exiftool")
    @patch("photo_stats.subprocess.run")
    def test_exiftool_command(self, run, which):
        run.return_value = subprocess.CompletedProcess([], 0, '[{"ISO":100}]', "")
        self.assertEqual(stats.read_metadata(Path("/photos"), False), [{"ISO": 100}])
        command = run.call_args.args[0]
        self.assertNotIn("-r", command)
        self.assertIn("-ExposureTime#", command)
        self.assertIn("-FocalLengthIn35mmFormat#", command)
        self.assertEqual(command[-1], "/photos")
        stats.read_metadata(Path("/photos"))
        self.assertIn("-r", run.call_args.args[0])

    @patch("photo_stats.shutil.which", return_value=None)
    def test_missing_exiftool(self, which):
        with self.assertRaisesRegex(RuntimeError, "未找到 ExifTool"):
            stats.read_metadata(Path("/photos"))

    @patch("photo_stats.shutil.which", return_value="exiftool")
    @patch("photo_stats.subprocess.run")
    def test_invalid_exiftool_output(self, run, which):
        run.return_value = subprocess.CompletedProcess([], 1, "not json", "")
        with self.assertRaisesRegex(RuntimeError, "有效 JSON"):
            stats.read_metadata(Path("/photos"))


if __name__ == "__main__":
    unittest.main()
