import asyncio, re, json, subprocess, time
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[2]
async def main():
    proc=subprocess.Popen(['python','-m','http.server','8766','--bind','127.0.0.1'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        await asyncio.sleep(.7)
        async with async_playwright() as p:
            browser=await p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
            context=await browser.new_context(accept_downloads=True)
            page=await context.new_page()
            errors=[]
            page.on('pageerror',lambda e: errors.append(str(e)))
            html=(ROOT/'index.html').read_text()
            for name in ['app/assets/jszip.min.js','app/assets/generator.js','app/assets/explorer-template.js']:
                html=html.replace('<script src="'+name+'"></script>', '<script>'+ (ROOT/name).read_text() + '</script>')
            await page.set_content(html,wait_until='load')
            await page.locator('#workbook').set_input_files(str(ROOT/'germplasm.xlsx'))
            await page.wait_for_function("!document.querySelector('#generate').disabled || document.querySelector('#status').classList.contains('bad')",timeout=50000)
            status=await page.locator('#status').inner_text()
            print('STATUS:',status)
            print('STATS:',[await page.locator('#'+x).inner_text() for x in ['sAccessions','sDescriptors','sStates','sDUS']])
            print('ERRORS:',errors)
            assert not errors, errors
            assert not await page.locator('#generate').is_disabled(),status
            assert '589' in await page.locator('#sAccessions').inner_text()
            assert '132' in await page.locator('#sDescriptors').inner_text()
            async with page.expect_download() as download_info:
                await page.locator('#generate').click()
            download=await download_info.value
            out=ROOT/'app'/'tests'/'generated_smoke.html'
            await download.save_as(out)
            content=out.read_text()
            assert '__EMBEDDED_DATA__' not in content
            assert len(content)>200000
            print('GENERATED',out,len(content))
            # Load generated explorer in a new browser page via local server
            viewer=await context.new_page()
            view_errors=[]
            viewer.on('pageerror',lambda e: view_errors.append(str(e)))
            await viewer.set_content(content,wait_until='load')
            await viewer.wait_for_timeout(700)
            assert not view_errors,view_errors
            assert await viewer.evaluate('DATA.records.length')==589
            assert await viewer.evaluate('DATA.descriptors.length')==132
            assert await viewer.evaluate('DATA.dus.length')==41
            print('EXPLORER OK')
            await page.screenshot(path=str(ROOT/'app'/'tests'/'generator_preview.png'),full_page=True)
            await browser.close()
    finally:proc.terminate();proc.wait()
if __name__=='__main__': asyncio.run(main())
