/* Crop Germplasm Explorer — browser-only Excel → standalone HTML generator.
   The same six-column Master Data and DUS mapping semantics as the reference Python generator.
   License: MIT (project code). JSZip is distributed with its own MIT/GPLv3 license. */
(function (global) {
  'use strict';
  const N = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main';
  const R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships';
  const norm = v => String(v ?? '').toLowerCase().replace(/[^a-z0-9]/g, '');
  const val = v => String(v ?? '').trim();
  const slug = v => val(v).toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
  function fail(s) { throw new Error(s); }
  function descendants(node, namespace, name) {return Array.from(node.getElementsByTagNameNS(namespace, name));}
  function children(node, namespace, name) {return Array.from(node.children || []).filter(x => x.namespaceURI===namespace && x.localName===name);}
  function colNumber(address) { const m=/^[A-Za-z]+/.exec(address); if(!m)return 0; return [...m[0].toUpperCase()].reduce((n,c)=>n*26+c.charCodeAt(0)-64,0)-1; }
  function parseXml(str, path) {const doc=new DOMParser().parseFromString(str,'application/xml');if(doc.getElementsByTagName('parsererror').length)fail('Invalid Excel XML: '+path);return doc;}
  function getText(node,ns,name){const e=descendants(node,ns,name)[0];return e?e.textContent:'';}
  async function readWorkbook(file) {
    if (file.size > 40 * 1024 * 1024) fail('Workbook exceeds the 40 MB browser safety limit; split the dataset or use the command-line generator');
    const zip=await JSZip.loadAsync(file);
    const entries=Object.values(zip.files);
    const unpackedBytes=entries.reduce((n,e)=>n+(Number(e._data?.uncompressedSize)||0),0);
    if(unpackedBytes>180*1024*1024)fail('Workbook expands beyond the 180 MB browser memory safety limit');
    async function xml(path){const entry=zip.file(path);if(!entry)fail('Missing Excel component: '+path);return parseXml(await entry.async('string'),path);}
    const book=await xml('xl/workbook.xml');const rels=await xml('xl/_rels/workbook.xml.rels');
    const targets=new Map(descendants(rels,'http://schemas.openxmlformats.org/package/2006/relationships','Relationship').map(r=>[r.getAttribute('Id'),r.getAttribute('Target')]));
    let strings=[];
    if(zip.file('xl/sharedStrings.xml')) {
      const shared=await xml('xl/sharedStrings.xml');
      strings=descendants(shared,N,'si').map(si=>descendants(si,N,'t').map(t=>t.textContent).join(''));
    }
    const result={};
    for(const sheet of descendants(book,N,'sheet')){
      const name=sheet.getAttribute('name');const rid=sheet.getAttributeNS(R,'id');let target=targets.get(rid);
      if(!target)fail('Missing sheet relationship: '+name);
      if(target.startsWith('/'))target=target.slice(1);
      else {let parts=['xl'];for(const x of target.split('/')){if(x==='..')parts.pop();else if(x!=='.')parts.push(x);}target=parts.join('/');}
      const doc=await xml(target);const records=[];
      for(const row of descendants(doc,N,'sheetData').flatMap(x=>children(x,N,'row'))){
        const values=new Map();
        for(const cell of children(row,N,'c')){
          const index=colNumber(cell.getAttribute('r')||'A1');const type=cell.getAttribute('t');let v='';
          if(type==='inlineStr')v=descendants(cell,N,'is').flatMap(e=>descendants(e,N,'t')).map(e=>e.textContent).join('');
          else {v=getText(cell,N,'v');if(type==='s'&&v!==''){const s=strings[Number(v)];if(s===undefined)fail('Invalid Excel shared string index');v=s;}else if(type==='b')v=v==='1'?'Yes':'No';}
          values.set(index,val(v));
        }
        if(values.size){const n=Math.max(...values.keys())+1;records.push(Array.from({length:n},(_,i)=>values.get(i)||''));}
      }
      result[name]=records;
      // Allow the browser to paint progress and respond between large worksheet parses.
      await new Promise(resolve=>setTimeout(resolve,0));
    }
    return result;
  }
  function extractRows(sheets,name,required){
    const matrix=sheets[name];if(!matrix?.length)fail(`Missing or empty sheet ${name}; expected columns: ${required.join(', ')}`);
    const headers=matrix[0];const normalized=headers.map(norm);
    for(const h of required)if(!normalized.includes(norm(h)))fail(`${name} is missing column ${h}`);
    const out=[];
    matrix.slice(1).forEach((row,i)=>{if(!row.some(x=>val(x)))return;const obj={_row:i+2};headers.forEach((h,j)=>obj[h]=val(row[j]));out.push(obj);});
    return out;
  }
  function get(row,column){const key=Object.keys(row).find(k=>norm(k)===norm(column));return key===undefined?'':val(row[key]);}
  function enabled(v){return !new Set(['no','n','0','false','off','disabled','hide']).has(val(v).toLowerCase());}
  function assemble(sheets){
    const warnings=[];
    const masters=extractRows(sheets,'Master Data',['CID','IPGRI','Descriptor','Description','Code','State']);
    if(!masters.length)fail('Master Data has no descriptors or states');
    const allMaster=new Map(),seen=new Set();
    // Allow both repeated-CID rows and grouped descriptors where subsequent
    // state rows leave CID, IPGRI, Descriptor and Description empty.
    // Inheritance is restricted to the immediately preceding descriptor group.
    let activeCid='';
    for(const row of masters){
      const explicitCid=get(row,'CID');
      const cid=explicitCid||activeCid;
      const code=get(row,'Code'),state=get(row,'State');
      if(!cid)fail(`Master Data row ${row._row}: state row has no preceding descriptor CID (orphan row)`);
      if(explicitCid)activeCid=explicitCid;
      if(!allMaster.has(cid))allMaster.set(cid,{cid,ipgri:'',name:'',description:'',options:[]});
      const item=allMaster.get(cid);
      for(const [col,k] of [['IPGRI','ipgri'],['Descriptor','name'],['Description','description']]){
        const v=get(row,col);if(v&&item[k]&&item[k]!==v)fail(`Master Data row ${row._row}: ${col} conflicts with earlier ${cid} row`);
        if(v)item[k]=v;
      }
      if(code){const key=cid+'\u0000'+code;if(seen.has(key))fail(`Duplicate Master Data state for ${cid} / ${code} (row ${row._row})`);seen.add(key);item.options.push({code,label:state||code});}
      else if(state)fail(`Master Data row ${row._row}: State without Code`);
    }
    const descriptors=Array.from(allMaster.values());
    descriptors.forEach(d=>{if(!d.name)fail(`Master Data: ${d.cid} has no descriptor name`);if(!d.options.length)warnings.push(`${d.cid} has no configured states`);});
    const byCid=new Map(descriptors.map(d=>[d.cid,d]));
    const germ=sheets['Germplasm Data'];if(!germ?.length)fail('Missing sheet Germplasm Data');
    const head=germ[0].map(norm),indexes=new Map(head.map((h,i)=>[h,i]));
    for(const col of ['ID','Accession','Name','Genome','Subgroup',...descriptors.map(d=>d.cid)])if(!indexes.has(norm(col)))fail(`Germplasm Data missing column ${col}`);
    const valid=new Map(descriptors.map(d=>[d.cid,new Set(d.options.map(o=>o.code))]));
    const records=[],invalid=new Map(),ids=new Set(),repeat=new Map();
    germ.slice(1).forEach((raw,i)=>{
      if(!raw.some(x=>val(x)))return;
      const gv=k=>val(raw[indexes.get(norm(k))]);
      const rid=gv('ID'),acc=gv('Accession'),name=gv('Name'),genome=gv('Genome'),sub=gv('Subgroup');
      if(!rid||!acc||!name)fail(`Germplasm Data row ${i+2}: ID, Accession and Name required`);
      if(ids.has(rid))fail(`Germplasm Data has duplicate internal ID: ${rid}`);ids.add(rid);
      repeat.set(acc,(repeat.get(acc)||0)+1);
      const traits=descriptors.map(d=>gv(d.cid));
      descriptors.forEach((d,j)=>{const code=traits[j];if(code&&!valid.get(d.cid).has(code)){const k=d.cid+' / '+code;invalid.set(k,(invalid.get(k)||0)+1);}});
      records.push([rid,acc,name,genome,sub,traits]);
    });
    if(!records.length)fail('Germplasm Data has no records');
    const repeated=Array.from(repeat).filter(([,n])=>n>1).map(([a])=>a);
    if(repeated.length)warnings.push(`${repeated.length} repeated accession number(s), kept as distinct records: ${repeated.slice(0,8).join(', ')}`);
    if(invalid.size){warnings.push(`${Array.from(invalid.values()).reduce((a,b)=>a+b,0)} trait values have no Master Data state mapping, excluded from similarity comparisons`);
      Array.from(invalid).sort((a,b)=>b[1]-a[1]).slice(0,8).forEach(([k,n])=>warnings.push(`  ${k}: ${n} observation(s)`));}
    const drows=extractRows(sheets,'DUS Equivalent',['DUS Descriptor','DUS Value','Germplasm Descriptor','Germplasm Value','DUS ID','DUS Code']);
    const byName=new Map();descriptors.forEach(d=>{const k=d.name.toLowerCase();byName.set(k,[...(byName.get(k)||[]),d]);});
    const byDus=new Map(),states=new Map();
    for(const row of drows){
      if(!enabled(get(row,'Enabled')))continue;
      const dname=get(row,'DUS Descriptor'),dvalue=get(row,'DUS Value');if(!dname&&!dvalue)continue;
      if(!dname||!dvalue)fail(`DUS Equivalent row ${row._row}: DUS Descriptor and DUS Value required`);
      const did=get(row,'DUS ID')||'dus_'+slug(dname),dcode=get(row,'DUS Code')||dvalue;
      let cid=get(row,'Germplasm CID'),gname=get(row,'Germplasm Descriptor'),gcode=get(row,'Germplasm Code'),glabel=get(row,'Germplasm Value'),mapped=null;
      if(cid){mapped=byCid.get(cid);if(!mapped)warnings.push(`DUS Equivalent row ${row._row}: ${cid} not found; not mapped`);}
      else if(gname){const matches=byName.get(gname.toLowerCase())||[];if(matches.length===1){mapped=matches[0];cid=mapped.cid;}else if(matches.length>1)fail(`DUS Equivalent row ${row._row}: ambiguous Germplasm Descriptor ${gname}; enter CID`);else warnings.push(`DUS Equivalent row ${row._row}: unknown Germplasm Descriptor ${gname}`);}
      if(mapped&&gname&&gname.toLowerCase()!==mapped.name.toLowerCase())warnings.push(`DUS Equivalent row ${row._row}: Germplasm Descriptor does not match CID ${cid}; CID used`);
      const matches=[];
      if(mapped&&gcode){for(const c of gcode.split(/[,;]/).map(val).filter(Boolean)){if(mapped.options.some(o=>o.code===c))matches.push(c);else warnings.push(`DUS Equivalent row ${row._row}: ${cid} code ${c} not in Master Data`);}if(glabel&&matches.length&&!mapped.options.some(o=>matches.includes(o.code)&&o.label.toLowerCase()===glabel.toLowerCase()))warnings.push(`DUS Equivalent row ${row._row}: Germplasm Value differs from code label; code used`);}
      else if(mapped&&glabel){for(const label of glabel.split('||').map(val).filter(Boolean)){const found=mapped.options.filter(o=>o.label.toLowerCase()===label.toLowerCase());if(found.length===1)matches.push(found[0].code);else if(found.length>1)fail(`DUS Equivalent row ${row._row}: ambiguous state label ${label}; enter Germplasm Code`);else warnings.push(`DUS Equivalent row ${row._row}: unknown state ${label} under ${cid}`);}}
      if(get(row,'Mapping Status')&&!['approved','verified'].includes(get(row,'Mapping Status').toLowerCase()))matches.length=0;
      if(!byDus.has(did))byDus.set(did,{id:did,name:dname,cid:mapped?cid:'',notes:'',states:[]});
      const item=byDus.get(did);if(item.name!==dname)fail(`DUS Equivalent row ${row._row}: DUS ID ${did} has inconsistent names`);
      if(mapped){if(item.cid&&item.cid!==cid)fail(`DUS Equivalent row ${row._row}: one DUS Descriptor must map to one Germplasm Descriptor`);item.cid=cid;}
      let note=get(row,'Notes');if(glabel&&!matches.length)note+=' Candidate NRCB value: '+glabel;
      const key=did+'\u0000'+dcode;
      if(!states.has(key)){const s={code:dcode,label:dvalue,codes:[],notes:note};states.set(key,s);item.states.push(s);}
      const s=states.get(key);if(s.label!==dvalue)fail(`DUS Equivalent row ${row._row}: DUS Code ${dcode} has inconsistent states`);
      matches.forEach(c=>{if(!s.codes.includes(c))s.codes.push(c);});if(note&&!s.notes)s.notes=note;
    }
    const dus=Array.from(byDus.values());
    if(dus.length&&!dus.some(d=>d.states.some(s=>s.codes.length)))warnings.push('DUS characteristics are visible, but no state-level mappings are approved; DUS filtering is disabled until verified codes are entered');
    const config={};for(const row of extractRows(sheets,'Configurations',['Setting','Value','Description'])){const k=norm(get(row,'Setting'));if(k)config[k]=get(row,'Value');}
    function posInt(k,def,cap){const v=Number(config[k]||def);if(!Number.isFinite(v))fail(`Configurations: ${k} must be a number`);return Math.max(1,Math.min(cap,Math.trunc(v)));}
    const data={title:config.title||'Banana Germplasm Explorer',subtitle:config.subtitle||'Explore, filter and compare morphological characteristics of banana germplasm.',source:config.datasource||'Germplasm descriptors',footer:config.footernote||'Data-driven, read-only explorer · Edit the workbook and regenerate',defaultMode:['traits','accession','dus'].includes(config.defaultmode)?config.defaultmode:'accession',maxClosest:posInt('maxclosestresults',20,200),pageSize:posInt('resultpagesize',25,100),descriptors,records,dus};
    if(data.defaultMode==='dus'&&!dus.length)data.defaultMode='accession';
    return {data,warnings,stats:{accessions:records.length,descriptors:descriptors.length,states:descriptors.reduce((n,d)=>n+d.options.length,0),dus:dus.length,mappedDusStates:dus.reduce((n,d)=>n+d.states.filter(s=>s.codes.length).length,0)}};
  }
  function produceHtml(template,data){
    const placeholder='__EMBEDDED_DATA__';if(template.split(placeholder).length!==2)fail('The explorer template must contain one embedded data placeholder');
    const payload=JSON.stringify(data).replace(/</g,'\\u003c').replace(/>/g,'\\u003e').replace(/&/g,'\\u0026').replace(/\u2028/g,'\\u2028').replace(/\u2029/g,'\\u2029');
    return template.replace(placeholder,payload);
  }
  global.CropGermGenerator={readWorkbook,assemble,produceHtml};
})(window);
