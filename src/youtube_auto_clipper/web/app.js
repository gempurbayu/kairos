'use strict';
const token = new URLSearchParams(location.search).get('token');
const url = route => `${route}?token=${encodeURIComponent(token)}`;
const $ = id => document.getElementById(id);
let plan, active, currentJob, rangeEnd, timer, setupReady=false, submitting=false;
function buttons(){ $("render").disabled=!setupReady||Boolean(currentJob)||submitting; $("render-preview").disabled=!setupReady||Boolean(currentJob)||submitting; }
async function api(route, body) {
  const response = await fetch(url(route), body === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Request failed');
  return data;
}
function node(tag, text, className) { const element=document.createElement(tag); if(text !== undefined) element.textContent=text; if(className) element.className=className; return element; }
function error(message) { $('status').textContent=message; $('status').className='error'; }
function selected() {
  return [...document.querySelectorAll('.card')].filter(card => card.querySelector('input[type=checkbox]').checked).map(card => ({id:card.dataset.id,start:Number(card.querySelector('[data-time=start]').value),end:Number(card.querySelector('[data-time=end]').value)}));
}
function preview(card) {
  const start=Number(card.querySelector('[data-time=start]').value),end=Number(card.querySelector('[data-time=end]').value);
  if(!Number.isFinite(start)||!Number.isFinite(end)||start<0||end<=start||end>plan.duration) return error('Choose valid start/end times inside the source video.');
  document.querySelectorAll('.card').forEach(c=>c.classList.remove('active'));
  card.classList.add('active'); active=card; showSource(); rangeEnd=end; $('video').currentTime=start;
  $('now').textContent=`${card.dataset.id} · ${start.toFixed(1)}–${end.toFixed(1)}s`;
  $('video').play().catch(()=>error('The browser could not play this source codec. Use a browser-compatible MP4.'));
}
function finish() { currentJob=null; clearTimeout(timer); buttons(); $('cancel').hidden=true; }
async function poll() {
  try {
    const job=await api(`/jobs/${currentJob}`);
    $('status').className=''; $('status').textContent=`${job.status} · ${job.stage}`;
    $('progress').value=job.progress;
    if(job.status==='completed') {
      const result=job.result; $('results').replaceChildren();
      if(result.is_preview && result.clips.length){
        document.querySelector('.player').classList.add('rendered');
        document.querySelector('.player').classList.toggle('rendered-wide',result.export?.aspect_ratio==='16:9');
        rangeEnd=undefined; $('video').pause(); $('video').src=url(`/artifact/${job.id}/0/video`);
        $('video').load(); $('source-view').hidden=false;
        $('player-mode').textContent='Rendered preview: actual crop, layout, resolution, and burned captions. Preview duration only.';
        $('now').textContent='Rendered preview · current job settings';
      }
      result.clips.forEach((clip,index)=>{
        const link=node('a',`Open rendered clip ${index+1}`); link.href=url(`/artifact/${job.id}/${index}/video`); link.target='_blank'; link.rel='noopener'; $('results').append(link);
        const sub=node('a',`Download subtitles ${index+1}`); sub.href=url(`/artifact/${job.id}/${index}/subtitles`); sub.download=`clip_${index+1}.srt`; $('results').append(sub);
      }); finish();
    } else if(['failed','cancelled'].includes(job.status)) { if(job.error) error(job.error); finish(); }
    else timer=setTimeout(poll,1000);
  } catch(e) { error(e.message); finish(); }
}
function showSource(){
  document.querySelector('.player').classList.remove('rendered','rendered-wide');
  if(!$('source-view').hidden){ $('video').pause(); $('video').src=url('/media'); $('video').load(); }
  $('source-view').hidden=true; rangeEnd=undefined;
  $('player-mode').textContent='Source preview shows the original video. Use Render preview to inspect the actual export.';
}
$('source-view').onclick=()=>{showSource();$('now').textContent='Source video';};
async function checkSetup(){
  $('check-setup').disabled=true;
  try{
    const report=await api('/doctor');setupReady=report.ready;
    const failed=report.checks.filter(c=>c.status==='error');
    $('readiness').replaceChildren(node('span',report.ready?'Setup ready for rendering.':'Setup needs attention.'));
    failed.forEach(c=>$('readiness').append(node('p',`${c.message}. ${c.fix}`)));
    if(report.ready && !report.offline_ready)$('readiness').append(node('p','Model not cached: transcription may need its first download.'));
  }catch(e){setupReady=false;$('readiness').textContent=`Setup check failed: ${e.message}`;}
  finally{$('check-setup').disabled=false;buttons();}
}
$('check-setup').onclick=checkSetup;
async function submit(previewOnly){
  let clips=selected();
  if(previewOnly){
    const card=active || [...document.querySelectorAll('.card')].find(c=>c.querySelector('input[type=checkbox]').checked);
    if(!card)return error('Preview a candidate or check one first.');
    clips=[{id:card.dataset.id,start:Number(card.querySelector('[data-time=start]').value),end:Number(card.querySelector('[data-time=end]').value)}];
  }
  if(!clips.length)return error('Select at least one candidate.');
  if(clips.some(c=>!Number.isFinite(c.start)||!Number.isFinite(c.end)||c.start<0||c.end<=c.start||c.end>plan.duration))return error('Check the selected timestamps.');
  submitting=true;buttons();
  try{
    const job=await api(previewOnly?'/preview':'/render',{clips,layout:$('layout').value,resolution:$('resolution').value,preset:$('preset').value||null,seconds:Number($('preview-seconds').value)});
    currentJob=job.id;submitting=false;buttons();$('progress').hidden=false;$('progress').value=0;$('cancel').hidden=false;$('results').replaceChildren();poll();
  }catch(e){submitting=false;error(e.message);finish();}
}
$('render').onclick=()=>submit(false);
$('render-preview').onclick=()=>submit(true);
$('cancel').onclick=async()=>{ if(currentJob) { try{ await api('/cancel',{job_id:currentJob}); $('status').textContent='Cancellation requested…'; }catch(e){error(e.message);} } };
$('play').onclick=()=>{if(active)preview(active);};
$('video').addEventListener('timeupdate',()=>{if(rangeEnd!==undefined && $('video').currentTime>=rangeEnd){$('video').pause();$('video').currentTime=rangeEnd;rangeEnd=undefined;}});
function exportSummary(){
  const platform=$('preset').value;
  const landscape=$('layout').querySelector('[value=landscape]');
  landscape.disabled=Boolean(platform);
  if(platform && $('layout').value==='landscape') $('layout').value='fit';
  const small=$('resolution').value==='720p';
  let width=small?720:1080, height=small?1280:1920;
  if($('layout').value==='landscape') [width,height]=[height,width];
  $('dimensions').textContent=`${width} × ${height} · ${width<height?'9:16 vertical':'16:9 landscape'} · MP4 / H.264 / AAC`;
}
function stalePreview(){
  if(!$('source-view').hidden)$('player-mode').textContent='Settings or timestamps changed. Render a new preview before approving the export.';
}
['preset','resolution','layout','preview-seconds'].forEach(id=>$(id).addEventListener('change',()=>{exportSummary();stalePreview();}));
async function init(){
  plan=await api('/plan'); $('video').src=url('/media');
  $('count').textContent=`${plan.clips.length} candidates`; $('mode').textContent=`${plan.mode} · ${plan.method} · ${plan.note}`;
  $('layout').value=plan.export_defaults?.layout || (['gaming','instruction'].includes(plan.mode)?'fit':'portrait');
  $('preset').value=plan.export_defaults?.preset||'reels';
  $('resolution').value=plan.export_defaults?.resolution||'auto';
  exportSummary();
  checkSetup();
  if(!plan.clips.length) $('cards').append(node('p','No candidates found. Try a shorter duration range.','hint'));
  plan.clips.forEach(clip=>{
    const card=node('article',undefined,'card'); card.dataset.id=clip.id;
    const top=node('div',undefined,'card-top'), check=node('input');check.type='checkbox';check.id=`select-${clip.id}`;
    const label=node('label',clip.title);label.htmlFor=check.id;
    top.append(check,label,node('span',`${clip.score.toFixed(0)} · ${clip.confidence}`,'badge'));card.append(top);
    const thumbs=node('div',undefined,'thumbs');(clip.thumbnails||[]).forEach((_,i)=>{const img=node('img');img.src=url(`/thumbnail/${encodeURIComponent(clip.id)}/${i}`);img.alt=`Preview frame ${i+1}`;img.loading='lazy';thumbs.append(img);});card.append(thumbs);
    if(clip.content_mode) card.append(node('p',`Transcript content: ${clip.content_mode} · matched goal concepts: ${(clip.goal_matches||[]).join(', ')||'none'}`,'hint'));
    if(clip.boundary) card.append(node('p',`Boundaries: ${clip.boundary.start_clean?'opening cue found':'opening needs review'} · ${clip.boundary.end_clean?'ending cue found':'ending needs review'}`,'hint'));
    const times=node('div',undefined,'times');['start','end'].forEach(key=>{const label=node('label',`${key==='start'?'Start':'End'} (seconds)`), input=node('input');input.type='number';input.step='0.1';input.min='0';input.max=String(plan.duration);input.value=clip[key];input.dataset.time=key;input.addEventListener('input',stalePreview);label.append(input);times.append(label);});card.append(times);
    const button=node('button','Preview range');button.type='button';button.onclick=()=>preview(card);card.append(button,node('p',clip.transcript,'transcript'),node('p',clip.reason,'reason'));
    if(clip.warnings?.length)card.append(node('p',clip.warnings.join(' · '),'reason'));
    $('cards').append(card);
  });
}
init().catch(e=>error(e.message));
