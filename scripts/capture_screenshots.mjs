import { chromium } from "playwright";

const baseUrl = process.env.INVOICEFLOW_BASE_URL || "http://127.0.0.1:8000";
const outputDir = new URL("../docs/screenshots/", import.meta.url);

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({
  viewport: { width: 1440, height: 1050 },
  deviceScaleFactor: 1,
});

async function save(name) {
  await page.screenshot({
    path: new URL(name, outputDir).pathname,
    fullPage: true,
  });
}

async function runSample(sampleId) {
  await page.evaluate((id) => {
    const button = document.querySelector(`[data-run-sample="${id}"]`);
    if (button) {
      button.scrollIntoView({ block: "center" });
    }
  }, sampleId);
  await page.click(`[data-run-sample="${sampleId}"]`);
  await page.waitForFunction(() => document.body.classList.contains("case-selected"), {
    timeout: 12000,
  });
  await page.waitForTimeout(700);
}

await page.goto(`${baseUrl}/ui`, { waitUntil: "networkidle" });
await save("console-overview.png");

await runSample("ap_002_missing_po");
await save("ap-missing-po-result.png");
await save("ap-result.png");

await page.click('[data-tab-target="inspect"]');
await page.waitForTimeout(500);
await save("evidence-panel.png");

await page.click('[data-tab-target="review"]');
await page.waitForTimeout(500);
await save("human-review-queue.png");

await page.setViewportSize({ width: 390, height: 920 });
await page.waitForTimeout(500);
await save("mobile-review-queue.png");
await page.setViewportSize({ width: 1440, height: 1050 });
await page.waitForTimeout(300);

await page.click('[data-tab-target="evaluation"]');
await page.waitForTimeout(500);
await save("eval-dashboard.png");

await page.click('.site-header .header-tab[href="#capture"]');
await page.waitForTimeout(500);
await runSample("ar_003_payment_claim_no_proof");
await save("ar-follow-up.png");

await browser.close();
