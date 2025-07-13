# test_cookie_decline.py
import asyncio
import json
import os
import re
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

async def test_cookie_decline_and_extract():
    """Test declining cookies and extracting profile info"""
    print("🧪 Testing Cookie Decline + Profile Extraction")
    print("=" * 50)
    
    # Load auth file
    auth_file = None
    for location in ['linkedin_storage_state.json', 'job_scraper/linkedin_storage_state.json']:
        if os.path.exists(location):
            auth_file = location
            break
    
    if not auth_file:
        print("❌ Auth file not found")
        return
    
    with open(auth_file, 'r') as f:
        auth_data = json.load(f)
    
    # Extract li_at cookie
    li_at_value = None
    for cookie in auth_data['cookies']:
        if cookie['name'] == 'li_at':
            li_at_value = cookie['value']
            break
    
    if not li_at_value:
        print("❌ No li_at cookie found")
        return
    
    print(f"🍪 Using li_at cookie: {li_at_value[:20]}...")
    
    # Browser config with authentication
    browser_config = BrowserConfig(
        headless=True,
        browser_type="chromium",
        viewport_width=1920,
        viewport_height=1080,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Cookie": f"li_at={li_at_value}"
        }
    )
    
    # JavaScript to handle cookie consent and extract profile info
    js_script = """
    (async () => {
        console.log('Starting cookie decline test...');
        
        // Wait for page to load
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        // Try to find and click the "Reject" button
        const rejectSelectors = [
            '[data-tracking-control-name="guest-homepage-basic_reject-all"]',
            'button[action-type="DENY"]',
            'button:contains("Reject")',
            'button:contains("Decline")',
            '.artdeco-global-alert-action--secondary',
            '[aria-label*="reject"]',
            '[aria-label*="decline"]'
        ];
        
        let rejectButton = null;
        for (const selector of rejectSelectors) {
            try {
                rejectButton = document.querySelector(selector);
                if (rejectButton) {
                    console.log('Found reject button with selector:', selector);
                    break;
                }
            } catch (e) {
                console.log('Selector failed:', selector, e);
            }
        }
        
        // Also try finding by text content
        if (!rejectButton) {
            const buttons = document.querySelectorAll('button, a');
            for (const button of buttons) {
                const text = button.textContent?.toLowerCase() || '';
                if (text.includes('reject') || text.includes('decline') || text.includes('deny')) {
                    rejectButton = button;
                    console.log('Found reject button by text:', text);
                    break;
                }
            }
        }
        
        if (rejectButton) {
            console.log('Clicking reject button...');
            rejectButton.click();
            await new Promise(resolve => setTimeout(resolve, 3000));
            console.log('Reject button clicked, waiting for page update...');
        } else {
            console.log('No reject button found, continuing anyway...');
        }
        
        // Now let's see what profile information we can extract
        console.log('Extracting profile information...');
        
        // Scroll through the page to load content
        window.scrollTo(0, document.body.scrollHeight * 0.3);
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        window.scrollTo(0, document.body.scrollHeight * 0.6);
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        window.scrollTo(0, document.body.scrollHeight);
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        window.scrollTo(0, 0);
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Extract profile information
        const profileInfo = {
            name: '',
            headline: '',
            location: '',
            connections: '',
            about: '',
            experience: [],
            profilePicture: '',
            isPublic: false
        };
        
        // Try different selectors for name
        const nameSelectors = [
            'h1[aria-label*="heading"]',
            '.text-heading-xlarge',
            '.pv-text-details__left-panel h1',
            '.top-card-layout__title',
            '.pv-top-card--list h1',
            'h1.text-heading-xlarge'
        ];
        
        for (const selector of nameSelectors) {
            const element = document.querySelector(selector);
            if (element && element.textContent.trim()) {
                profileInfo.name = element.textContent.trim();
                console.log('Found name:', profileInfo.name);
                break;
            }
        }
        
        // Try different selectors for headline
        const headlineSelectors = [
            '.text-body-medium.break-words',
            '.pv-text-details__left-panel .text-body-medium',
            '.top-card-layout__headline',
            '.pv-top-card--list .text-body-medium',
            '[data-generated-suggestion-target]'
        ];
        
        for (const selector of headlineSelectors) {
            const element = document.querySelector(selector);
            if (element && element.textContent.trim() && !element.textContent.includes('LinkedIn')) {
                profileInfo.headline = element.textContent.trim();
                console.log('Found headline:', profileInfo.headline);
                break;
            }
        }
        
        // Try to find location
        const locationSelectors = [
            '.text-body-small.inline.t-black--light.break-words',
            '.pv-text-details__left-panel .text-body-small',
            '.top-card-layout__first-subline',
            '.pv-top-card--list .text-body-small'
        ];
        
        for (const selector of locationSelectors) {
            const element = document.querySelector(selector);
            if (element && element.textContent.trim()) {
                const text = element.textContent.trim();
                if (text && !text.includes('connections') && !text.includes('followers')) {
                    profileInfo.location = text;
                    console.log('Found location:', profileInfo.location);
                    break;
                }
            }
        }
        
        // Check if we're seeing a public profile or need login
        profileInfo.isPublic = !document.body.textContent.includes('Sign in to see full profile');
        
        // Log what we found
        console.log('Profile extraction complete:', profileInfo);
        
        // Return the extracted info
        return profileInfo;
    })();
    """
    
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        js_code=js_script,
        page_timeout=45000,
        delay_before_return_html=5.0,
        word_count_threshold=100
    )
    
    test_url = "https://www.linkedin.com/in/otbabs/"
    
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=test_url, config=run_config)
            
            if result.success:
                content = result.markdown
                print(f"📄 Got {len(content)} characters of content after cookie handling")
                
                # Analyze the content
                analyze_extracted_content(content)
                
                # Try to extract profile info using regex
                extracted_info = extract_profile_with_regex(content)
                print("\n🎯 Regex Extraction Results:")
                for key, value in extracted_info.items():
                    print(f"  {key}: {value}")
                
            else:
                print(f"❌ Request failed: {result.error_message}")
                
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")

