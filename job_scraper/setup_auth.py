#!/usr/bin/env python3
"""
Setup script for LinkedIn authentication
"""

import os
import subprocess
import sys
import json

def check_nodejs():
    """Check if Node.js is installed"""
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Node.js found: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    
    print("❌ Node.js not found. Please install Node.js first:")
    print("   https://nodejs.org/")
    return False

def install_playwright():
    """Install Playwright dependencies"""
    print("📦 Installing Playwright...")
    
    try:
        # Install playwright package
        subprocess.run(['npm', 'install', 'playwright'], check=True)
        print("✅ Playwright installed")
        
        # Install browsers
        subprocess.run(['npx', 'playwright', 'install', 'chromium'], check=True)
        print("✅ Chromium browser installed")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install Playwright: {e}")
        return False

def create_auth_script():
    """Create the authentication script"""
    script_content = '''const { chromium } = require('playwright');
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
})();'''
    
    with open('extract_linkedin_auth.js', 'w') as f:
        f.write(script_content)
    
    print("✅ Authentication script created: extract_linkedin_auth.js")

def check_auth_status():
    """Check if authentication is already set up"""
    if os.path.exists('linkedin_storage_state.json'):
        try:
            with open('linkedin_storage_state.json', 'r') as f:
                data = json.load(f)
                if data.get('cookies'):
                    print(f"✅ Found existing authentication with {len(data['cookies'])} cookies")
                    return True
        except:
            pass
    
    print("❌ No valid authentication found")
    return False

def main():
    print("🔧 LinkedIn Scraper Authentication Setup")
    print("=" * 50)
    
    # Check Node.js
    if not check_nodejs():
        sys.exit(1)
    
    # Check if already authenticated
    if check_auth_status():
        choice = input("\nAuthentication already exists. Re-authenticate? (y/N): ")
        if choice.lower() != 'y':
            print("✅ Using existing authentication")
            return
    
    # Install Playwright
    if not install_playwright():
        sys.exit(1)
    
    # Create auth script
    create_auth_script()
    
    print("\n🚀 Setup complete!")
    print("\nNext steps:")
    print("1. Run: node extract_linkedin_auth.js")
    print("2. Login to LinkedIn in the browser")
    print("3. Press Enter when logged in")
    print("4. Your scraper will now work with authentication!")

if __name__ == "__main__":
    main()