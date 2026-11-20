import json
import subprocess
import sys
from types import SimpleNamespace

import numpy as np

from youtube_auto_clipper import pipeline


def test_missing_cascade_api_falls_back_without_stdout(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, 'cv2', SimpleNamespace(data=SimpleNamespace(haarcascades='/missing/')))
    assert pipeline._face_crop_points('source.mp4',0,3,1000,500)==[]
    captured=capsys.readouterr()
    assert captured.out=='' and 'centered crop' in captured.err


def test_largest_face_is_scaled_and_capture_released(monkeypatch):
    released=[]
    capture=SimpleNamespace(isOpened=lambda:True,set=lambda *_:None,
       read=lambda:(True,np.zeros((100,200,3),dtype=np.uint8)),release=lambda:released.append(True))
    detector=SimpleNamespace(empty=lambda:False,detectMultiScale=lambda *args,**kwargs:np.array([[1,2,3,4],[10,20,80,60]]))
    cv2=SimpleNamespace(CascadeClassifier=lambda _:detector,data=SimpleNamespace(haarcascades='/fixture/'),
       VideoCapture=lambda _:capture,cvtColor=lambda *args:np.zeros((100,200),dtype=np.uint8),
       CAP_PROP_POS_MSEC=0,COLOR_BGR2GRAY=0,error=RuntimeError)
    monkeypatch.setitem(sys.modules,'cv2',cv2)
    assert pipeline._face_crop_points('source.mp4',0,3,1000,500)==[(0.,250.,250.),(2.,250.,250.),(3,250.,250.)]
    assert released==[True]


def test_missing_classifier_data_releases_capture(monkeypatch):
    released=[]
    capture=SimpleNamespace(isOpened=lambda:True,release=lambda:released.append(True))
    cv2=SimpleNamespace(CascadeClassifier=lambda _:SimpleNamespace(empty=lambda:True),
         data=SimpleNamespace(haarcascades='/missing/'),VideoCapture=lambda _:capture,error=RuntimeError)
    monkeypatch.setitem(sys.modules,'cv2',cv2)
    assert pipeline._face_crop_points('source.mp4',0,3,1000,500)==[]
    assert released==[True]


def test_moving_face_crop_expression_renders(video,tmp_path,monkeypatch):
    # The capture unit test above verifies detector coordinates; this exercises
    # their real FFmpeg interpolation/render path without shipping a face image.
    monkeypatch.setattr(pipeline,'_face_crop_points',lambda *args:[(0.,1000.,640.),(.5,1200.,640.),(1.,900.,640.)])
    output=tmp_path/'tracked.mp4'
    pipeline.render_clip(video,0,1,output,face_tracking=True,resolution='720p',preset='tiktok')
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(output)]))
    stream=next(s for s in probe['streams'] if s['codec_type']=='video')
    assert (stream['width'],stream['height'])==(720,1280)


def test_supported_opencv_distribution_includes_working_cascade():
    import cv2
    assert hasattr(cv2,'CascadeClassifier')
    detector=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
    assert not detector.empty()


def test_detection_error_falls_back_and_releases_capture(monkeypatch,capsys):
    released=[]
    capture=SimpleNamespace(isOpened=lambda:True,set=lambda *_:None,
        read=lambda:(True,np.zeros((100,200,3),dtype=np.uint8)),release=lambda:released.append(True))
    def fail(*args,**kwargs):
        raise RuntimeError('detector failure')
    detector=SimpleNamespace(empty=lambda:False,detectMultiScale=fail)
    cv2=SimpleNamespace(CascadeClassifier=lambda _:detector,data=SimpleNamespace(haarcascades='/fixture/'),
        VideoCapture=lambda _:capture,cvtColor=lambda *args:np.zeros((100,200),dtype=np.uint8),
        CAP_PROP_POS_MSEC=0,COLOR_BGR2GRAY=0,error=RuntimeError)
    monkeypatch.setitem(sys.modules,'cv2',cv2)
    assert pipeline._face_crop_points('source.mp4',0,3,1000,500)==[]
    assert released==[True]
    captured=capsys.readouterr()
    assert captured.out=='' and 'centered crop' in captured.err
