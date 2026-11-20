import shutil
import subprocess

import pytest


@pytest.fixture
def video(tmp_path):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg and ffprobe required")
    target = tmp_path / "synthetic.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
                    "-i", "testsrc2=size=320x180:rate=10", "-f", "lavfi", "-i",
                    "sine=frequency=440:sample_rate=16000", "-t", "3", "-c:v", "libx264",
                    "-c:a", "aac", "-y", str(target)], check=True)
    return target
