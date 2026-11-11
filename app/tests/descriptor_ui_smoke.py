import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[2]
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  context=await browser.new_context(accept_downloads=True)
  gen=await context.new_page();ge=[];gen.on('pageerror',lambda e:ge.append(str(e)))
  html=(ROOT/'index.html').read_text()
  for name in ['app/assets/jszip.min.js','app/assets/generator.js','app/assets/explorer-template.js']:
   html=html.replace(f'<script src="{name}"></script>','<script>'+(ROOT/name).read_text()+'</script>')
  await gen.set_content(html)
  assert await gen.locator('.brand').inner_text() == 'Germplasm Descriptor\nExcel to HTML generator'
  await gen.locator('#workbook').set_input_files(str(ROOT/'germplasm.xlsx'))
  await gen.wait_for_function("document.getElementById('validationBox').hidden === false")
  await gen.locator('#allowExclusions').check()
  async with gen.expect_download() as dl: await gen.locator('#generate').click()
  assert (await dl.value).suggested_filename=='germplasm_descriptor.html'
  out=ROOT/'app/tests/generated_descriptor_smoke.html';await (await dl.value).save_as(out)
  viewer=await context.new_page();ve=[];viewer.on('pageerror',lambda e:ve.append(str(e)))
  await viewer.set_content(out.read_text(),wait_until='load')
  assert await viewer.locator('#appTitle').inner_text()=='Germplasm Descriptor'
  await viewer.locator('[data-tab="dus"]').click()
  assert await viewer.locator('[data-action="open-dus-mappings"]').count()==1
  assert await viewer.locator('.dus-map-toggle').count()==0
  await viewer.locator('[data-action="open-dus-mappings"]').click()
  assert await viewer.locator('#dusMappingBackdrop').is_visible()
  assert await viewer.locator('.map-group').count()>0
  await viewer.locator('#dusMappingSearch').fill('leaf')
  assert await viewer.locator('.map-group').count()>0
  await viewer.locator('[data-action="close-dus-mappings"]').click()
  assert await viewer.locator('#dusMappingBackdrop').is_hidden()
  await viewer.locator('#resultList .result .icon-btn').first.click()
  assert await viewer.locator('#modalBackdrop').is_visible()
  assert await viewer.locator('#resultList .result [data-action="detail"]').first.inner_text()==''
  assert not ge,ge
  assert not ve,ve
  print('PASS: title from Excel, mapping viewer, single mapping button, compact result icon, accession popup; page errors: 0')
  await browser.close()
asyncio.run(main())
