import json
import subprocess

import pytest

from youtube_auto_clipper.export import export_target
from youtube_auto_clipper.pipeline import render_clip


@pytest.mark.parametrize('preset', ['tiktok', 'reels', 'shorts'])
def test_auto_platform_target(preset):
    settings = export_target('fit', 'auto', preset)
    assert (settings['width'], settings['height']) == (1080, 1920)
    assert settings['resolution'] == '1080p'
    assert settings['requested_resolution'] == 'auto'
    assert settings['aspect_ratio'] == '9:16'
    with pytest.raises(ValueError, match='require portrait or fit'):
        export_target('landscape', 'auto', preset)


@pytest.mark.parametrize('options', [('bad', '1080p', None), ('portrait', '4k', None), ('fit', '720p', 'unknown')])
def test_invalid_export_settings(options):
    with pytest.raises(ValueError):
        export_target(*options)


@pytest.mark.parametrize('preset,resolution,layout,dimensions', [
    ('tiktok', 'auto', 'portrait', (1080,1920)),
    ('reels', '720p', 'portrait', (720,1280)),
    ('shorts', '720p', 'fit', (720,1280)),
    (None, '720p', 'landscape', (1280,720)),
])
def test_real_export_dimensions_and_pixel_format(video,tmp_path,preset,resolution,layout,dimensions):
    output=tmp_path/'export.mp4'
    render_clip(video,0,.5,output,face_tracking=False,layout=layout,resolution=resolution,preset=preset)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(output)]))
    stream=next(s for s in probe['streams'] if s['codec_type']=='video')
    assert (stream['width'],stream['height']) == dimensions
    assert stream['pix_fmt'] == 'yuv420p'
    assert stream['codec_name'] == 'h264'


def test_cli_passes_platform_and_quality(monkeypatch,capsys):
    from youtube_auto_clipper import cli
    calls=[]
    monkeypatch.setattr(cli,'process',lambda *args: calls.append(args) or {})
    monkeypatch.setattr('sys.argv',['kairos','video.mp4','--preset','tiktok','--resolution','720p','--layout','fit'])
    cli.main()
    assert calls[0][-3:] == ('fit','720p','tiktok')
    assert json.loads(capsys.readouterr().out) == {}
