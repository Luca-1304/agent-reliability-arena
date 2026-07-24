const $=(selector,scope=document)=>scope.querySelector(selector);const $$=(selector,scope=document)=>[...scope.querySelectorAll(selector)];
const header=$('[data-header]');const menu=$('[data-menu]');const nav=$('[data-nav]');
addEventListener('scroll',()=>header?.classList.toggle('scrolled',scrollY>18),{passive:true});
menu?.addEventListener('click',()=>{const open=nav?.classList.toggle('open')??false;menu.setAttribute('aria-expanded',String(open))});
$$('[data-nav] a').forEach(link=>link.addEventListener('click',()=>{nav?.classList.remove('open');menu?.setAttribute('aria-expanded','false')}));
document.addEventListener('click',event=>{if(event.target.closest('[data-nav] a')){nav?.classList.remove('open');menu?.setAttribute('aria-expanded','false')}});

function showDemo(key){$$('[data-demo]').forEach(tab=>{const active=tab.dataset.demo===key;tab.classList.toggle('active',active);tab.setAttribute('aria-selected',String(active))});$$('[data-demo-panel]').forEach(panel=>panel.classList.toggle('active',panel.dataset.demoPanel===key))}
$$('[data-demo]').forEach(tab=>tab.addEventListener('click',()=>showDemo(tab.dataset.demo)));

$$('[data-open-cv]').forEach(button=>button.addEventListener('click',()=>{location.href='index.html#experience'}));

const modal=$('[data-call-modal]');const state=$('[data-call-state]');const requestButton=$('[data-request-call]');let previousFocus=null;
function openCall(){if(!modal)return;previousFocus=document.activeElement;modal.classList.add('open');modal.setAttribute('aria-hidden','false');document.body.style.overflow='hidden';$('[data-request-call]',modal)?.focus()}
function closeCall(){if(!modal)return;modal.classList.remove('open');modal.setAttribute('aria-hidden','true');document.body.style.overflow='';previousFocus?.focus?.()}
$$('[data-call-luca]').forEach(button=>button.addEventListener('click',openCall));$$('[data-close-call]').forEach(button=>button.addEventListener('click',closeCall));

async function requestProtectedPhone(){const endpoint=document.body.dataset.callEndpoint||'/api/contact/call';state.dataset.state='loading';state.textContent='Validating the protected request…';requestButton.disabled=true;try{const response=await fetch(endpoint,{method:'POST',credentials:'same-origin',headers:{'Accept':'application/json','Content-Type':'application/json'},body:JSON.stringify({intent:'call',source:'portfolio'})});if(!response.ok)throw new Error(`Protected endpoint returned ${response.status}`);const payload=await response.json();if(!payload||typeof payload.tel!=='string'||!payload.tel.startsWith('tel:'))throw new Error('Protected endpoint returned an invalid dial action');state.dataset.state='success';state.textContent='Protected contact action approved. Opening your device dialler…';location.href=payload.tel}catch(error){state.dataset.state='error';state.textContent='The protected call endpoint is not active in this public branch preview. No phone number is present in the current preview files. Please use the business email or LinkedIn fallback.'}finally{requestButton.disabled=false}}
requestButton?.addEventListener('click',requestProtectedPhone);
addEventListener('keydown',event=>{if(event.key==='Escape'){closeCall();nav?.classList.remove('open');menu?.setAttribute('aria-expanded','false')}});
showDemo('evaluation');

if(!document.querySelector('script[data-flagship-loader]')){const flagship=document.createElement('script');flagship.src='flagship.js';flagship.defer=true;flagship.dataset.flagshipLoader='true';document.head.append(flagship)}
