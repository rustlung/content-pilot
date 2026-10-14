"""Verify that runtime web assets are included in the distributable wheel."""
from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = PROJECT_ROOT / "src" / "content_pilot" / "web"


def test_wheel_contains_all_runtime_web_assets(tmp_path: Path) -> None:
    wheel_dir = tmp_path / "wheel"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "--wheel-dir",
            str(wheel_dir),
            str(PROJECT_ROOT),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    wheel = next(wheel_dir.glob("content_pilot-*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())

    expected_assets = {
        "content_pilot/web/static/css/app.css",
        "content_pilot/web/static/js/app.js",
    }
    expected_templates = {
        f"content_pilot/web/templates/{template.name}"
        for template in WEB_ROOT.joinpath("templates").glob("*.html")
    }

    assert expected_assets <= names
    assert expected_templates <= names
