import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, ArrowUpRight, Calculator, Check, ChevronRight, FileSearch, FileText, Globe2, Info, Languages, LockKeyhole, RefreshCw, ShieldAlert, UploadCloud } from 'lucide-react';

type Language='en'|'ar';
type Clause={id:string;page:number;text:string};
type Finding={id:string;clause_id:string;page:number;category:string;level:'high'|'review';title:string;quote:string;matched_phrase:string;explanation:string};
type Result={clauses:Clause[];findings:Finding[];analysis_method:string;disclaimer:string;pages_processed:number};
const API='http://localhost:8000';
const translations={
 en:{
  intro:'Read before you sign.',
  sub:'Review your student rental agreement, find clauses worth a closer look, and estimate possible costs.',
  analyze:'Review your agreement',
  demo:'Try sample agreement',
  upload:'Drop your lease PDF here, or browse',
  small:'Text-based PDF · 8 MB max · 25 pages',
  status:'This review matches English keywords. It can miss clauses or flag routine terms.',
  original:'Original agreement',
  findings:'Points to review',
  none:'No matching terms were found. Read the full agreement for terms the review may have missed.',
  financial:'Financial scenarios',
  deposit:'Deposit (RM)',
  rent:'Monthly rent (RM)',
  months:'Notice months (hypothetical)',
  exposure:'Illustrative exposure (not amount legally owed)',
  note:'This calculator assumes deposit plus notice rent; actual contract terms may differ and amounts may overlap.',
  source:'Source evidence',
  empty:'Upload a PDF or open the sample to begin.',
  page:'Page',
  run:'Review this PDF',
  working:'Reading document…',
  home:'Overview',
  review:'Review',
  privacy:'Uploaded agreements are processed for review and are not saved by ClauseX AI.',
  feature:'Built for students. Designed for clarity.',
  feat1:'Clause-focused review',
  feat1d:'See the original wording behind each flagged term.',
  feat2:'Arabic and English',
  feat2d:'Use the review tools in either language. Agreements stay in their original language.',
  feat3:'Original wording',
  feat3d:'Each finding shows the clause text and the page it came from.',
  label:'Student rental agreements',
  insight:'Understand your rental terms.',
  reviewTitle:'Contract workspace',
  terms:'For information only. This review does not provide legal advice or determine whether terms are enforceable.',
  clear:'Reset',
  invalid:'The document could not be reviewed. Please try again.',
  legal:'For information only. No legal advice.',
  copyright:'© 2026 ClauseX AI',
  previewTitle:'TENANCY AGREEMENT',
  previewClause:'The landlord may retain the security deposit if the tenancy ends early.',
  previewFinding:'Deposit clause to review',
  previewPage:'Early termination · Page 2',
  previewFile:'sample-agreement.pdf',
  uploaded:'Uploaded agreement',
  brandHome:'ClauseX AI home',
  workspaceLabel:'CLAUSEX / REVIEW',
  sampleError:'The sample agreement is unavailable right now. Please try again.',
  pdfOnly:'Choose a PDF with selectable text.',
  fileSize:'Choose a PDF that is 8 MB or smaller.',
  pageLimit:'Choose a PDF with 25 pages or fewer.',
  invalidPdf:'This PDF could not be opened. Try another file.',
  encryptedPdf:'Upload an unlocked copy of the PDF.',
  noText:'This PDF has no selectable text. Upload a text-based copy.',
 },
 ar:{
  intro:'اقرأ قبل أن توقّع.',
  sub:'راجع عقد إيجار سكنك الطلابي، وتعرّف على البنود التي تستحق انتباهك، وقدّر التكاليف المحتملة.',
  analyze:'راجع عقد الإيجار',
  demo:'جرّب عقدًا نموذجيًا',
  upload:'اسحب عقد PDF هنا أو اختر ملفًا',
  small:'PDF نصّي · حتى 8 ميجابايت · 25 صفحة',
  status:'تبحث المراجعة عن كلمات مفتاحية باللغة الإنجليزية، وقد تفوّت بعض البنود أو تبرز شروطًا اعتيادية.',
  original:'نص العقد الأصلي',
  findings:'بنود تستحق المراجعة',
  none:'لم تظهر عبارات مطابقة. اقرأ العقد كاملًا للاطلاع على البنود التي ربما فاتت المراجعة.',
  financial:'سيناريوهات مالية',
  deposit:'التأمين (RM)',
  rent:'الإيجار الشهري (RM)',
  months:'أشهر الإشعار الافتراضية',
  exposure:'تعرض مالي افتراضي (وليس مبلغًا واجب الدفع)',
  note:'الحساب يفترض جمع التأمين وإيجار الإشعار؛ قد تختلف الشروط الفعلية وقد تتداخل المبالغ.',
  source:'النص الأصلي المقتبس',
  empty:'ارفع ملف PDF أو جرّب العقد النموذجي للبدء.',
  page:'صفحة',
  run:'راجع ملف PDF',
  working:'جاري قراءة المستند…',
  home:'نظرة عامة',
  review:'المراجعة',
  privacy:'تعالج ClauseX AI الملفات المرفوعة للمراجعة دون الاحتفاظ بها.',
  feature:'مراجعة أوضح لعقود سكن الطلاب',
  feat1:'مراجعة البنود',
  feat1d:'اطّلع على النص الأصلي لكل بند مميّز.',
  feat2:'عربي وإنجليزي',
  feat2d:'استخدم أدوات المراجعة بأيٍّ من اللغتين. تبقى نصوص العقود بلغتها الأصلية.',
  feat3:'النص الأصلي',
  feat3d:'تعرض كل ملاحظة نص البند ورقم صفحته.',
  label:'عقود إيجار السكن الطلابي',
  insight:'افهم شروط الإيجار.',
  reviewTitle:'مساحة مراجعة العقد',
  terms:'هذه المراجعة لأغراض معلوماتية فقط، ولا تقدّم استشارة قانونية أو تحدّد قابلية إنفاذ الشروط.',
  clear:'إعادة ضبط',
  invalid:'تعذّرت مراجعة المستند. يرجى المحاولة مرة أخرى.',
  legal:'لأغراض معلوماتية فقط. لا تُعدّ استشارة قانونية.',
  copyright:'© 2026 ClauseX AI',
  previewTitle:'عقد إيجار',
  previewClause:'يجوز للمؤجر الاحتفاظ بمبلغ التأمين عند إنهاء عقد الإيجار مبكرًا.',
  previewFinding:'بند التأمين للمراجعة',
  previewPage:'الإنهاء المبكر · الصفحة ٢',
  previewFile:'عقد-نموذجي.pdf',
  uploaded:'العقد المرفوع',
  brandHome:'الصفحة الرئيسية لـ ClauseX AI',
  workspaceLabel:'مراجعة عقد الإيجار',
  sampleError:'العقد النموذجي غير متاح حاليًا. يرجى المحاولة مرة أخرى.',
  pdfOnly:'اختر ملف PDF يحتوي على نص قابل للتحديد.',
  fileSize:'اختر ملف PDF لا يتجاوز حجمه ٨ ميجابايت.',
  pageLimit:'اختر ملف PDF لا يتجاوز ٢٥ صفحة.',
  invalidPdf:'تعذّر فتح ملف PDF. جرّب ملفًا آخر.',
  encryptedPdf:'ارفع نسخة من ملف PDF غير محمية بكلمة مرور.',
  noText:'لا يحتوي هذا الملف على نص قابل للتحديد. ارفع نسخة نصية من ملف PDF.',
 }
};
const uploadErrorKeys:Partial<Record<string,keyof typeof translations.en>>={
 'Only text-based PDF files are supported in Sprint 1.':'pdfOnly',
 'File exceeds the 8 MB limit.':'fileSize',
 'Maximum 25 pages per document.':'pageLimit',
 'File does not have a valid PDF signature.':'invalidPdf',
 'Cannot read this PDF file.':'invalidPdf',
 'Encrypted PDFs are not supported.':'encryptedPdf',
 'This PDF has no selectable text. OCR support is planned.':'noText',
};
const categoryTitles:Record<string,{en:string,ar:string}>={deposit:{en:'Security deposit',ar:'شروط التأمين'},termination:{en:'Early termination',ar:'الإنهاء المبكر'},fees:{en:'Additional fees',ar:'رسوم إضافية'},entry:{en:'Landlord access',ar:'دخول المؤجر'},maintenance:{en:'Maintenance duties',ar:'مسؤوليات الصيانة'}};
function App(){
 const [lang,setLang]=useState<Language>('en'); const t=translations[lang];
 const [result,setResult]=useState<Result|null>(null); const [sampleText,setSampleText]=useState('');
 const [file,setFile]=useState<File|null>(null); const [fileUrl,setFileUrl]=useState('');
 const [busy,setBusy]=useState(false); const [error,setError]=useState<keyof typeof translations.en|null>(null); const [active,setActive]=useState<string>('');
 const [deposit,setDeposit]=useState(2000); const [rent,setRent]=useState(1000); const [months,setMonths]=useState(2);
 const [view,setView]=useState<'home'|'review'>('home');
 useEffect(()=>()=>{if(fileUrl)URL.revokeObjectURL(fileUrl)},[fileUrl]);
 const chosen=useMemo(()=>result?.findings.find(x=>x.id===active)||result?.findings[0], [result,active]);
 const chosenClause=useMemo(()=>result?.clauses.find(c=>c.id===chosen?.clause_id),[result,chosen]);
 const money=(x:number)=>'RM '+Math.max(0,x||0).toLocaleString('en-MY',{maximumFractionDigits:2});
 useEffect(()=>{
  document.documentElement.lang=lang;
  document.documentElement.dir=lang==='ar'?'rtl':'ltr';
  document.title=`ClauseX AI — ${t.label}`;
 },[lang,t.label]);
 const changeFile=(f?:File)=>{setError(null);setResult(null);setSampleText('');setFile(f||null);setFileUrl(f?URL.createObjectURL(f):'');setActive('');};
 const loadSample=async()=>{setBusy(true);setError(null);try{const res=await fetch(`${API}/api/sample`);if(!res.ok){setError('sampleError');return;}const data=await res.json();setSampleText(data.text);setResult(data);setFile(null);setFileUrl('');setActive(data.findings?.[0]?.id||'');setView('review');}catch{setError('sampleError')}finally{setBusy(false)}};
 const analyze=async()=>{if(!file)return;setBusy(true);setError(null);try{const fd=new FormData();fd.append('file',file);const res=await fetch(`${API}/api/analyze-file`,{method:'POST',body:fd});const data=await res.json();if(!res.ok){setError(uploadErrorKeys[data.detail]||'invalid');return;}setResult(data);setActive(data.findings?.[0]?.id||'');setView('review');}catch{setError('invalid');}finally{setBusy(false)}};
 return <div className="app" dir={lang==='ar'?'rtl':'ltr'}>
  <header className="header"><button className="brand" onClick={()=>setView('home')} aria-label={t.brandHome}><span className="brand-symbol"><FileSearch size={22}/></span><span>Clause<span className="brand-x">X</span><small> AI</small></span></button><nav><button className={view==='home'?'nav-active':''} onClick={()=>setView('home')}>{t.home}</button><button className={view==='review'?'nav-active':''} onClick={()=>setView('review')}>{t.review}</button></nav><div className="header-actions"><span className="lang-icon"><Globe2 size={16}/></span><button className="lang-toggle" onClick={()=>setLang(l=>l==='en'?'ar':'en')}><Languages size={17}/>{lang==='en'?'العربية':'English'}</button></div></header>
  {view==='home'?<main><section className="hero"><div className="hero-copy"><div className="eyebrow"><span className="eyebrow-dot"/>{t.label}</div><h1>{t.intro}<br/><span>{t.insight}</span></h1><p className="hero-sub">{t.sub}</p><div className="hero-cta"><button className="primary" onClick={()=>setView('review')}>{t.analyze}<ArrowRight size={18}/></button><button className="ghost" onClick={loadSample} disabled={busy}>{t.demo}<ArrowUpRight size={18}/></button></div>{error==='sampleError'&&<div role="alert" className="error"><Info size={16}/>{t[error]}</div>}<div className="under-hero"><LockKeyhole size={15}/><span>{t.privacy}</span></div></div><div className="hero-preview"><div className="preview-toolbar"><div className="preview-dots"><i/><i/><i/></div><span>{t.previewFile}</span><span className="tiny-chip">ClauseX</span></div><div className="preview-content"><span className="preview-kicker">{t.previewTitle}</span><div className="fake-line long"/><div className="fake-line"/><div className="fake-line medium"/><div className="fake-clause"><span>02</span>{t.previewClause}</div><div className="fake-line"/><div className="fake-line medium"/><div className="preview-alert"><ShieldAlert size={18}/><div><strong>{t.previewFinding}</strong><small>{t.previewPage}</small></div><ChevronRight size={17}/></div></div></div></section><section className="features"><div><span className="section-overline">ClauseX AI</span><h2>{t.feature}</h2></div><div className="feature-grid"><article><FileText size={24}/><h3>{t.feat1}</h3><p>{t.feat1d}</p></article><article><Languages size={24}/><h3>{t.feat2}</h3><p>{t.feat2d}</p></article><article><ShieldAlert size={24}/><h3>{t.feat3}</h3><p>{t.feat3d}</p></article></div></section></main>:<main className="workspace"><div className="workspace-heading"><div><span className="section-overline">{t.workspaceLabel}</span><h1>{t.reviewTitle}</h1><p>{t.terms}</p></div><button className="outline" disabled={busy} onClick={()=>{changeFile();setView('review')}}><RefreshCw size={15}/>{t.clear}</button></div><div className="workspace-grid"><aside className="upload-panel"><h2><UploadCloud size={19}/>{t.analyze}</h2><label className="dropzone" onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();if(!busy)changeFile(e.dataTransfer.files[0]);}}><input type="file" accept=".pdf,application/pdf" disabled={busy} onChange={e=>{changeFile(e.target.files?.[0]);e.target.value='';}}/><UploadCloud size={32}/><strong>{file?.name||t.upload}</strong><span>{t.small}</span></label><div className="panel-buttons"><button className="primary small" onClick={analyze} disabled={!file||busy}>{busy?t.working:t.run}<ArrowRight size={16}/></button><button className="outline small" onClick={loadSample} disabled={busy}>{t.demo}</button></div>{error&&<div role="alert" className="error"><Info size={16}/>{t[error]}</div>}<div className="privacy-tip"><Info size={17}/><span>{t.status}</span></div></aside><section className="document-panel"><div className="panel-heading"><h2><FileText size={19}/>{t.original}</h2><span>{result?`${result.pages_processed} ${t.page}`:'PDF'}</span></div>{fileUrl?<iframe title={t.uploaded} src={fileUrl}/>:sampleText?<div className="sample-doc" lang="en" dir="ltr">{sampleText}</div>:<div className="empty-doc"><FileText size={35}/><p>{t.empty}</p></div>}</section><aside className="insights-panel"><div className="panel-heading"><h2><ShieldAlert size={19}/>{t.findings}</h2><span className="count">{result?.findings.length||0}</span></div>{result?<>{result.findings.length? <div className="finding-list">{result.findings.map(f=><button key={f.id} className={'finding '+(f.id===chosen?.id?'selected':'')} onClick={()=>setActive(f.id)}><span className={'finding-tag '+f.level}>{f.level==='high'?'!':'•'}</span><div><b>{categoryTitles[f.category]?.[lang]||f.category}</b><small>{t.page} {f.page} · {f.matched_phrase}</small></div><ChevronRight size={16}/></button>)}</div>:<div className="empty-finding">{t.none}</div>}{chosen&&<div className="evidence"><span className="evidence-heading"><Check size={15}/>{t.source}</span><blockquote dir="auto">{chosenClause?.text||chosen.quote}</blockquote><small>{t.page} {chosen.page}</small></div>}</>:<div className="empty-finding">{t.empty}</div>}</aside></div><section className="finance"><div className="finance-title"><Calculator size={21}/><h2>{t.financial}</h2></div><div className="finance-grid"><label>{t.deposit}<input type="number" min="0" value={deposit} onChange={e=>setDeposit(Math.max(0,Number(e.target.value)))}/></label><label>{t.rent}<input type="number" min="0" value={rent} onChange={e=>setRent(Math.max(0,Number(e.target.value)))}/></label><label>{t.months}<input type="number" min="0" max="24" value={months} onChange={e=>setMonths(Math.max(0,Number(e.target.value)))}/></label><div className="finance-result"><span>{t.exposure}</span><strong>{money(deposit+rent*months)}</strong></div></div><p>{t.note}</p></section></main>}
  <footer><div className="footer-logo">Clause<span>X</span> AI</div><span>{t.legal}</span><span dir="ltr">{t.copyright}</span></footer>
 </div>
}
export default App;
