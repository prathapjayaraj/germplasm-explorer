"""Browser regression: grouped and repeated CIDs produce identical output."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        page = await browser.new_page(accept_downloads=True)
        errors=[]
        page.on('pageerror', lambda e: errors.append(str(e)))
        html=(ROOT/'index.html').read_text()
        for name in ['app/assets/jszip.min.js','app/assets/generator.js','app/assets/explorer-template.js']:
            html=html.replace(f'<script src="{name}"></script>', '<script>'+(ROOT/name).read_text()+'</script>')
        await page.set_content(html, wait_until='load')
        await page.locator('#workbook').set_input_files(str(ROOT/'germplasm.xlsx'))
        await page.wait_for_function("!document.querySelector('#generate').disabled || document.querySelector('#status').classList.contains('bad')", timeout=50000)
        assert not await page.locator('#generate').is_disabled(), await page.locator('#status').inner_text()
        results=await page.evaluate('''async () => {
            const original=await CropGermGenerator.readWorkbook(document.querySelector('#workbook').files[0]);
            const baseline=CropGermGenerator.assemble(original);
            const clone=JSON.parse(JSON.stringify(original));
            const idx=clone['Master Data'][0].findIndex(h=>h.toLowerCase()==='cid');
            let count=0,last='';
            for (let i=1;i<clone['Master Data'].length;i++) {
                let row=clone['Master Data'][i],cid=String(row[idx]||'').trim();
                if (cid && cid===last) {row[idx]='';count++;}
                else if (cid) last=cid;
            }
            const grouped=CropGermGenerator.assemble(clone);
            const identical=JSON.stringify(baseline.data)===JSON.stringify(grouped.data);
            // Invalid orphan state row should fail with a clear error.
            const orphan=JSON.parse(JSON.stringify(clone));orphan['Master Data'][1][idx]='';
            let orphanError='';try { CropGermGenerator.assemble(orphan); } catch(e) { orphanError=e.message; }
            // Conflicting nonempty descriptor text must not be silently inherited.
            const conflict=JSON.parse(JSON.stringify(clone));
            const descIdx=conflict['Master Data'][0].findIndex(h=>h.toLowerCase()==='descriptor');
            conflict['Master Data'][2][descIdx]='Different descriptor';
            let conflictError='';try { CropGermGenerator.assemble(conflict); } catch(e) { conflictError=e.message; }
            // Duplicate state code under the same CID should fail.
            const dup=JSON.parse(JSON.stringify(clone));
            const codeIdx=dup['Master Data'][0].findIndex(h=>h.toLowerCase()==='code');
            dup['Master Data'][2][codeIdx]=dup['Master Data'][1][codeIdx];
            let duplicateError='';try { CropGermGenerator.assemble(dup); } catch(e) { duplicateError=e.message; }
            return {identical, blankedCids:count,baseline:baseline.stats,grouped:grouped.stats,orphanError,conflictError,duplicateError};
        }''')
        print(results)
        assert results['identical'], 'Grouped and repeated CID dataset differ'
        assert results['blankedCids'] > 400
        assert 'orphan' in results['orphanError'].lower()
        assert 'conflict' in results['conflictError'].lower()
        assert 'duplicate' in results['duplicateError'].lower()
        assert results['baseline']==results['grouped']
        assert not errors,errors
        async with page.expect_download() as download_info:
            await page.locator('#generate').click()
        download=await download_info.value
        path=ROOT/'app/tests/generated_smoke.html'
        await download.save_as(path)
        assert '__EMBEDDED_DATA__' not in path.read_text()
        print('PASS: grouped and repeated CID parity, validation, browser download')
        await browser.close()

if __name__=='__main__': asyncio.run(main())
