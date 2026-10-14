/* Read completed stage outputs only. No sample values and no demo execution. */
(() => {
  const stages = ['storage', 'mapreduce', 'hive', 'pig', 'hbase'];
  const labels = {storage:'HDFS',mapreduce:'MapReduce + YARN',hive:'Hive',pig:'Pig',hbase:'HBase'};
  const commands = {storage:'storage',mapreduce:'mapreduce',hive:'hive',pig:'pig',hbase:'hbase --child D000030'};
  const colors = {blue:'#a3bddb',teal:'#9e7956',orange:'#e5acc9',red:'#edd987',pale:'#d8e4ef'};
  const number = value => value == null ? '—' : new Intl.NumberFormat('id-ID').format(value);
  const percent = value => value == null ? 'N/A' : new Intl.NumberFormat('id-ID',{minimumFractionDigits:2,maximumFractionDigits:2}).format(value)+'%';
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const $ = id => document.getElementById(id);
  const short = value => value.replace(/^Kabupaten /,'');
  let current = null, signature = '', hiveProvince = '', hiveMetric = 'coverage_pct', pigList = 'dropout_d1_d3';
  const ready = stage => current?.stages[stage]?.status === 'ready';

  function empty(stage, message) {
    return `<div class="empty"><span class="empty-symbol" aria-hidden="true">·</span><div><h3>${esc(message || 'Belum ada hasil '+labels[stage])}</h3><p>Hasil muncul setelah tahap ini selesai dijalankan.</p><code class="command">python code/demo.py ${commands[stage]}</code></div></div>`;
  }
  function downloads(stage, names) {
    const artifacts = current.stages[stage].artifacts || {};
    return `<div class="downloads">${names.filter(n=>artifacts[n]).map(n=>`<a href="${esc(artifacts[n])}" download>${esc(n)}</a>`).join('')}</div>`;
  }
  function table(headers, rows) {
    return `<div class="table-wrap"><table><thead><tr>${headers.map(h=>`<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map(v=>`<td>${esc(v)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  }
  function legend(items) {
    return `<div class="legend">${items.map(i=>`<span><i style="background:${i.color}"></i>${esc(i.label)}</span>`).join('')}</div>`;
  }
  function chart(rows, series, {maximum=null, percentages=false,title='Grafik hasil',labelKey='district',rowHeight=40}={}) {
    if (!rows.length) return '<p class="no-data">Tidak ada baris untuk pilihan ini.</p>';
    const width=860, left=193, right=82, top=30, bottom=30;
    const height=top+rows.length*rowHeight+bottom, plot=width-left-right;
    const max=maximum || Math.max(1,...rows.flatMap(r=>series.map(s=>Number(r[s.key] || 0))));
    let marks='';
    for (let i=0;i<=4;i++) {
      const value=max*i/4, x=left+plot*i/4;
      marks+=`<line x1="${x}" y1="24" x2="${x}" y2="${height-bottom}" stroke="#e4ebf1"/>`;
      marks+=`<text x="${x}" y="15" text-anchor="middle" fill="#72849a" font-size="13">${esc(percentages ? Math.round(value)+'%' : number(Math.round(value)))}</text>`;
    }
    rows.forEach((r,index)=>{
      const y=top+index*rowHeight, full=r[labelKey], label=labelKey==='district' ? short(full) : full;
      const display=label.length>24 ? label.slice(0,23)+'…' : label;
      marks+=`<text x="${left-12}" y="${y+rowHeight/2+4}" text-anchor="end" fill="#40556b" font-size="14"><title>${esc((r.province ? r.province+' / ' : '')+full)}</title>${esc(display)}</text>`;
      series.forEach((s,j)=>{
        const value=r[s.key], barHeight=series.length===1 ? 14 : 8;
        const barY=y+rowHeight/2-(series.length*barHeight+(series.length-1)*2)/2+j*(barHeight+2);
        const barWidth=value==null ? 0 : Math.max(0,Math.min(plot,plot*value/max));
        const text=percentages ? percent(value) : number(value);
        if (value!=null) marks+=`<rect x="${left}" y="${barY}" width="${barWidth}" height="${barHeight}" fill="${s.color}" rx="2"><title>${esc(full+' · '+s.label+': '+text)}</title></rect>`;
        marks+=`<text x="${Math.min(left+barWidth+8,width-65)}" y="${barY+barHeight-1}" fill="#385168" font-size="${series.length>1 ? 11 : 13}">${esc(text)}</text>`;
      });
    });
    return `<div class="chart-scroll"><svg class="chart" role="img" aria-label="${esc(title)}" viewBox="0 0 ${width} ${height}"><title>${esc(title)}</title>${marks}</svg></div>`;
  }

  function renderStorage() {
    const d=current.stages.storage.data;
    const files=d.files.filter(f=>f.name!=='metadata.json');
    const dataBlocks=files.reduce((total,f)=>total+f.blocks,0);
    $('content-storage').innerHTML=`<div class="grid-two"><div class="panel"><h3>Blok per file data</h3><p class="description">Satuan: jumlah potongan file, ukuran maksimal ${number(d.block_size_bytes/1024)} KiB.</p>${chart(files.map(f=>({...f,label:f.name})),[{key:'blocks',label:'Blok',color:colors.teal}],{labelKey:'label',title:'Jumlah blok per file data'})}</div><div class="panel"><h3>Ketahanan penyimpanan</h3><div class="mini-stats"><div><strong>${number(dataBlocks)}</strong><span>Blok file data</span></div><div><strong>${number(d.replication)}</strong><span>Salinan per blok</span></div></div><div class="status-list"><div><span>Isi file tetap sama</span><strong>${d.hash_matches ? 'Hash cocok' : 'Tidak cocok'}</strong></div><div><span>Jumlah salinan dipulihkan</span><strong>${d.replication_restored ? 'Ya' : 'Belum'}</strong></div></div></div></div>`;
  }
  function renderMapreduce() {
    const d=current.stages.mapreduce.data;
    const samples=d.results.slice(0,5);
    const series=[{key:'eligible_children',label:'Anak dianalisis',color:colors.pale},{key:'dose1_children',label:'Sudah D1',color:colors.blue},{key:'dose3_children',label:'Sudah D3',color:colors.teal}];
    $('content-mapreduce').innerHTML=`<div class="grid-two"><div class="panel"><h3>Jumlah anak dan penerima dosis</h3><p class="description">${samples.length} sampel dari ${d.results.length} kabupaten · kohort ${d.cohort}. Ketiga seri menggunakan satu skala jumlah anak.</p>${legend(series)}${chart(samples,series,{title:'Jumlah anak dianalisis, penerima D1 dan D3: '+samples.length+' sampel kabupaten',rowHeight:42})}${downloads('mapreduce',['reduced.tsv','results.json'])}</div><div><div class="panel"><h3>Pembagian kerja mapper</h3>${table(['Mapper','Profil dibaca','Anak terpilih'],d.mapper_input_rows.map((v,i)=>['Mapper '+(i===0?'A':'B'),number(v),number(d.mapper_output_rows[i])]))}<p class="success-line">${number(d.source_rows)} profil → ${number(d.selected_rows)} anak dianalisis → ${d.results.length} kabupaten</p></div><div class="panel" style="margin-top:18px"><h3>YARN</h3><p class="success-line">${esc(d.yarn.status)}${d.yarn.queued ? ' · mapper menunggu kapasitas' : ' · dua mapper mendapat tempat'}</p>${table(['Tugas','Tempat'],d.yarn.tasks.map(t=>[t.task,t.node]))}<p class="pale-line">Resource dilepas: ${d.yarn.resource_released ? 'ya' : 'belum'}</p></div></div></div>`;
  }
  function renderHive() {
    const d=current.stages.hive.data;
    const provinces=[...new Set(d.results.map(r=>r.province))].sort();
    if (!provinces.includes(hiveProvince)) hiveProvince='';
    const rows=d.results.filter(r=>!hiveProvince || r.province===hiveProvince);
    const selected=rows.reduce((s,r)=>({eligible:s.eligible+r.eligible_children,d1:s.d1+r.dose1_children,d3:s.d3+r.dose3_children}),{eligible:0,d1:0,d3:0});
    const both=hiveMetric==='both';
    const metricLabel=both?'Cakupan D3 dan putus lanjut':hiveMetric==='coverage_pct'?'Cakupan D3':'Putus lanjut D1 → D3';
    const sortKey=both?'coverage_pct':hiveMetric;
    const sorted=[...rows].sort((a,b)=> (a[sortKey]??-1)-(b[sortKey]??-1));
    const options=`<option value="">Semua provinsi</option>${provinces.map(p=>`<option value="${esc(p)}" ${p===hiveProvince?'selected':''}>${esc(p)}</option>`).join('')}`;
    const series=both
      ? [{key:'coverage_pct',label:'Cakupan D3',color:colors.teal},{key:'dropout_pct',label:'Putus lanjut D1 → D3',color:colors.orange}]
      : [{key:hiveMetric,label:metricLabel,color:hiveMetric==='coverage_pct'?colors.teal:colors.orange}];
    $('content-hive').innerHTML=`<div class="grid-two">
      <div class="panel">
        <h3>Perbandingan kabupaten</h3>
        <p class="description">D1 = dosis pertama; D3 = dosis ketiga. N/A berarti putus lanjut tidak bisa dihitung karena belum ada penerima D1.</p>
        <div class="controls"><label for="province-filter">Provinsi</label><select id="province-filter">${options}</select><label for="metric-filter">Ukuran</label><select id="metric-filter"><option value="coverage_pct" ${hiveMetric==='coverage_pct'?'selected':''}>Cakupan D3</option><option value="dropout_pct" ${hiveMetric==='dropout_pct'?'selected':''}>Putus lanjut</option><option value="both" ${both?'selected':''}>Keduanya</option></select></div>
        <div class="mini-stats"><div><strong>${number(selected.eligible)}</strong><span>Anak pada pilihan</span></div><div><strong>${percent(selected.eligible?100*selected.d3/selected.eligible:null)}</strong><span>Cakupan D3 pilihan</span></div><div><strong>${percent(selected.d1?100*(selected.d1-selected.d3)/selected.d1:null)}</strong><span>Putus lanjut pilihan</span></div></div>
        ${legend(series)}${chart(sorted,series,{maximum:100,percentages:true,title:metricLabel+' menurut kabupaten'})}
      </div>
      <div class="panel">
          <h3>Cakupan D3 per provinsi</h3>
          <p class="description">Seluruh provinsi dalam sesi. Jumlah anak dijumlahkan dari seluruh kabupaten di setiap provinsi.</p>
          <div class="formula"><strong>Cakupan D3 provinsi (%)</strong><span>Total penerima D3 di provinsi ÷ total anak yang memenuhi syarat di provinsi × 100%</span></div>
          ${chart(d.analysis.province,[{key:'coverage_pct',label:'Cakupan D3',color:colors.blue}],{maximum:100,percentages:true,labelKey:'province',title:'Cakupan D3 per provinsi',rowHeight:34})}
      </div>
    </div>`;
    $('province-filter').addEventListener('change',e=>{hiveProvince=e.target.value;renderHive();});
    $('metric-filter').addEventListener('change',e=>{hiveMetric=e.target.value;renderHive();});
  }
  function renderPig() {
    const stage=current.stages.pig,d=stage.data, received=d.cohort_rows-d.missed_dose3;
    const choices={dropout_d1_d3:'Sudah D1, belum D3',not_started_d1:'Belum memulai D1',missed_dose3:'Semua yang belum D3'};
    const parts=[{value:received,label:'Sudah D3',color:colors.teal,cls:'part-done'},{value:d.dropout_children,label:'Putus lanjut',color:colors.orange,cls:'part-drop'},{value:d.never_started_dose1,label:'Belum memulai D1',color:colors.red,cls:'part-none'}];
    const preview=d.preview[pigList] || [];
    $('content-pig').innerHTML=`<div class="grid-two"><div class="panel"><h3>Hasil penyaringan</h3><p class="scope">${esc(d.province ? d.province+' / '+(d.district || 'semua kabupaten') : 'Seluruh wilayah dalam sesi')}</p><div class="funnel"><div><strong>${number(d.source_rows)}</strong><span>Profil sumber</span></div><span aria-hidden="true">→</span><div><strong>${number(d.cohort_rows)}</strong><span>Kelompok terpilih</span></div><span aria-hidden="true">→</span><div><strong>${number(d.missed_dose3)}</strong><span>Belum D3</span></div></div><div class="stack-track" role="img" aria-label="${esc(parts.map(p=>p.label+': '+number(p.value)).join(', '))}">${parts.map(p=>`<div class="${p.cls}" style="width:${d.cohort_rows?100*p.value/d.cohort_rows:0}%" title="${esc(p.label+': '+number(p.value))}"></div>`).join('')}</div>${legend(parts)}${table(['Kelompok','Jumlah anak'],parts.map(p=>[p.label,number(p.value)]))}<p class="small">Belum D3 = putus lanjut + belum memulai D1. Kedua daftar tidak saling tumpang tindih.</p>${downloads('pig',['cohort.csv','missed_dose3.csv','dropout_d1_d3.csv','not_started_d1.csv'])}</div><div class="panel"><h3>Cuplikan daftar anak</h3><p class="description">Maksimal 12 baris pertama dari file hasil. Unduh CSV untuk daftar lengkap.</p><div class="controls"><label for="pig-list">Daftar</label><select id="pig-list">${Object.entries(choices).map(([key,label])=>`<option value="${key}" ${key===pigList?'selected':''}>${label}</option>`).join('')}</select></div>${preview.length?table(['ID anak','Kabupaten','D1 / D2 / D3'],preview.map(r=>[r.child_id,short(r.district),[r.dose1,r.dose2,r.dose3].join(' / ')])):'<p class="no-data">Daftar ini kosong untuk wilayah terpilih.</p>'}${preview.length?`<p class="small">Telusuri contoh ID ini di terminal:</p><code class="command">python code/demo.py hbase --child ${esc(preview[0].child_id)}</code>`:''}</div></div>`;
    $('pig-list').addEventListener('change',e=>{pigList=e.target.value;renderPig();});
  }
  function renderHbase() {
    const d=current.stages.hbase.data;
    if (!d.found) {
      $('content-hbase').innerHTML=`<div class="panel"><h3>${esc(d.child_id)} · ID tidak ditemukan</h3><p class="description">Pencarian selesai, tetapi ID ini tidak ada dalam registri.</p></div>`;
      return;
    }
    const p=d.profile;
    const dates=new Map(d.history.map(e=>[e.dose_number,e]));
    const timeline=[1,2,3].map(dose=>{
      const event=dates.get(dose);
      return `<div class="${event?'':'missing'}"><strong>DTP${dose}</strong><span>${event?esc(event.vaccination_date):p.dose3_due?'Belum diterima':'Belum ada catatan dosis'}</span><span>${event?esc(event.facility_id):p.dose3_due?'Sudah waktunya menurut data latihan':'Belum masuk penanda waktu latihan'}</span></div>`;
    }).join('');
    $('content-hbase').innerHTML=`<div class="panel"><h3>${esc(d.child_id)} · ${esc(p.district)}</h3><p class="lookup-meta">${esc(p.province)} · lahir ${esc(p.birth_date)} · ${d.history.length} catatan dosis</p><div class="timeline">${timeline}</div><p class="pale-line">Dosis yang belum diterima dan sudah waktunya: ${esc(d.missing_due_doses.join(', ') || 'tidak ada')}.</p>${downloads('hbase',['column_cells.csv','results.json'])}</div>`;
  }
  const renderers={storage:renderStorage,mapreduce:renderMapreduce,hive:renderHive,pig:renderPig,hbase:renderHbase};
  function render(snapshot) {
    const previous=current;
    current=snapshot;
    if (previous?.run?.id!==snapshot.run?.id) {hiveProvince='';hiveMetric='coverage_pct';pigList='dropout_d1_d3';}
    $('session-label').textContent=snapshot.run ? `Sesi ${snapshot.run.id} · ${snapshot.run.provinces} provinsi / ${snapshot.run.districts} kabupaten · kohort ${snapshot.run.cohort}` : snapshot.message || 'Belum ada hasil pada sesi demo baru';
    $('metric-children').textContent=ready('storage')?number(snapshot.run.children):'—';
    $('metric-events').textContent=ready('storage')?number(snapshot.run.vaccination_events):'—';
    const cohort=ready('hive')?snapshot.stages.hive.data.analysis.overall.eligible_children:ready('mapreduce')?snapshot.stages.mapreduce.data.selected_rows:null;
    $('metric-cohort').textContent=number(cohort);
    $('metric-cohort-note').textContent=cohort==null?'Menunggu penghitungan':`Kelahiran ${snapshot.run.cohort}, memenuhi syarat`;
    $('metric-coverage').textContent=ready('hive')?percent(snapshot.stages.hive.data.analysis.overall.coverage_pct):'—';
    stages.forEach(s=>{
      const status=snapshot.stages[s].status;
      $('status-'+s).textContent=status==='ready'?'Selesai':status==='waiting'?'Menunggu berkas hasil':'Belum diproses';
      $('status-'+s).classList.toggle('ready',status==='ready');
      if (!ready(s)) $('content-'+s).innerHTML=empty(s,snapshot.stages[s].message);
      else if (previous?.run?.id!==snapshot.run.id || previous.stages[s].job!==snapshot.stages[s].job || previous.stages[s].status!=='ready') renderers[s]();
    });
  }
  async function poll() {
    try {
      if (location.protocol==='file:') throw Error('Buka melalui server lokal. Jalankan python code/dashboard_server.py, lalu buka http://127.0.0.1:8765.');
      const response=await fetch('/api/dashboard',{cache:'no-store',signal:AbortSignal.timeout(5000)});
      if (!response.ok) throw Error('Server belum mengirim hasil.');
      const snapshot=await response.json();
      const next=JSON.stringify(snapshot);
      if (next!==signature) {signature=next;render(snapshot);}
      $('connection-dot').className='dot online';
      $('connection-text').textContent='Terhubung';
    } catch(error) {
      signature='';
      render({state:'error',run:null,message:location.protocol==='file:'?error.message:'Server terputus. Jalankan kembali server dashboard untuk membaca hasil.',stages:Object.fromEntries(stages.map(s=>[s,{status:'pending',data:null}]))});
      $('connection-dot').className='dot offline';
      $('connection-text').textContent='Tidak terhubung';
    }
  }
  $('refresh').addEventListener('click',()=>poll());
  stages.forEach(s=>{$('content-'+s).innerHTML=empty(s);});
  async function loop() {await poll();setTimeout(loop,1500);}
  loop();
})();
