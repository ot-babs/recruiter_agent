const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  console.log('🚀 Starting LinkedIn authentication process...');
  
  // Launch browser with user data persistence
  const browser = await chromium.launchPersistentContext('./linkedin-user-data', {
    headless: false,
    channel: 'chrome', // Use system Chrome for better compatibility
    viewport: { width: 1920, height: 1080 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  });
  
  const page = browser.pages()[0] || await browser.newPage();
  
  // Navigate to LinkedIn
  console.log('📱 Navigating to LinkedIn...');
  await page.goto('https://www.linkedin.com/login');
  
  // Wait for user to login manually
  console.log('👤 Please complete the following steps:');
  console.log('   1. Login to your LinkedIn account');
  console.log('   2. Complete any 2FA if required');
  console.log('   3. Navigate to any recruiter profile page');
  console.log('   4. Press Enter in this terminal when ready...');
  
  // Pause for manual login
  await new Promise(resolve => {
    process.stdin.once('data', () => resolve());
  });
  
  // Extract storage state
  console.log('💾 Extracting authentication data...');
  const storageState = await browser.storageState();
  
  // Save to file
  fs.writeFileSync('linkedin_storage_state.json', JSON.stringify(storageState, null, 2));
  
  console.log('✅ Authentication data saved to linkedin_storage_state.json');
  console.log('🔒 You can now use this for authenticated scraping');
  
  await browser.close();
})();