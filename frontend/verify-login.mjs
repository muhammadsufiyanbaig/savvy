import { chromium } from 'playwright';
import { writeFileSync } from 'fs';

const SCREENSHOTS = 'C:\\Users\\I-TECH\\OneDrive\\Desktop\\Projects\\Applications\\Savvy\\frontend\\screenshots';
import { mkdirSync } from 'fs';
try { mkdirSync(SCREENSHOTS, { recursive: true }); } catch {}

const ss = (name) => `${SCREENSHOTS}\\${name}.png`;

const browser = await chromium.launch({ headless: false, slowMo: 300 });
const page = await browser.newPage();
page.setDefaultTimeout(15000);

const errors = [];
page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
page.on('pageerror', err => errors.push(`PAGEERROR: ${err.message}`));

async function shot(name) {
  await page.screenshot({ path: ss(name), fullPage: false });
  console.log(`📸 ${name}`);
}

console.log('\n=== STEP 1: Navigate to root ===');
await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
console.log(`URL after redirect: ${page.url()}`);
await shot('01-initial-redirect');

console.log('\n=== STEP 2: Login page loaded ===');
await page.waitForSelector('input[name="username"]', { timeout: 8000 });
await shot('02-login-page');
console.log('Login form visible ✓');

console.log('\n=== STEP 3: Fill credentials ===');
await page.fill('input[name="username"]', 'savvytest');
await page.fill('input[name="password"]', 'Test1234!');
await shot('03-filled-form');

console.log('\n=== STEP 4: Submit login ===');
await page.click('button[type="submit"]');

console.log('\n=== STEP 5: Wait for dashboard ===');
try {
  await page.waitForURL('**/dashboard', { timeout: 10000 });
  console.log(`Dashboard URL: ${page.url()} ✓`);
  await page.waitForLoadState('networkidle');
  await shot('04-dashboard-loaded');
} catch (e) {
  await shot('04-login-failed');
  console.log(`ERROR: Did not reach dashboard — ${e.message}`);
  console.log(`Current URL: ${page.url()}`);
  await browser.close();
  process.exit(1);
}

console.log('\n=== STEP 6: Check dashboard content ===');
// Check stat cards present
const statCards = await page.locator('.grid >> text=Monthly Expenses').count();
console.log(`Stat cards (Monthly Expenses text): ${statCards > 0 ? '✓ found' : '✗ missing'}`);

// Check sidebar
const sidebar = await page.locator('text=Savvy').first().isVisible();
console.log(`Sidebar logo: ${sidebar ? '✓ visible' : '✗ missing'}`);

// Check navbar
const navbar = await page.locator('text=Dashboard').first().isVisible();
console.log(`Navbar title: ${navbar ? '✓ visible' : '✗ missing'}`);

await shot('05-dashboard-content');

console.log('\n=== STEP 7: Test Expenses page ===');
await page.click('text=Expenses');
await page.waitForLoadState('networkidle');
await shot('06-expenses-page');
console.log(`Expenses URL: ${page.url()}`);

console.log('\n=== STEP 8: Test Budgets page ===');
await page.click('text=Budgets');
await page.waitForLoadState('networkidle');
await shot('07-budgets-page');
console.log(`Budgets URL: ${page.url()}`);

console.log('\n=== STEP 9: Test Savings page ===');
await page.click('text=Savings');
await page.waitForLoadState('networkidle');
await shot('08-savings-page');
console.log(`Savings URL: ${page.url()}`);

console.log('\n=== STEP 10: Test AI Insights page ===');
await page.click('text=AI Insights');
await page.waitForLoadState('networkidle');
await shot('09-ai-insights-page');
console.log(`AI Insights URL: ${page.url()}`);

console.log('\n=== STEP 11: Test Notifications page ===');
await page.click('text=Notifications');
await page.waitForLoadState('networkidle');
await shot('10-notifications-page');
console.log(`Notifications URL: ${page.url()}`);

console.log('\n=== STEP 12: Test Settings page ===');
await page.click('text=Settings');
await page.waitForLoadState('networkidle');
await shot('11-settings-page');
console.log(`Settings URL: ${page.url()}`);

console.log('\n=== PROBE: Try invalid login ===');
await page.click('text=Savvy'); // click logo area — may not work, try direct nav
await page.goto('http://localhost:3000/login');
await page.waitForSelector('input[name="username"]');
await page.fill('input[name="username"]', 'wronguser');
await page.fill('input[name="password"]', 'wrongpass');
await page.click('button[type="submit"]');
await page.waitForTimeout(2000);
await shot('12-invalid-login-probe');
const stillOnLogin = page.url().includes('login');
console.log(`Stays on login after bad creds: ${stillOnLogin ? '✓' : '✗ (redirected!)'}`);

// Check for error toast or error message
const toastOrError = await page.locator('[role="status"], .toast, text=Invalid').count();
console.log(`Error feedback shown: ${toastOrError > 0 ? '✓' : '⚠️ none visible'}`);

console.log('\n=== Console Errors ===');
if (errors.length === 0) {
  console.log('None ✓');
} else {
  errors.forEach(e => console.log(`  ✗ ${e}`));
}

console.log('\n=== DONE ===');
console.log(`Screenshots saved to: ${SCREENSHOTS}`);
await browser.close();
