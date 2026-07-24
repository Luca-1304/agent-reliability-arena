const $=(s,c=document)=>c.querySelector(s);const $$=(s,c=document)=>[...c.querySelectorAll(s)];
const header=$('[data-header]'),cursor=$('.cursor-field'),menu=$('[data-menu]'),nav=$('[data-nav]');
addEventListener('scroll',()=>header?.classList.toggle('scrolled',scrollY>18),{passive:true});
addEventListener('pointermove',e=>{if(cursor){cursor.style.left=e.clientX+'px';cursor.style.top=e.clientY+'px'}},{passive:true});
menu?.addEventListener('click',()=>{const open=nav?.classList.toggle('open')??false;menu.setAttribute('aria-expanded',String(open))});
$$('#primary-nav a').forEach(x=>x.addEventListener('click',()=>{nav?.classList.remove('open');menu?.setAttribute('aria-expanded','false')}));
const io='IntersectionObserver'in window?new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('visible');io.unobserve(e.target)}}),{threshold:.08}):null;$$('.reveal').forEach(x=>io?io.observe(x):x.classList.add('visible'));
$$('[data-filter]').forEach(button=>button.addEventListener('click',()=>{const category=button.dataset.filter;$$('[data-filter]').forEach(x=>x.classList.toggle('active',x===button));$$('[data-category]').forEach(card=>{card.hidden=category!=='all'&&card.dataset.category!==category})}));
function addSocialFooter(){const footer=$('.footer-inner');if(!footer||$('.footer-socials',footer))return;const socials=document.createElement('nav');socials.className='footer-socials';socials.setAttribute('aria-label','Social profiles');socials.innerHTML='<a href="https://www.linkedin.com/in/luca-panayiotou-64936b256/" target="_blank" rel="noreferrer noopener" aria-label="Luca Panayiotou on LinkedIn">LinkedIn</a>';const note=$('p',footer);if(note)footer.insertBefore(socials,note);else footer.append(socials)}
addSocialFooter();
addEventListener('keydown',e=>{if(e.key==='Escape'){nav?.classList.remove('open');menu?.setAttribute('aria-expanded','false')}});