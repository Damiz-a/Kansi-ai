document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.alert').forEach(a => {
        setTimeout(() => { a.style.transition='opacity 0.6s,transform 0.6s'; a.style.opacity='0'; a.style.transform='translateY(-10px)'; setTimeout(()=>a.remove(),600); }, 6000);
    });

    const obs = new IntersectionObserver(entries => {
        entries.forEach(e => { if(e.isIntersecting){e.target.classList.add('vis');obs.unobserve(e.target);} });
    }, {threshold:0.1});
    document.querySelectorAll('.card,.feature-card,.stat-card').forEach(el => {
        el.style.opacity='0';el.style.transform='translateY(15px)';el.style.transition='opacity 0.6s,transform 0.6s';obs.observe(el);
    });
    const s=document.createElement('style');s.textContent='.vis{opacity:1!important;transform:translateY(0)!important;}';document.head.appendChild(s);

    const ta=document.querySelector('textarea[name="text"]');
    if(ta){
        const c=document.createElement('div');c.style.cssText='text-align:right;font-size:0.8rem;color:var(--text-muted);margin-top:0.35rem;';
        ta.parentNode.appendChild(c);
        const upd=()=>{const l=ta.value.length;c.textContent=l+' char'+(l!==1?'s':'');c.style.color=l<10?'var(--danger)':'var(--text-muted)';};
        ta.addEventListener('input',upd);upd();
    }

    const wh1=document.querySelector('.welcome h1');
    if(wh1){const m=wh1.textContent.match(/Welcome,\s*(.+)!/);if(m){const h=new Date().getHours();const g=h<12?'Good morning':h<17?'Good afternoon':h<21?'Good evening':'Hello';wh1.textContent=g+', '+m[1]+'!';}}
});

function signInWithGoogle(){
    const email=prompt('Enter your Google email address:');
    if(!email||!email.includes('@'))return;
    fetch('/auth/google',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:email,name:email.split('@')[0].replace(/[._]/g,' '),google_id:'google_'+Date.now()})})
    .then(r=>r.json()).then(d=>{if(d.success)window.location.href=d.redirect;else alert(d.error||'Authentication failed.');})
    .catch(()=>alert('Connection error.'));
}