def analyze_extracted_content(content):
    """Analyze the extracted content to see what we got"""
    print("\n📊 Content Analysis:")
    print(f"  Total length: {len(content)} characters")
    
    # Check for various indicators
    indicators = {
        "Cookie consent": "LinkedIn and 3rd parties use essential and non-essential cookies",
        "Login required": "Sign in to see",
        "Profile name": r'#\s+([A-Z][a-zA-Z\s.-]+)',
        "Job title/headline": r'([A-Z][a-zA-Z\s,&.-]+?)\s+at\s+([A-Z][a-zA-Z\s&.,Inc-]+)',
        "Location info": r'([A-Z][a-zA-Z\s,.-]+?),\s*(?:United States|USA|US|Area)',
        "Experience section": "Experience",
        "Education section": "Education",
        "About section": "About",
        "Connection count": r'(\d+(?:,\d+)*)\s+connections?'
    }
    
    found_indicators = {}
    for name, pattern in indicators.items():
        if isinstance(pattern, str):
            # Simple string search
            if pattern in content:
                found_indicators[name] = "✅ Found"
            else:
                found_indicators[name] = "❌ Not found"
        else:
            # Regex search
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                found_indicators[name] = f"✅ Found: {match.group(1) if match.groups() else match.group(0)}"
            else:
                found_indicators[name] = "❌ Not found"
    
    for name, status in found_indicators.items():
        print(f"  {name}: {status}")
    
    # Show first few lines to see structure
    lines = content.split('\n')[:10]
    print(f"\n📝 First 10 lines of content:")
    for i, line in enumerate(lines, 1):
        if line.strip():
            print(f"  {i}: {line.strip()[:100]}...")

def extract_profile_with_regex(content):
    """Extract profile information using regex patterns"""
    profile_info = {
        "name": "Not found",
        "headline": "Not found", 
        "location": "Not found",
        "connections": "Not found",
        "about_preview": "Not found"
    }
    
    # Extract name (first heading)
    name_patterns = [
        r'^#\s+(.+?)(?:\n|$)',
        r'([A-Z][a-zA-Z\s.-]{2,30})\s+\|\s+LinkedIn',
        r'^(.+?)(?:\n.*?at\s+)'
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, content, re.MULTILINE)
        if match:
            name = match.group(1).strip()
            if len(name) > 2 and len(name) < 50:
                profile_info["name"] = name.replace(" | LinkedIn", "")
                break
    
    # Extract headline/job title
    headline_patterns = [
        r'([A-Z][a-zA-Z\s,&.-]+?)\s+at\s+([A-Z][a-zA-Z\s&.,Inc-]+?)(?:\n|$)',
        r'## (.+?)(?:\n|$)',
        r'\*\*([A-Z][a-zA-Z\s,&.-]+?)\*\*'
    ]
    
    for pattern in headline_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            if len(match.groups()) >= 2:
                profile_info["headline"] = f"{match.group(1)} at {match.group(2)}"
            else:
                profile_info["headline"] = match.group(1)
            break
    
    # Extract location
    location_patterns = [
        r'([A-Z][a-zA-Z\s,.-]+?),\s*(?:United States|USA|US)',
        r'Location:\s*([A-Z][a-zA-Z\s,.-]+?)(?:\n|$)',
        r'([A-Z][a-zA-Z\s,.-]+?)\s+Area'
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, content)
        if match:
            profile_info["location"] = match.group(1).strip()
            break
    
    # Extract connection count
    connection_pattern = r'(\d+(?:,\d+)*)\s+connections?'
    match = re.search(connection_pattern, content, re.IGNORECASE)
    if match:
        profile_info["connections"] = f"{match.group(1)} connections"
    
    # Extract about preview (first paragraph after About)
    about_pattern = r'About\s*\n\s*(.{1,200})'
    match = re.search(about_pattern, content, re.IGNORECASE | re.DOTALL)
    if match:
        profile_info["about_preview"] = match.group(1).strip()[:100] + "..."
    
    return profile_info

def main():
    """Main test function"""
    print("🚀 Cookie Decline & Profile Extraction Test")
    print("This will test clicking 'Reject' on cookies and extracting profile info")
    print("=" * 60)
    
    asyncio.run(test_cookie_decline_and_extract())
    
    print("\n" + "=" * 60)
    print("🏁 Test complete")

if __name__ == "__main__":
    main()