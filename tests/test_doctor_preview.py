import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from youtube_auto_clipper import doctor, pipeline


def test_media_probe_detects_missing_libass(monkeypatch):
    monkeypatch.setattr(doctor.shutil,'which',lambda name:'/fake/'+name)
    def run(args,**kwargs):
        text=' V..... libx264 Encoder\n A..... aac Encoder' if '-encoders' in args else ' ... scale V->V' if '-filters' in args else 'version'
        return SimpleNamespace(returncode=0,stdout=text)
    monkeypatch.setattr(doctor,'run_capture',run)
    checks={c['name']:c for c in doctor.probe_media_tools()}
    assert checks['ffmpeg']['status']=='ok'
    assert checks['libass']['status']=='error'
    assert checks['libx264']['status']=='ok'
    with pytest.raises(RuntimeError,match='kairos doctor'):
        doctor.require_render_support()


def test_doctor_missing_model_warns_without_exposing_key(monkeypatch,tmp_path):
    monkeypatch.setattr(doctor,'probe_media_tools',lambda:[doctor.check('ffmpeg',True,'ready')])
    cv=SimpleNamespace(CascadeClassifier=lambda _:SimpleNamespace(empty=lambda:False),data=SimpleNamespace(haarcascades='/fixture/'))
    monkeypatch.setattr(doctor.importlib,'import_module',lambda name:cv if name=='cv2' else SimpleNamespace())
    monkeypatch.setattr(doctor,'local_model_ready',lambda model:False)
    monkeypatch.setenv('GEMINI_API_KEY','private-example-key-must-not-be-printed')
    report=doctor.diagnose(output_dir=str(tmp_path))
    assert report['ready'] and not report['offline_ready']
    assert report['network_used'] is False and report['status']=='warning'
    assert 'private-example' not in json.dumps(report)


def test_doctor_cli_json_exit_status(monkeypatch,capsys):
    monkeypatch.setattr(doctor,'diagnose',lambda *_:{'ready':False,'checks':[],'status':'blocked'})
    with pytest.raises(SystemExit) as exc:
        doctor.doctor_cli(['--json'])
    assert exc.value.code==1
    assert json.loads(capsys.readouterr().out)['status']=='blocked'


def test_cli_dispatches_doctor_without_source(monkeypatch):
    from youtube_auto_clipper import cli
    captured=[]
    monkeypatch.setattr(doctor,'doctor_cli',lambda args:captured.append(args))
    monkeypatch.setattr('sys.argv',['kairos','doctor','--json'])
    cli.main()
    assert captured==[['--json']]


def test_render_preflight_fails_before_transcription(tmp_path,monkeypatch):
    called=[]
    monkeypatch.setattr(pipeline,'transcribe',lambda *_:called.append(True))
    def fail():
        raise RuntimeError('Render prerequisites failed: missing ass')
    monkeypatch.setattr(pipeline,'require_render_support',fail)
    with pytest.raises(RuntimeError,match='prerequisites'):
        pipeline.process(str(tmp_path/'video.mp4'),str(tmp_path/'output'))
    assert not called


@pytest.mark.parametrize('length',[0,11,float('nan'),True])
def test_preview_length_validation(tmp_path,monkeypatch,length):
    monkeypatch.setattr(pipeline,'require_render_support',lambda:None)
    with pytest.raises(ValueError,match='Preview length'):
        pipeline.process('video.mp4',str(tmp_path),candidate_plan='plan.json',candidate_ids=['one'],preview_seconds=length)


def test_real_rendered_preview_preserves_plan_and_settings(video,tmp_path,monkeypatch):
    from youtube_auto_clipper.discovery import fingerprint
    import subprocess
    if ' ass ' not in subprocess.run(['ffmpeg','-hide_banner','-filters'],capture_output=True,text=True).stdout:pytest.skip('FFmpeg libass required')
    plan=tmp_path/'plan.json'
    plan.write_text(json.dumps({'schema_version':1,'source_sha256':fingerprint(video),
                               'clips':[{'id':'chosen','start':.25,'end':2.75}]}))
    original=plan.read_bytes()
    monkeypatch.setattr(pipeline,'transcribe',lambda *_:([{'start':0,'end':3,'text':'Preview caption.'}],'en'))
    result=pipeline.preview_clip(str(video),str(plan),'chosen',str(tmp_path/'out'),seconds=1,
                                 layout='fit',resolution='720p',preset='reels')
    assert result['is_preview'] and result['clips'][0]['end']==1.25
    assert result['clips'][0]['candidate_end']==2.75
    assert plan.read_bytes()==original
    output=Path(result['clips'][0]['video'])
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(output)]))
    stream=next(s for s in probe['streams'] if s['codec_type']=='video')
    assert (stream['width'],stream['height'])==(720,1280)
    assert abs(float(probe['format']['duration'])-1)<.15
    assert 'Preview caption' in Path(result['clips'][0]['subtitles']).read_text()


def test_srt_trims_partial_segment_using_word_timestamps(tmp_path):
    target=tmp_path/'trimmed.srt'
    segments=[{'start':0,'end':3,'text':'one two three','words':[
        {'start':0,'end':.9,'text':'one'}, {'start':1,'end':1.9,'text':'two'},
        {'start':2,'end':2.9,'text':'three'}]}]
    pipeline.make_srt(segments,1,2,target)
    text=target.read_text()
    assert 'two' in text and 'one' not in text and 'three' not in text
    assert '00:00:00,000 --> 00:00:00,900' in text
