"""Headless Chromium performance smoke test; metrics vary by environment."""
import asyncio, json, statistics, time
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[2]
async def stats(page,client):
    await client.send('HeapProfiler.collectGarbage')
    return (await client.send('Runtime.getHeapUsage'))['usedSize']

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--js-flags=--expose-gc'])
        context=await browser.new_context(accept_downloads=True)
        page=await context.new_page()
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        html=(ROOT/'index.html').read_text()
        for name in ['app/assets/jszip.min.js','app/assets/generator.js','app/assets/explorer-template.js']:
            html=html.replace('<script src="'+name+'"></script>','<script>'+(ROOT/name).read_text()+'</script>')
        await page.set_content(html,wait_until='load')
        cdp=await context.new_cdp_session(page)
        await cdp.send('HeapProfiler.enable')
        loads=[]
        for i in range(4):
            started=time.perf_counter()
            await page.locator('#workbook').set_input_files([])
            await page.locator('#workbook').set_input_files(str(ROOT/'germplasm.xlsx'))
            await page.wait_for_function("!document.querySelector('#generate').disabled || document.querySelector('#status').classList.contains('bad')",timeout=30000)
            assert not await page.locator('#generate').is_disabled(),await page.locator('#status').inner_text()
            loads.append((time.perf_counter()-started)*1000)
            await page.locator('#viewMappings').click()
            await page.locator('#mappingSearch').fill('leaf')
            await page.wait_for_timeout(160)
            assert await page.locator('#mappingList .mapitem').count()>0
            await page.locator('#closeMapping').click()
        gen_heap=await stats(page,cdp)
        async with page.expect_download() as download_info:
            await page.locator('#generate').click()
        download=await download_info.value
        out=ROOT/'app/tests/generated_smoke.html';await download.save_as(out)
        viewer=await context.new_page();viewer_errors=[];viewer.on('pageerror',lambda e:viewer_errors.append(str(e)))
        await viewer.set_content(out.read_text(),wait_until='load')
        vcdp=await context.new_cdp_session(viewer);await vcdp.send('HeapProfiler.enable')
        start_heap=await stats(viewer,vcdp)
        # Accession selection, similarity rerender and profile modal should not retain detached DOM.
        cycles=[]
        await viewer.locator('[data-action="tab"][data-tab="accession"]').click()
        for i in range(16):
            t=time.perf_counter()
            accession=viewer.locator('#accessionSearch')
            await accession.fill('')
            await accession.fill('600' if i%2 else '1')
            await viewer.wait_for_timeout(130)
            buttons=viewer.locator('[data-action="reference"]')
            if await buttons.count():
                await buttons.first.click()
                detail=viewer.locator('[data-action="detail"]')
                if await detail.count():
                    await detail.first.click()
                    if await viewer.locator('#modalBackdrop').is_visible():
                        await viewer.locator('[data-action="close-modal"]').first.click()
            cycles.append((time.perf_counter()-t)*1000)
        after_heap=await stats(viewer,vcdp)
        await viewer.locator('[data-action="tab"][data-tab="dus"]').click()
        for i in range(12):
            await viewer.locator('#dusSearch').fill('fruit' if i%2 else 'leaf')
            await viewer.wait_for_timeout(115)
        final_heap=await stats(viewer,vcdp)
        assert not errors and not viewer_errors,(errors,viewer_errors)
        print(json.dumps({'generator_load_ms':{'median':round(statistics.median(loads),1),'samples':[round(v,1) for v in loads]},'generator_heap_after_4_loads_mb':round(gen_heap/1048576,2),'explorer_heap_mb':{'initial':round(start_heap/1048576,2),'after_16_selection_cycles':round(after_heap/1048576,2),'after_12_searches':round(final_heap/1048576,2)},'interaction_cycle_ms':{'median':round(statistics.median(cycles),1),'max':round(max(cycles),1)},'page_errors':errors+viewer_errors},indent=2))
        await browser.close()
if __name__=='__main__':asyncio.run(main())
