from youtube_auto_clipper.editorial import concepts, detect_content, speech_units
from youtube_auto_clipper.discovery import rank_candidates, align_ai_candidate


def test_goal_matches_across_english_and_indonesian():
    segments = [{"start":0,"end":22,"text":"Reaksi lucu! Aku kaget lalu ketawa melihat kesalahan itu."}]
    clip = rank_candidates(segments,1,20,30,'auto','funny reaction')[0]
    assert clip['goal_matches'] == ['humor','reaction']
    assert clip['scores']['goal_relevance'] == 100
    assert concepts('funny reaction') == concepts('reaksi lucu')


def test_swearing_and_chat_do_not_imply_gameplay():
    assert detect_content('Anjir, chat kalian lucu, jangan spoiler!')[0] == 'conversation'
    assert detect_content('Menang! Headshot musuh terakhir, clutch!')[0] == 'gaming'
    assert detect_content('Langkah mengatasi error, ini caranya.')[0] == 'instruction'


def test_fragment_merging_and_question_answer_boundaries():
    segments = [{'start':0,'end':10,'text':'Why did this error happen?'},
                {'start':10,'end':18,'text':'Because the file'},
                {'start':18,'end':25,'text':'was missing. The fix is to restore it.'}]
    units = speech_units(segments)
    assert len(units) == 2
    assert units[1]['start'] == 10 and units[1]['end'] == 25
    clip = rank_candidates(segments,1,20,30,'instruction','fix error')[0]
    assert (clip['start'],clip['end']) == (0,25)
    assert clip['boundary']['start_clean'] and clip['boundary']['end_clean']


def test_repetition_and_call_to_action_do_not_dominate():
    segments = [{'start':0,'end':22,'text':'Like like like subscribe subscribe follow like like.'},
                {'start':24,'end':46,'text':'Here is a useful tip. Restore the missing file to fix the error.'}]
    clip = rank_candidates(segments,1,20,25,'instruction','useful tip')[0]
    assert clip['start'] == 24


def test_long_unpunctuated_speech_still_has_flagged_fallback():
    segments = [{'start':i,'end':i+10,'text':'continuing speech without punctuation'} for i in range(0,90,10)]
    clips = rank_candidates(segments,2,20,30,'auto')
    assert clips and all(c['end']-c['start'] <= 30 for c in clips)
    assert all(c['warnings'] for c in clips)


def test_auto_classifies_each_window_and_reports_requested_mismatch():
    segments = [{'start':0,'end':22,'text':'Chat, ayo ngobrol tentang cerita lucu.'},
                {'start':30,'end':52,'text':'Headshot musuh terakhir! Kita menang.'}]
    clips = rank_candidates(segments,2,20,25,'auto')
    assert {c['content_mode'] for c in clips} == {'conversation','gaming'}
    chat = rank_candidates(segments[:1],1,20,25,'gaming')[0]
    assert any('Requested gaming' in warning for warning in chat['warnings'])


def test_ai_ranges_align_and_do_not_return_overlong_or_unrelated_windows():
    segments = [{'start':0,'end':10,'text':'Here is the problem?'},
                {'start':10,'end':25,'text':'This is the solution.'},
                {'start':40,'end':65,'text':'An unrelated story.'}]
    aligned = align_ai_candidate(segments,{'start':2,'end':24,'reason':'test'},20,30,'auto','solution')
    assert (aligned['start'],aligned['end']) == (0,25)
    assert align_ai_candidate(segments,{'start':100,'end':125,'reason':'test'},20,30,'auto','') is None


def test_generic_success_and_workplace_boss_are_not_gameplay():
    assert detect_content('I successfully fixed this error with these tutorial steps.')[0] == 'instruction'
    assert detect_content('My boss told a funny story about our office.')[0] == 'conversation'


def test_ai_selection_deduplicates_snapped_windows_and_falls_back_on_invalid():
    from youtube_auto_clipper.discovery import select_editorial_highlights
    segments = [{'start':0,'end':10,'text':'What is the problem?'},
                {'start':10,'end':25,'text':'Here is the solution.'}]
    proposals = [{'start':1,'end':24,'reason':'first'}, {'start':2,'end':23,'reason':'duplicate'}]
    clips, method, _ = select_editorial_highlights(segments,3,20,30,'instruction','solution',True,
                                                  ai_selector=lambda *_:(proposals,'gemini'))
    assert method == 'gemini' and len(clips) == 1
    clips, method, warnings = select_editorial_highlights(segments,3,20,30,'instruction','solution',True,
                                                         ai_selector=lambda *_:([{'bad':'response'}],'gemini'))
    assert clips and method == 'offline-fallback' and warnings


def test_direct_pipeline_uses_bilingual_goal_and_category(tmp_path, monkeypatch):
    from youtube_auto_clipper import pipeline
    video = tmp_path/'video.mp4'
    video.write_bytes(b'fixture')
    segments = [{'start':0,'end':22,'text':'Subscribe like like follow subscribe.'},
                {'start':25,'end':47,'text':'Reaksi lucu! Aku kaget lalu ketawa melihat kesalahan itu.'}]
    monkeypatch.setattr(pipeline,'require_binary',lambda *_:None)
    monkeypatch.setattr(pipeline,'transcribe',lambda *_:(segments,'id'))
    monkeypatch.setattr(pipeline,'render_clip',lambda *args,**kwargs:None)
    result = pipeline.process(str(video),str(tmp_path/'out'),count=1,min_duration=20,max_duration=25,
                              use_ai=False,mode='auto',goal='funny reaction')
    assert result['clips'][0]['start'] == 25
    assert result['clips'][0]['scores']['goal_relevance'] == 100


def test_ai_scores_and_ranges_are_finite_and_bounded(monkeypatch):
    import json,sys,types
    from youtube_auto_clipper.pipeline import ai_highlights
    monkeypatch.setenv('GEMINI_API_KEY','test-placeholder')
    payload={'clips':[{'start':0,'end':25,'score':200},
                      {'start':30,'end':55,'score':float('nan')},
                      {'start':60,'end':85,'score':float('inf')},
                      {'start':90,'end':115,'score':90}]}
    client=types.SimpleNamespace(models=types.SimpleNamespace(generate_content=lambda **_:types.SimpleNamespace(text=json.dumps(payload))))
    google=types.ModuleType('google')
    google.genai=types.SimpleNamespace(Client=lambda **_:client)
    monkeypatch.setitem(sys.modules,'google',google)
    clips,method=ai_highlights([{'start':0,'end':100,'text':'fixture'}],5,20,30)
    assert method == 'gemini' and len(clips)==1
    assert clips[0]['score']==100
