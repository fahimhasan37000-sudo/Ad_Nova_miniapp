const tg = window.Telegram?.WebApp;
tg?.ready(); tg?.expand();
const initData = tg?.initData || "";
const headers = {"Content-Type":"application/json","X-Telegram-Init-Data":initData};
const $ = id => document.getElementById(id);
function toast(msg){const el=$("toast");el.textContent=msg;el.style.display="block";setTimeout(()=>el.style.display="none",2800)}
async function api(path,opts={}){const r=await fetch(path,{...opts,headers:{...headers,...opts.headers}});let d;try{d=await r.json()}catch{d={}}if(!r.ok)throw new Error(d.detail||"Request failed");return d}
async function loadMe(){if(!initData){$("greeting").textContent="Open inside Telegram";$("tasks").innerHTML='<p class="muted">For secure account access, open this page from your Telegram bot.</p>';return}
try{const u=await api("/api/me");$("greeting").textContent=u.first_name||"Earning Hub";$("balance").textContent=Number(u.balance_usd).toFixed(4);$("pending").textContent=Number(u.pending_balance_usd).toFixed(4);const botName=location.hostname;const uid=u.telegram_id;$("refLink").textContent=`Share your bot start link with referral code ${uid}. Configure your actual bot username after setup.`}catch(e){toast(e.message)}}
async function loadTasks(){if(!initData)return;try{const tasks=await api("/api/tasks");$("tasks").innerHTML=tasks.length?tasks.map(t=>`<div class="task"><strong>${escapeHtml(t.title)} <span style="float:right;color:#16a36a">$${Number(t.reward_usd).toFixed(4)}</span></strong><p>${escapeHtml(t.description||"Complete the task and submit it for verification.")}</p>${t.target_url?`<a href="${safeUrl(t.target_url)}" target="_blank" rel="noopener">Open task</a><br>`:""}<button data-task="${t.id}">Submit for verification</button></div>`).join(""):'<p class="muted">No tasks available yet.</p>'}catch(e){$("tasks").innerHTML=`<p class="muted">${escapeHtml(e.message)}</p>`}}
function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
function safeUrl(s){try{const u=new URL(s);return ["https:","http:"].includes(u.protocol)?u.href:"#"}catch{return "#"}}
$("tasks").addEventListener("click",async e=>{const b=e.target.closest("[data-task]");if(!b)return;try{const d=await api("/api/tasks/complete",{method:"POST",body:JSON.stringify({task_id:Number(b.dataset.task),proof:""})});toast(d.message);b.disabled=true;b.textContent="Pending review"}catch(err){toast(err.message)}});
$("withdrawSubmit").addEventListener("click",async()=>{try{const d=await api("/api/withdrawals",{method:"POST",body:JSON.stringify({amount_usd:$("withdrawAmount").value,method:$("withdrawMethod").value,payout_details:$("withdrawDetails").value})});$("withdrawMessage").textContent=`Request #${d.id}: ${d.status}`;toast(d.message);loadMe()}catch(e){$("withdrawMessage").textContent=e.message}});
$("loadHistory").addEventListener("click",async()=>{try{const h=await api("/api/history");$("history").innerHTML=h.length?h.map(x=>`<p class="muted">${escapeHtml(x.type)} — $${Number(x.amount_usd).toFixed(4)} — ${escapeHtml(x.note)}</p>`).join(""):"<p class='muted'>No transactions yet.</p>"}catch(e){toast(e.message)}});
$("copyRef").addEventListener("click",async()=>{try{await navigator.clipboard.writeText($("refLink").textContent);toast("Copied")}catch{toast("Select and copy the referral link")}})
$("withdrawScroll").onclick=()=>$("withdraw").scrollIntoView({behavior:"smooth"});
document.querySelectorAll("[data-section]").forEach(b=>b.onclick=()=>$(b.dataset.section).scrollIntoView({behavior:"smooth"}));
loadMe().then(loadTasks);
