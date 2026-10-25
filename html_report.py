"""Self-contained, offline HTML report, no third-party Python or JS packages."""

import json
from pathlib import Path


def write_html(path, groups, directory, removed=0, failed=0):
    metrics = [
        ("FocalLengthIn35mmFormat", "等效焦距", "35mm 等效 · mm"),
        ("ISO", "ISO", "感光度"),
        ("FNumber", "光圈", "f 值"),
        ("ExposureTime", "快门速度", "曝光时间 · 秒"),
    ]
    data = {
        "directory": str(directory), "removed": removed, "failed": failed,
        "metrics": metrics,
        "lenses": [
            {"name": name, "count": group["count"], "metrics": {
                tag: [[value, count] for value, count in group["metrics"][tag].items()]
                for tag, _, _ in metrics
            }}
            for name, group in sorted(groups.items())
        ],
    }
    # Escape HTML parser delimiters, including in untrusted EXIF lens names.
    payload = json.dumps(data, ensure_ascii=False, allow_nan=False)
    payload = payload.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    template = Path(__file__).with_name("report_template.html").read_text(encoding="utf-8")
    path.write_text(template.replace("__REPORT_DATA__", payload), encoding="utf-8")
