import { chromium } from 'playwright';
import { mkdirSync } from 'fs';

const SCREENSHOTS = 'C:\\Users\\I-TECH\\OneDrive\\Desktop\\Projects\\Applications\\Savvy\\frontend\\screenshots';
try { mkdirSync(SCREENSHOTS, { recursive: true }); } catch {}
const ss = (name) => `${SCREENSHOTS}\\${name}.png`;

const browser = await chromium.launch({ headless: false, slowMo: 500 });
const page = await browser.newPage();
page.setDefaultTimeout(12000);

// Capture ALL console
page.on('console', msg => console.log(`[${msg.type().toUpperCase()}] ${msg.text()}`));
page.on('pageerror', err => console.log(`[PAGEERROR] ${err.message}`));

// Capture network requests/responses
page.on('request', req => {
  if (req.url().includes('localhost:8000') || req.url().includes('localhost:3000/api')) {
    console.log(`→ ${req.method()} ${req.url()}`);
  }
});
page.on('response', resp => {
  if (resp.url().includes('localhost:8000') || resp.url().includes('localhost:3000/api')) {
    console.log(`← ${resp.status()} ${resp.url()}`);
  }
});

console.log('Navigating to login...');
await page.goto('http://localhost:3000/login', { waitUntil: 'domcontentloaded' });
await page.screenshot({ path: ss('d1-login') });

await page.waitForSelector('input[name="username"]', { timeout: 8000 });
console.log('Filling credentials...');
await page.fill('input[name="username"]', 'savvytest');
await page.fill('input[name="password"]', 'Test1234!');
await page.screenshot({ path: ss('d2-filled') });

console.log('Clicking submit...');
await page.click('button[type="submit"]');

// Wait 6 seconds and capture whatever state we're in
await page.waitForTimeout(6000);
console.log(`URL after submit: ${page.url()}`);
await page.screenshot({ path: ss('d3-after-submit') });

// Check for any error text on page
const bodyText = await page.locator('body').innerText();
const errorLine = bodyText.split('\n').find(l => l.toLowerCase().includes('error') || l.toLowerCase().includes('invalid') || l.toLowerCase().includes('fail'));
if (errorLine) console.log(`[PAGE TEXT ERROR] ${errorLine.trim()}`);

// Check toast container
const toasts = await page.locator('[role="status"]').allInnerTexts();
if (toasts.length) console.log(`[TOAST] ${toasts.join(' | ')}`);

await browser.close();
console.log('Done');
