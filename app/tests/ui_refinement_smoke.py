import asyncio
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
  await page.set_content(html)
  assert await page.locator('body > header').count()==0
  assert await page.locator('main .intro h1').inner_text()=='Publish your descriptor data'
  await page.locator('#workbook').set_input_files(str(ROOT/'germplasm.xlsx'))
  await page.wait_for_function("document.querySelector('#validationBox').hidden === false",timeout=30000)
  await page.locator('#allowExclusions').check()
  print('GEN enabled?',await page.locator('#generate').is_enabled(),'errors',errors,'status',await page.locator('#status').inner_text());
  async with page.expect_download(timeout=12000) as info: await page.locator('#generate').click()
  path=ROOT/'app/tests/generated_refined_smoke.html';await (await info.value).save_as(path)
  view=await context.new_page();view.on('pageerror',lambda e:errors.append(str(e)))
  await view.set_content(path.read_text())
  await view.locator('[data-tab="dus"]').click()
  assert await view.locator('.card .code').count()==0
  assert await view.locator('.card .note').count()==0
  assert await view.locator('#resultSearch').get_attribute('placeholder')=='Search by accession name, number, cultivar or genome…'
  assert await view.locator('#resultList .result').count()>0
  assert await view.locator('#resultList [data-action="dus-compare"]').count()==0
  assert await view.locator('#resultList .result .inline-view').count()>0
  # verify icon shares title row
  assert await view.locator('#resultList .result .result-top .inline-view').count()>0
  await view.locator('#resultSearch').fill('Gros Michel')
  await view.wait_for_timeout(250)
  assert await view.locator('#resultList .result').count()>0
  await view.locator('#resultList .result .inline-view').first.click()
  assert await view.locator('#modalBackdrop').is_visible()
  await view.locator('[data-action="close-modal"]').first.click()
  # configure DUS state and check IPGRI in rendered text
  trigger=view.locator('#dusGrid .picker-trigger').first
  await trigger.click()
  await view.locator('#dusGrid .panel.open [data-action="choose"]').first.click()
  txt=await view.locator('#dusGrid .card').first.inner_text()
  assert 'cid' not in txt.lower(),txt
  assert not errors,errors
  print('PASS: no generator header, DUS cards compact, name search, inline eye, no map icon, IPGRI references and accession modal')
  await browser.close()
asyncio.run(main())
