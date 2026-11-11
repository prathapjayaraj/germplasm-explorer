import asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[2]
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  context=await browser.new_context(accept_downloads=True)
  page=await context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  html=(ROOT/'index.html').read_text()
  for name in ['app/assets/jszip.min.js','app/assets/generator.js','app/assets/explorer-template.js']:
   html=html.replace(f'<script src="{name}"></script>','<script>'+(ROOT/name).read_text()+'</script>')
  await page.set_content(html,wait_until='load')
  await page.locator('#workbook').set_input_files(str(ROOT/'germplasm.xlsx'))
  await page.wait_for_function("document.getElementById('validationBox').hidden === false || document.getElementById('status').classList.contains('bad')",timeout=50000)
  print('STATUS',await page.locator('#status').inner_text())
  print('ISSUES',await page.locator('#validationHeadline').inner_text())
  assert '118' in await page.locator('#validationHeadline').inner_text()
  assert await page.locator('#generate').is_disabled()
  checks=await page.evaluate('''async()=>{let s=await CropGermGenerator.readWorkbook(document.getElementById('workbook').files[0]);const trial=(edit)=>{let x=JSON.parse(JSON.stringify(s));edit(x);try{CropGermGenerator.assemble(x);return 'NO ERROR'}catch(e){return e.message}};const c=Object.keys(s),mc=s['Master Data'][0],gc=s['Germplasm Data'][0];return {duplicateHeader:trial(x=>x['Germplasm Data'][0][6]=x['Germplasm Data'][0][5]),unknownColumn:trial(x=>x['Germplasm Data'][0][6]='cid9999'),duplicateState:trial(x=>x['Master Data'][2][4]=x['Master Data'][1][4]),orphan:trial(x=>x['Master Data'][1][0]=''),blankCode:trial(x=>x['Master Data'][1][4]=''),baseline:CropGermGenerator.assemble(s).stats}}''')
  print('CHECKS',checks)
  for k in ['duplicateHeader','unknownColumn','duplicateState','orphan','blankCode']:assert checks[k]!='NO ERROR',(k,checks[k])
  await page.locator('#allowExclusions').check();assert not await page.locator('#generate').is_disabled()
  async with page.expect_download() as dl:await page.locator('#generate').click()
  out=ROOT/'app/tests/generated_strict_smoke.html';await (await dl.value).save_as(out)
  viewer=await context.new_page();ve=[];viewer.on('pageerror',lambda e:ve.append(str(e)))
  await viewer.set_content(out.read_text(),wait_until='load')
  await viewer.locator('[data-tab="accession"]').click()
  await viewer.locator('[data-action="reference"]').first.click()
  assert await viewer.locator('.selected-reference').count()==1
  assert await viewer.locator('.reference-traits').count()==0
  assert await viewer.locator('.selected-reference .reference-view-icon').count()==1
  await viewer.locator('.selected-reference .reference-view-icon').click()
  print('VIEWER_MODAL',await viewer.locator('#detailModal').count(),await viewer.locator('[role="dialog"]').count())
  assert not ve,ve
  assert not errors,errors
  await browser.close()
  print('SUCCESS')
asyncio.run(main())
