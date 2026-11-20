'use strict';
const token = new URLSearchParams(location.search).get('token');
const url = route => `${route}?token=${encodeURIComponent(token)}`;
const $ = id => document.getElementById(id);
let plan, active, currentJob, rangeEnd, timer;
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
  card.classList.add('active'); active=card; rangeEnd=end; $('video').currentTime=start;
  $('now').textContent=`${card.dataset.id} · ${start.toFixed(1)}–${end.toFixed(1)}s`;
  $('video').play().catch(()=>error('The browser could not play this source codec. Use a browser-compatible MP4.'));
}
function finish() { currentJob=null; clearTimeout(timer); $('render').disabled=false; $('cancel').hidden=true; }
async function poll() {
  try {
    const job=await api(`/jobs/${currentJob}`);
    $('status').className=''; $('status').textContent=`${job.status} · ${job.stage}`;
    $('progress').value=job.progress;
    if(job.status==='completed') {
      const result=job.result; $('results').replaceChildren();
      result.clips.forEach((clip,index)=>{
        const link=node('a',`Open rendered clip ${index+1}`); link.href=url(`/artifact/${job.id}/${index}/video`); link.target='_blank'; link.rel='noopener'; $('results').append(link);
        const sub=node('a',`Download subtitles ${index+1}`); sub.href=url(`/artifact/${job.id}/${index}/subtitles`); sub.download=`clip_${index+1}.srt`; $('results').append(sub);
      }); finish();
    } else if(['failed','cancelled'].includes(job.status)) { if(job.error) error(job.error); finish(); }
    else timer=setTimeout(poll,1000);
  } catch(e) { error(e.message); finish(); }
}
$('render').onclick=async()=>{
  const clips=selected(); if(!clips.length) return error('Select at least one candidate.');
  if(clips.some(c=>!Number.isFinite(c.start)||!Number.isFinite(c.end)||c.start<0||c.end<=c.start||c.end>plan.duration)) return error('Check the selected timestamps.');
  $('render').disabled=true;
  try { const job=await api('/render',{clips,layout:$('layout').value,resolution:$('resolution').value,preset:$('preset').value||null}); currentJob=job.id; $('progress').hidden=false; $('progress').value=0; $('cancel').hidden=false; $('results').replaceChildren(); poll(); }
  catch(e){ error(e.message); finish(); }
};
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
['preset','resolution','layout'].forEach(id=>$(id).addEventListener('change',exportSummary));
async function init(){
  plan=await api('/plan'); $('video').src=url('/media');
  $('count').textContent=`${plan.clips.length} candidates`; $('mode').textContent=`${plan.mode} · ${plan.method} · ${plan.note}`;
  $('layout').value=plan.export_defaults?.layout || (['gaming','instruction'].includes(plan.mode)?'fit':'portrait');
  $('preset').value=plan.export_defaults?.preset||'reels';
  $('resolution').value=plan.export_defaults?.resolution||'auto';
  exportSummary();
  if(!plan.clips.length) $('cards').append(node('p','No candidates found. Try a shorter duration range.','hint'));
  plan.clips.forEach(clip=>{
    const card=node('article',undefined,'card'); card.dataset.id=clip.id;
    const top=node('div',undefined,'card-top'), check=node('input');check.type='checkbox';check.id=`select-${clip.id}`;
    const label=node('label',clip.title);label.htmlFor=check.id;
    top.append(check,label,node('span',`${clip.score.toFixed(0)} · ${clip.confidence}`,'badge'));card.append(top);
    const thumbs=node('div',undefined,'thumbs');(clip.thumbnails||[]).forEach((_,i)=>{const img=node('img');img.src=url(`/thumbnail/${encodeURIComponent(clip.id)}/${i}`);img.alt=`Preview frame ${i+1}`;img.loading='lazy';thumbs.append(img);});card.append(thumbs);
    const times=node('div',undefined,'times');['start','end'].forEach(key=>{const label=node('label',`${key==='start'?'Start':'End'} (seconds)`), input=node('input');input.type='number';input.step='0.1';input.min='0';input.max=String(plan.duration);input.value=clip[key];input.dataset.time=key;label.append(input);times.append(label);});card.append(times);
    const button=node('button','Preview range');button.type='button';button.onclick=()=>preview(card);card.append(button,node('p',clip.transcript,'transcript'),node('p',clip.reason,'reason'));
    if(clip.warnings?.length)card.append(node('p',clip.warnings.join(' · '),'reason'));
    $('cards').append(card);
  });
}
init().catch(e=>error(e.message));
