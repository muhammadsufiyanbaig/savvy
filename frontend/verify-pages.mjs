import { chromium } from 'playwright';
import { mkdirSync } from 'fs';

const SS = 'C:\\Users\\I-TECH\\OneDrive\\Desktop\\Projects\\Applications\\Savvy\\frontend\\screenshots';
try { mkdirSync(SS, { recursive: true }); } catch {}
const shot = async (page, name) => { await page.screenshot({ path: `${SS}\\${name}.png` }); console.log(`📸 ${name}`); };

const browser = await chromium.launch({ headless: false, slowMo: 200 });
const page = await browser.newPage();
page.setDefaultTimeout(12000);

const apiErrors = [];
page.on('response', resp => {
  const url = resp.url();
  if (url.includes('localhost:8000') && resp.status() >= 400) {
    apiErrors.push(`${resp.status()} ${url}`);
  }
});

// Login first
await page.goto('http://localhost:3000/login', { waitUntil: 'domcontentloaded' });
await page.fill('input[name="username"]', 'savvytest');
await page.fill('input[name="password"]', 'Test1234!');
await page.click('button[type="submit"]');
await page.waitForURL('**/dashboard', { timeout: 10000 });
console.log('✅ Login → Dashboard');

// Test each page by clicking sidebar links (use role=link and href)
const pages = [
  { href: '/expenses', label: 'Expenses', screenshot: 'pg-expenses' },
  { href: '/budgets', label: 'Budgets', screenshot: 'pg-budgets' },
  { href: '/savings', label: 'Savings', screenshot: 'pg-savings' },
  { href: '/banks', label: 'Banks', screenshot: 'pg-banks' },
  { href: '/ai-recommendations', label: 'AI Insights', screenshot: 'pg-ai' },
  { href: '/notifications', label: 'Notifications', screenshot: 'pg-notifications' },
  { href: '/settings', label: 'Settings', screenshot: 'pg-settings' },
];

for (const p of pages) {
  // Use sidebar link by href attribute
  await page.click(`a[href="${p.href}"]`);
  await page.waitForLoadState('networkidle');
  const url = page.url();
  const ok = url.endsWith(p.href);
  console.log(`${ok ? '✅' : '❌'} ${p.label}: ${url}`);
  await shot(page, p.screenshot);
}

// Probe: Try adding an expense
await page.click('a[href="/expenses"]');
await page.waitForLoadState('networkidle');
await page.click('button:has-text("Add Expense")');
await page.waitForTimeout(500);
await shot(page, 'probe-add-expense-form');
const formVisible = await page.locator('text=New Expense').isVisible().catch(() => false);
console.log(`🔍 Add Expense form opens: ${formVisible ? '✓' : '✗'}`);

// Fill and submit expense
if (formVisible) {
  await page.fill('input[placeholder="0.00"]', '25.50');
  // Select Food category
  await page.selectOption('select', 'Food');
  await page.fill('input[placeholder="Coffee, groceries..."]', 'Test coffee');
  await shot(page, 'probe-expense-filled');
  await page.click('button:has-text("Add Expense"):not([icon])');
  await page.waitForTimeout(2000);
  await shot(page, 'probe-expense-after-submit');
  const toast = await page.locator('text=Expense added').isVisible().catch(() => false);
  console.log(`🔍 Expense submit toast: ${toast ? '✓' : '✗ (no toast)'}`);
}

// Probe: Create a savings goal
await page.click('a[href="/savings"]');
await page.waitForLoadState('networkidle');
await page.click('button:has-text("New Goal")');
await page.waitForTimeout(500);
const goalForm = await page.locator('text=Create Savings Goal').isVisible().catch(() => false);
console.log(`🔍 Savings goal form opens: ${goalForm ? '✓' : '✗'}`);

console.log('\n=== API Errors During Test ===');
if (apiErrors.length === 0) console.log('None ✓');
else apiErrors.forEach(e => console.log(`  ✗ ${e}`));

await shot(page, 'final-state');
await browser.close();
console.log('\nDone. Screenshots:', SS);
