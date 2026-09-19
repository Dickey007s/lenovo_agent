import { expect, test } from '@playwright/test';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const root = path.resolve(process.cwd(), '../../docs/reports/copilot-boundary-design-20260911');
const url = pathToFileURL(path.join(root,'index.html')).href;
const viewports = [{width:1440,height:1000},{width:390,height:844}];
for(const viewport of viewports) {
  test(`boundary design: scoped consent and independent states at ${viewport.width}px`, async ({page,context}) => {
    const errors:string[] = [], requests:string[] = [];
    page.on('pageerror',e=>errors.push(e.message));
    page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
    page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url());});
    await context.setOffline(true);
    await page.setViewportSize(viewport);
    await page.goto(url);
    const selectCase = async(id:string)=>{
      const picker=page.locator('#case-picker');
      if(await picker.isVisible()) await picker.selectOption(id);
      else await page.locator(`[data-case=${id}]`).click();
    };
    const noOverflow = async()=>expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
    const capture = async(name:string)=> {if(process.env.CAPTURE_BOUNDARY_SCREENSHOTS==='1')await page.screenshot({path:path.join(root,'screenshots',`${name}-${viewport.width}.png`),fullPage:true});};
    await expect(page.getByRole('heading',{name:'人机共驾 · 动态边界',exact:true})).toBeVisible();
    await expect(page.locator('[data-case]')).toHaveCount(8);
    await expect(page.locator('[data-action=approve]')).toBeDisabled();
    await expect(page.locator('#attempts')).toHaveText('0');
    await noOverflow(); await capture('workbench');
    await page.locator('#ack').check();
    await page.locator('[data-action=approve]').click();
    await expect(page.locator('#decision-title')).toHaveText('已确认，但还没有发送');
    await expect(page.locator('#outcome-summary')).toContainText('尚未发送');
    await expect(page.locator('#decision-title')).toBeFocused();
    await expect(page.locator('#attempts')).toHaveText('0');
    await page.locator('#perturbations>summary').click();
    await page.locator('[data-change=file]').click();
    await expect(page.locator('#decision-title')).toHaveText('这次发送需要重新确认');
    await expect(page.locator('#scope-change')).toContainText('项目周报 v2.pdf');
    await expect(page.locator('#scope-change')).toContainText('项目周报 v3.pdf');
    await expect(page.locator('#ack')).not.toBeChecked();
    await expect(page.locator('[data-action=approve]')).toBeDisabled();
    await page.locator('#ack').check(); await page.locator('[data-action=approve]').click();
    await page.locator('[data-change=recipient]').click();
    await page.locator('[data-change=recipient]').click();
    await expect(page.locator('#decision-title')).toHaveText('这次发送需要重新确认');
    await expect(page.locator('#decision-text')).toContainText('改回原值');
    await expect(page.locator('[data-action=approve]')).toBeDisabled();
    await page.locator('#ack').check(); await page.locator('[data-action=approve]').click();
    await page.locator('#fail-next').check(); await page.locator('[data-action=execute]').click();
    await expect(page.locator('#decision-title')).toHaveText('不确定是否发送成功');
    await expect(page.locator('[data-action=execute]')).toBeDisabled();
    await expect(page.locator('#attempts')).toHaveText('1'); await capture('unknown');
    for(const result of ['unavailable','not_found']) {
      await page.locator('#query-result').selectOption(result);
      await page.locator('[data-action=reconcile]').click();
      await expect(page.locator('#decision-title')).toHaveText('不确定是否发送成功');
      await expect(page.locator('#attempts')).toHaveText('1');
      await expect(page.locator('#notice')).not.toBeEmpty();
      await expect(page.locator('[data-action=execute]')).toBeDisabled();
    }
    await page.locator('#query-result').selectOption('confirmed');
    await page.locator('[data-action=reconcile]').click();
    await expect(page.locator('#attempts')).toHaveText('1');
    await expect(page.locator('#decision-title')).toHaveText('演示发送成功');
    await expect(page.locator('#preview')).not.toContainText('没有收到可靠回执');
    await selectCase('evidence');
    if(viewport.width>700) await expect(page.locator('[data-case=evidence]')).toBeFocused();
    else await expect(page.locator('#case-picker')).toBeFocused();
    await expect(page.getByRole('radio',{checked:true})).toHaveCount(0);
    await expect(page.locator('[data-action=resolve]')).toBeDisabled();
    await page.getByRole('radio').nth(1).check(); await page.locator('[data-action=resolve]').click();
    await expect(page.locator('#preview')).toContainText('引导后样本');
    await expect(page.locator('#preview')).toContainText('92%（46/50）');
    await expect(page.locator('#boundary-facts')).toContainText('本例不申请发送权限');
    await expect(page.locator('#outcome-summary')).toContainText('项目周报 v3.pdf');
    await expect(page.locator('#preserved-copy')).toContainText('历史 v2');
    await expect(page.locator('#attempts')).toHaveText('0');
    await selectCase('forbidden');
    await expect(page.locator('[data-action=approve]')).toHaveCount(0);
    await page.locator('[data-action=fallback]').click();
    await expect(page.locator('#decision-title')).toHaveText('内部草稿已保留，仍不能发送');
    await expect(page.locator('#preview')).toContainText('未删除草稿中的折扣承诺');
    await selectCase('takeover');
    await page.locator('[data-action=return]').click();
    await expect(page.locator('#decision-title')).toHaveText('发送前，请核对附件和收件人');
    await expect(page.locator('.lane .done')).toHaveCount(2);
    await page.locator('[data-action=defer]').click();
    await expect(page.locator('#decision-title')).toHaveText('已留待稍后决定');
    await page.locator('[data-action=reopen]').click();
    await expect(page.locator('[data-action=approve]')).toBeDisabled();
    await page.locator('#tab-workbench').press('ArrowRight');
    await expect(page.locator('#tab-research')).toHaveAttribute('aria-selected','true');
    await expect(page.locator('.source-row')).toHaveCount(8);
    await expect(page.locator('.followup-source')).toHaveCount(9);
    await expect(page.locator('#followup-count')).toHaveText('9 项资料');
    await page.locator('#followup-filter').selectOption('paper');
    await expect(page.locator('.followup-source')).toHaveCount(6);
    await page.locator('#followup-search').fill('MAGENTIC-UI');
    await expect(page.locator('#followup-empty')).toBeVisible();
    await page.locator('#followup-filter').selectOption('official');
    await expect(page.locator('.followup-source')).toHaveCount(1);
    await page.locator('.followup-source summary').click();
    await expect(page.locator('.followup-source')).toContainText('模拟用户');
    await expect(page.locator('.followup-source')).toContainText('项目推论 · 待验证');
    await page.locator('#followup-search').fill('');
    await expect(page.locator('.followup-source')).toHaveCount(3);
    await page.locator('#followup-filter').selectOption('all');
    await expect(page.locator('.followup-source')).toHaveCount(9);
    await expect(page.locator('#attempts')).toHaveText('0');
    await expect(page.locator('.counterevidence')).toContainText('未带来更强');
    await noOverflow(); await capture('research');
    await page.locator('#tab-research').press('ArrowRight');
    await expect(page.locator('#tab-tests')).toHaveAttribute('aria-selected','true');
    await expect(page.locator('.test-row')).toHaveCount(8); await noOverflow(); await capture('cases');
    await expect(page.locator('.comprehension-row')).toHaveCount(5);
    await expect(page.locator('.test-status')).toContainText('目标用户理解测试：未开展');
    await page.locator('[data-try=expired]').click();
    await expect(page.locator('#decision-title')).toHaveText('这次发送需要重新确认');
    await expect(page.locator('#tab-workbench')).toBeFocused();
    expect(errors).toEqual([]); expect(requests).toEqual([]);
  });
}

test('all boundary cases fit at 1280px and 640px layout width (not browser zoom)',async({page})=>{
  await page.goto(url);
  for(const width of [1280,640]) {
    await page.setViewportSize({width,height:900});
    for(const id of ['send','draft','evidence','forbidden','changed','expired','unknown','takeover']) {
      if(width<=700) await page.locator('#case-picker').selectOption(id);
      else await page.locator(`[data-case=${id}]`).click();
      expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
      const textOverflow = await page.locator('button,h1,h2,h3,.candidate,dd').evaluateAll(elements=>elements.filter(el=>el.getClientRects().length && el.scrollWidth>el.clientWidth+2).map(el=>el.textContent));
      expect(textOverflow).toEqual([]);
    }
  }
});
