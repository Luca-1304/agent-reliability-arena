const views={
  simple:`<div class="flow"><div><small>01</small><b>Objective</b><p>Purpose, constraints and decision owner.</p></div><div><small>02</small><b>Context</b><p>Sources, evidence and prior decisions.</p></div><div><small>03</small><b>AI leverage</b><p>Options, synthesis and comparison.</p></div><div><small>04</small><b>Validation</b><p>Evidence, uncertainty and risk.</p></div><div><small>05</small><b>Learning</b><p>Outcome, correction and next action.</p></div></div>`,
  technical:`<div class="flow"><div><small>01</small><b>Observation</b></div><div><small>02</small><b>Decision</b></div><div><small>03</small><b>Action</b></div><div><small>04</small><b>Outcome</b></div><div><small>05</small><b>Error</b></div><div><small>06</small><b>Correction</b></div><div><small>07</small><b>Confidence</b></div><div><small>08</small><b>Provenance</b></div><div><small>09</small><b>Reusable pattern</b></div><div><small>10</small><b>Next action</b></div></div>`,
  status:`<div class="flow"><div><span class="badge verified">Verified</span><p>Repeated use with observable artefacts.</p></div><div><span class="badge prototype">Prototype</span><p>Working demonstration, not production-hardened.</p></div><div><span class="badge framework">Framework</span><p>Structured method or architecture guiding work.</p></div><div><b>Planned</b><p>Intentional next step, not implemented.</p></div></div>`
};
const panel=document.getElementById('nexus-panel');
panel.innerHTML=views.simple;
document.querySelectorAll('.tabs button').forEach(button=>button.addEventListener('click',()=>{
  document.querySelectorAll('.tabs button').forEach(x=>x.classList.remove('active'));
  button.classList.add('active');
  panel.innerHTML=views[button.dataset.view];
}));
function openCV(){document.getElementById('cv').classList.add('open')}
function closeCV(){document.getElementById('cv').classList.remove('open')}
window.openCV=openCV;window.closeCV=closeCV;
addEventListener('keydown',event=>{if(event.key==='Escape')closeCV()});