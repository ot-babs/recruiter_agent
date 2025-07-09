const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  console.log('🚀 Starting LinkedIn authentication process...');
  
  const browser = await chromium.launchPersistentContext('./linkedin-user-data', {
    headless: false,
    channel: 'chrome',
    viewport: { width: 1920, height: 1080 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  });
  
  const page = browser.pages()[0] || await browser.newPage();
  
  console.log('📱 Navigating to LinkedIn...');
  await page.goto('https://www.linkedin.com/login');
  
  console.log('👤 Please complete the following steps:');
  console.log('   1. Login to your LinkedIn account');
  console.log('   2. Complete any 2FA if required');
  console.log('   3. Navigate to any recruiter profile page');
  console.log('   4. Press Enter in this terminal when ready...');
  
  await new Promise(resolve => {
    process.stdin.once('data', () => resolve());
  });
  
  console.log('💾 Extracting authentication data...');
  const storageState = await browser.storageState();
  
  fs.writeFileSync('linkedin_storage_state.json', JSON.stringify(storageState, null, 2));
  
  console.log('✅ Authentication data saved to linkedin_storage_state.json');
  console.log('🔒 You can now use this for authenticated scraping');
  
  await browser.close();
})();