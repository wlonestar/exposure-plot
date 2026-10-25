import json
from pathlib import Path
import tempfile
import unittest

from html_report import write_html
from photo_stats import aggregate


class HtmlReportTests(unittest.TestCase):
    def export(self, records):
        groups, _ = aggregate(records)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "report.html"
            write_html(path, groups, "/photos", removed=2, failed=1)
            return path.read_text(encoding="utf-8")

    def test_embedded_data_and_four_metrics(self):
        html = self.export([{"LensModel": "镜头", "ISO": 100}, {"LensModel": "镜头"}])
        payload = html.split('<script id="data" type="application/json">')[1].split('</script>')[0]
        data = json.loads(payload)
        self.assertEqual(len(data["metrics"]), 4)
        self.assertEqual(data["lenses"][0]["count"], 2)
        self.assertIn([None, 1], data["lenses"][0]["metrics"]["ISO"])
        self.assertEqual(data["removed"], 2)
        self.assertNotIn("__REPORT_DATA__", html)
        self.assertNotIn('<script src=', html)

    def test_exif_cannot_close_script(self):
        name = '</script><script>alert("EXIF")</script>'
        html = self.export([{"LensModel": name}])
        self.assertNotIn(name, html)
        payload = html.split('<script id="data" type="application/json">')[1].split('</script>')[0]
        self.assertEqual(json.loads(payload)["lenses"][0]["name"], name)

    def test_empty_report(self):
        html = self.export([])
        self.assertIn('"lenses": []', html)
        self.assertIn('没有可统计的照片', html)
