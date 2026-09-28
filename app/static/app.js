const $=s=>document.querySelector(s);let currentArticle=null;
async function api(path,opt={}){
  const r=await fetch(path,{headers:{"Content-Type":"application/json"},...opt});
  if(!r.ok){
    let message=await r.text();
    try{
      const detail=JSON.parse(message).detail;
      message=Array.isArray(detail)?detail.map(item=>item.msg||String(item)).join("；"):
        typeof detail==="object"?JSON.stringify(detail):detail||message;
    }catch(_){/* plain-text response */}
    throw new Error(message);
  }
  return r.headers.get("content-type")?.includes("application/json")?r.json():r;
}
function note(t,err=false){$("#notice").textContent=t;$("#notice").className=err?"error":""}
function page(id){document.querySelectorAll(".page").forEach(x=>x.classList.remove("active"));$("#"+id).classList.add("active");if(id==="home")dashboard();if(id==="settings")settings();if(id==="records")loadRecords();if(id==="search")searchStudents()}
document.querySelectorAll("[data-page]").forEach(b=>b.onclick=()=>page(b.dataset.page));
async function dashboard(){let d=await api("/api/dashboard");$("#articles").textContent=d.articles;$("#validrecords").textContent=d.valid_records||0;$("#review").textContent=d.needs_review;$("#lastsync").textContent=d.last_sync||"尚未同步"}
function recordCard(r){return `<article class="result"><h3>${escape(r.student_name)}${r.needs_review?'<span class="tag review">待核对</span>':''}</h3><div class="record-fields"><span class="tag">届别：${escape(r.graduation_year)}</span><span class="tag">年级：${escape(r.grade)}</span><span class="tag">学历：${escape(r.degree)}</span><span class="tag">专业：${escape(r.major)}</span><span class="tag">城市或地区：${escape(r.city)}</span><span class="tag">就业单位：${escape(r.employer)}</span><span class="tag">岗位：${escape(r.position)}</span></div><p class="meta">来源文章：${escape(r.title)} · ${escape(r.published_at||'')}</p><details><summary>查看OCR证据文字</summary><pre>${escape(r.evidence_text)}</pre></details></article>`}
async function loadRecords(){try{let d=await api("/api/records?limit=1000");$("#recordlist").innerHTML=d.results.length?d.results.map(recordCard).join(""):"<p>还没有有效记录。请先获取数据，然后重新识别全部就业分享。</p>"}catch(e){note(e.message,true)}}
async function watch(path,target){for(let i=0;i<720;i++){let d=await api(path);$(target).textContent=`状态：${d.status}\n进度：${d.current||0}/${d.total||0}\n成功：${d.success||0}，失败：${d.failed||0}\n${d.message||""}`;if(["completed","failed","idle"].includes(d.status)){dashboard();return d}await new Promise(r=>setTimeout(r,1000))}}
$("#login").onclick=async()=>{try{let x=await api("/api/auth/start",{method:"POST"});note(x.message)}catch(e){note(e.message,true)}};
$("#confirm").onclick=async()=>{try{let x=await api("/api/auth/confirm",{method:"POST"});note(x.message,!x.logged_in)}catch(e){note(e.message,true)}};
async function sync(mode,autoProcess=false){try{await api("/api/sync/start",{method:"POST",body:JSON.stringify({mode,max_pages:mode==="full"?1000:2})});let done=await watch("/api/sync/status","#syncstatus");if(autoProcess&&done?.status==="completed"){note("数据已同步并可立即搜索，正在后台补充处理附件……");await api("/api/process/start",{method:"POST",body:JSON.stringify({all_local:false,build_index:false})});watch("/api/process/status","#processstatus");page("search")}}catch(e){note(e.message,true)}}
$("#mock").onclick=()=>sync("mock");$("#testsync").onclick=()=>sync("test");$("#fullsync").onclick=()=>sync("full",true);$("#retry").onclick=async()=>{await api("/api/sync/retry",{method:"POST"});watch("/api/sync/status","#syncstatus")};
async function process(all){try{await api("/api/process/start",{method:"POST",body:JSON.stringify({all_local:all,build_index:false})});watch("/api/process/status","#processstatus")}catch(e){note(e.message,true)}}
$("#processnew").onclick=()=>process(false);$("#processall").onclick=()=>process(true);
async function searchStudents(){
  const values={q:$("#q").value.trim(),graduation_year:$("#year").value.trim(),degree:$("#degree").value,major:$("#major").value.trim(),city:$("#city").value.trim()};
  try{
    const all=(await api("/api/records?limit=1000")).results;
    const words=values.q.toLocaleLowerCase().split(/\s+/).filter(Boolean);
    const fields=["student_name","graduation_year","grade","degree","major","city","employer","position","title"];
    const results=all.filter(r=>{
      const text=fields.map(field=>String(r[field]||"").toLocaleLowerCase());
      return words.every(word=>text.some(value=>value.includes(word)))&&
        ["graduation_year","degree","major","city"].every(field=>!values[field]||String(r[field]||"").includes(values[field]));
    });
    $("#resultcount").textContent=`找到 ${results.length} 条选调生记录（本地共 ${all.length} 条）`;
    if(results.length){$("#results").innerHTML=results.map(recordCard).join("");return}
    const terms=[values.q,values.graduation_year,values.degree,values.major,values.city].filter(Boolean).join("、");
    const counts=new Map();
    all.map(r=>r.city).filter(city=>city&&city!=="待人工核对"&&!city.includes("省级单位")).forEach(city=>counts.set(city,(counts.get(city)||0)+1));
    const cityExamples=[...counts].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0],"zh-CN")).slice(0,6).map(item=>item[0]);
    const examples=cityExamples.map((city,i)=>`<button type="button" class="city-example" data-index="${i}">${escape(city)}</button>`).join(" ");
    $("#results").innerHTML=`<article class="result"><p>当前 ${all.length} 条选调生记录中，没有匹配“${escape(terms)}”的学生。此处只查学生记录，模拟文章和普通通知不计入。</p>${examples?`<p>可试试已有地区：</p><div class="actions">${examples}</div>`:""}</article>`;
    document.querySelectorAll(".city-example").forEach(button=>button.onclick=()=>{$("#searchform").reset();$("#q").value=cityExamples[Number(button.dataset.index)];searchStudents()});
  }catch(e){note(e.message,true)}
}
$("#searchform").onsubmit=e=>{e.preventDefault();searchStudents()};
$("#clearsearch").onclick=()=>{$("#searchform").reset();searchStudents()};
function escape(v){const d=document.createElement("div");d.textContent=v??"";return d.innerHTML}window.showArticle=async id=>{let a=await api("/api/articles/"+id);currentArticle=a;$("#detailtitle").textContent=a.title;$("#detailtext").textContent=a.text_preview;$("#record").innerHTML=["graduation_year","grade","degree","major","city","employer","position"].map(k=>`<span class="tag">${k}：${escape(a[k]||"待人工核对")}</span>`).join("")+"<pre>证据："+escape(JSON.stringify(a.evidence,null,2))+"</pre>";$("#reviewfields").innerHTML=["graduation_year","grade","degree","major","city","employer","position","evidence_sentence"].map(k=>`<label>${k}<input name="${k}" value="${escape(a[k]||"")}"></label>`).join(" ");page("detail")};
$("#reviewform").onsubmit=async e=>{e.preventDefault();let d=Object.fromEntries(new FormData(e.target));d.needs_review=false;await api("/api/articles/"+currentArticle.id+"/review",{method:"PUT",body:JSON.stringify(d)});note("人工核对已保存");dashboard()};
async function settings(){
  const box=$("#config");
  box.value="正在加载本地页面配置…";
  try{
    const d=await api("/api/settings");
    box.value=JSON.stringify(d,null,2);
  }catch(e){
    box.value=JSON.stringify({
      portal_url:"https://TODO-PORTAL-URL",allowed_domains:["TODO-ALLOWED-DOMAIN"],
      employment_entry:"https://TODO-EMPLOYMENT-ENTRY",list_item_selector:"TODO_LIST_ITEM_SELECTOR",
      title_selector:"TODO_TITLE_SELECTOR",date_selector:"TODO_DATE_SELECTOR",
      detail_link_selector:"TODO_DETAIL_LINK_SELECTOR",next_button_selector:"TODO_NEXT_BUTTON_SELECTOR",
      detail_body_selector:"TODO_DETAIL_BODY_SELECTOR",attachment_selector:"TODO_ATTACHMENT_SELECTOR",
      detail_open_mode:"link",data_source:"page",api_keywords:["选调经验"],api_notice_type:10,
      api_detail_url_template:"https://TODO-DETAIL-URL?notice_id={notice_id}&type={notice_type}",
      login_page_markers:["登录","统一认证"],page_interval_seconds:1.5
    },null,2);
    note("无法读取本地配置，已显示可编辑的默认配置："+e.message,true);
  }
}
$("#saveconfig").onclick=async()=>{try{let values=JSON.parse($("#config").value);await api("/api/settings",{method:"PUT",body:JSON.stringify({values})});note("设置已保存到 config/portal.yaml") }catch(e){note("设置格式错误："+e.message,true)}};
$("#testselectors").onclick=async()=>{try{let d=await api("/api/settings/test-selectors",{method:"POST"});$("#selectorstatus").textContent=JSON.stringify(d,null,2)}catch(e){note(e.message,true)}};
$("#export").onclick=()=>{window.location="/api/export"};dashboard();
