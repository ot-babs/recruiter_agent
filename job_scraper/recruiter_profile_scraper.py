import asyncio
import os
import re
import random
import json
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from config import settings

def load_linkedin_auth_state():
    """Load authentication state from the extracted JSON file"""
    try:
        auth_file = os.path.join(os.path.dirname(__file__), 'linkedin_storage_state.json')
        if os.path.exists(auth_file):
            with open(auth_file, 'r') as f:
                return json.load(f)
        else:
            print("⚠️ No linkedin_storage_state.json found - falling back to unauthenticated scraping")
            return None
    except Exception as e:
        print(f"⚠️ Error loading auth state: {e}")
        return None

def get_random_user_agent():
    """Generate random user agents to avoid detection"""
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
    ]
    return random.choice(agents)

def extract_all_linkedin_cookies(auth_state):
    """Extract ALL LinkedIn cookies (the key fix!)"""
    if not auth_state or 'cookies' not in auth_state:
        return ""
    
    # Get ALL LinkedIn cookies, not just essential ones
    cookie_header = []
    for cookie in auth_state['cookies']:
        if 'linkedin.com' in cookie['domain']:
            cookie_header.append(f"{cookie['name']}={cookie['value']}")
    
    cookie_string = "; ".join(cookie_header)
    print(f"🍪 Using {len(cookie_header)} LinkedIn cookies")
    return cookie_string

async def scrape_linkedin_recruiter_profile(recruiter_url: str) -> dict:
    """
    Scrape LinkedIn recruiter profile with FULL authentication (ALL cookies)
    """
    try:
        # Load authentication state
        auth_state = load_linkedin_auth_state()
        
        if not auth_state:
            return {
                "url": recruiter_url,
                "error": "No authentication state found - please run extract_linkedin_auth.js"
            }
        
        # Browser configuration with ALL LinkedIn cookies
        browser_config = BrowserConfig(
            headless=True,
            browser_type="chromium",
            viewport_width=random.randint(1366, 1920),
            viewport_height=random.randint(768, 1080),
            headers={
                "User-Agent": get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Cache-Control": "no-cache",
                # THE KEY FIX: Use ALL LinkedIn cookies
                "Cookie": extract_all_linkedin_cookies(auth_state)
            },
            extra_args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                "--disable-extensions",
                "--no-first-run",
                "--disable-default-apps",
                "--disable-sync"
            ],
            verbose=False
        )
        
        # Generate random delays for human-like behavior
        delay1 = random.randint(2000, 4000)
        delay2 = random.randint(1500, 3000)
        delay3 = random.randint(2000, 4000)
        delay4 = random.randint(2000, 4000)
        delay5 = random.randint(3000, 5000)
        delay6 = random.randint(1000, 2000)
        delay7 = random.randint(1000, 2000)
        
        # Simple but effective JavaScript for scrolling
        js_script = f"""
        (async () => {{
            console.log('Starting authenticated profile scraping...');
            await new Promise(resolve => setTimeout(resolve, {delay1}));
            
            // Scroll like a human reading a profile
            window.scrollTo(0, window.innerHeight * 0.2);
            await new Promise(resolve => setTimeout(resolve, {delay2}));
            
            window.scrollTo(0, window.innerHeight * 0.5);
            await new Promise(resolve => setTimeout(resolve, {delay3}));
            
            window.scrollTo(0, window.innerHeight * 0.8);
            await new Promise(resolve => setTimeout(resolve, {delay4}));
            
            window.scrollTo(0, document.body.scrollHeight);
            await new Promise(resolve => setTimeout(resolve, {delay5}));
            
            // Scroll back up slowly like reading
            window.scrollTo(0, window.innerHeight * 0.6);
            await new Promise(resolve => setTimeout(resolve, {delay6}));
            
            window.scrollTo(0, 0);
            await new Promise(resolve => setTimeout(resolve, {delay7}));
            
            console.log('Profile scrolling complete');
        }})();
        """
        
        # Human-like crawl configuration
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            js_code=js_script,
            page_timeout=60000,
            delay_before_return_html=random.uniform(4.0, 8.0),
            remove_overlay_elements=True,
            process_iframes=False,
            magic=True,
            simulate_user=True,
            word_count_threshold=200
        )
        
        # Random delay before scraping (simulate human behavior)
        await asyncio.sleep(random.uniform(2, 5))
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(
                url=recruiter_url,
                config=run_config
            )
            
            if result.success:
                print(f"✅ Successfully scraped recruiter profile")
                print(f"Status: {result.status_code}")
                print(f"Content length: {len(result.markdown)}")
                
                # Debug: print what we actually got
                print(f"First 500 chars: {result.markdown[:500]}")
                
                # Check if we got authenticated content
                if is_authenticated_content(result.markdown):
                    print("🎉 AUTHENTICATED PROFILE DATA RETRIEVED!")
                    
                    # Parse recruiter information from authenticated content
                    recruiter_data = parse_authenticated_recruiter_profile(result.markdown, recruiter_url)
                    
                    return {
                        "url": recruiter_url,
                        "markdown": result.markdown,
                        "html": result.cleaned_html,
                        "metadata": recruiter_data,
                        "authenticated": True
                    }
                else:
                    print("⚠️ Still getting public profile view - authentication may have failed")
                    return {
                        "url": recruiter_url,
                        "error": "Authentication failed - only public profile data available"
                    }
                
            else:
                print(f"❌ Failed to scrape recruiter profile: {result.error_message}")
                return {
                    "url": recruiter_url,
                    "error": f"Recruiter profile scraping failed: {result.error_message}",
                    "markdown": "",
                    "html": "",
                    "metadata": {},
                }
                
    except Exception as e:
        return {
            "url": recruiter_url,
            "error": f"Recruiter profile scraping exception: {str(e)}",
            "markdown": "",
            "html": "",
            "metadata": {},
        }

def is_authenticated_content(content: str) -> bool:
    """Check if we got authenticated content vs public profile"""
    # Signs of authenticated access
    authenticated_indicators = [
        "Send message",
        "Connect",
        "Follow",
        "More actions",
        "Contact info",
        "Message",
        "years of experience"  # Usually only shown to authenticated users
    ]
    
    # Signs of public/unauthenticated access
    public_indicators = [
        "Sign in to view",
        "Join to view",
        "Sign up to see"
    ]
    
    has_authenticated = any(indicator in content for indicator in authenticated_indicators)
    has_public = any(indicator in content for indicator in public_indicators)
    
    print(f"🔍 Authentication check: authenticated_signals={has_authenticated}, public_signals={has_public}")
    
    return has_authenticated and not has_public

def parse_authenticated_recruiter_profile(markdown_content: str, recruiter_url: str) -> dict:
    """
    Parse authenticated recruiter profile content with enhanced patterns
    """
    # Enhanced patterns for authenticated LinkedIn profiles
    name_patterns = [
        r'^#\s+(.+?)(?:\n|$)',  # First markdown heading
        r'([A-Z][a-zA-Z\s.-]+?)\s+\|\s+LinkedIn',
        r'^(.+?)(?:\n.*?at\s+)',  # Name followed by position
        r'h1.*?>([^<]+)<'  # HTML h1 tag
    ]
    
    recruiter_name = "Recruiter"
    for pattern in name_patterns:
        match = re.search(pattern, markdown_content, re.MULTILINE | re.IGNORECASE)
        if match:
            potential_name = match.group(1).strip()
            if len(potential_name) > 2 and len(potential_name) < 50 and not any(word in potential_name.lower() for word in ['linkedin', 'profile', 'company']):
                recruiter_name = potential_name.replace(" | LinkedIn", "").strip()
                break
    
    # Enhanced position extraction for authenticated profiles
    position_patterns = [
        r'([A-Z][a-zA-Z\s,&.-]+?)\s+at\s+([A-Z][a-zA-Z\s&.,Inc-]+?)(?:\n|$)',
        r'## ([A-Z][a-zA-Z\s,&.-]+?)(?:\n|$)',
        r'\*\*([A-Z][a-zA-Z\s,&.-]+?)\*\*',
        r'headline.*?>([^<]+)',
        r'pv-entity__secondary-title.*?>([^<]+)'
    ]
    
    current_position = "Not specified"
    current_company = "Not specified"
    for pattern in position_patterns:
        match = re.search(pattern, markdown_content, re.IGNORECASE)
        if match:
            if len(match.groups()) >= 2:
                current_position = match.group(1).strip()
                current_company = match.group(2).strip()
            else:
                position_text = match.group(1).strip()
                if " at " in position_text:
                    parts = position_text.split(" at ", 1)
                    current_position = parts[0].strip()
                    current_company = parts[1].strip()
                else:
                    current_position = position_text
            break
    
    # Enhanced location extraction
    location_patterns = [
        r'([A-Z][a-zA-Z\s,.-]+?),\s*(?:United Kingdom|UK|England)',
        r'Location[:\s]*([A-Z][a-zA-Z\s,.-]+?)(?:\n|$)',
        r'([A-Z][a-zA-Z\s,.-]+?)\s+Area',
        r'Based in\s+([A-Z][a-zA-Z\s,.-]+?)(?:\n|$)',
        r'\b(London(?:\s+Area)?)\b'
    ]
    
    location = "Not specified"
    for pattern in location_patterns:
        match = re.search(pattern, markdown_content, re.MULTILINE)
        if match:
            potential_location = match.group(1).strip()
            if len(potential_location) > 2 and len(potential_location) < 50:
                location = potential_location
                break
    
    # Extract experience and specializations with authenticated patterns
    specialization_patterns = [
        r'Specializes? in\s+([a-zA-Z\s,&.-]+?)(?:\n|$)',
        r'Focus(?:es)?\s+on\s+([a-zA-Z\s,&.-]+?)(?:\n|$)',
        r'Expert in\s+([a-zA-Z\s,&.-]+?)(?:\n|$)',
        r'Recruiting\s+([a-zA-Z\s,&.-]+?)(?:\n|$)',
        r'Talent Acquisition.*?([a-zA-Z\s,&.-]+?)(?:\n|$)',
        r'(\d+)\+?\s+years?\s+(?:of\s+)?experience',
        r'helping\s+([a-zA-Z\s,&.-]+?)\s+professionals'
    ]
    
    specializations = []
    years_experience = "Not specified"
    
    for pattern in specialization_patterns:
        matches = re.finditer(pattern, markdown_content, re.IGNORECASE)
        for match in matches:
            spec = match.group(1).strip()
            if len(spec) > 3 and len(spec) < 100:
                if spec.isdigit():
                    years_experience = f"{spec}+ years"
                else:
                    specializations.append(spec)
    
    return {
        "recruiter_name": recruiter_name,
        "current_position": current_position,
        "current_company": current_company,
        "location": location,
        "specializations": specializations[:3],  # Limit to top 3
        "years_experience": years_experience,
        "education": "Check full profile",  # Authenticated users can get more details
        "industry_focus": specializations[:2] if specializations else ["Recruitment"],
        "source_url": recruiter_url,
        "authentication_status": "Authenticated"
    }

def fetch_recruiter_profile(recruiter_url: str, manual_recruiter_text: str = None) -> dict:
    """
    Main function: try authenticated scraping first, then fall back to manual input
    """
    
    # If manual text is provided, use that
    if manual_recruiter_text and manual_recruiter_text.strip():
        print("✅ Using manual recruiter profile input")
        return {
            "url": recruiter_url,
            "markdown": format_manual_recruiter_text(manual_recruiter_text, recruiter_url),
            "html": "",
            "metadata": parse_manual_recruiter_text(manual_recruiter_text, recruiter_url)
        }
    
    # Validate LinkedIn profile URL
    if not is_valid_linkedin_profile_url(recruiter_url):
        return create_manual_recruiter_input_prompt(recruiter_url, "Invalid LinkedIn profile URL")
    
    print(f"🎯 Attempting to scrape recruiter profile with FULL authentication")
    
    try:
        # Try authenticated scraping with ALL cookies
        result = asyncio.run(scrape_linkedin_recruiter_profile(recruiter_url))
        
        if result.get("error"):
            print(f"❌ Authenticated scraping failed: {result['error']}")
            return create_manual_recruiter_input_prompt(recruiter_url, result['error'])
        else:
            print("✅ Authenticated scraping successful!")
            return result
            
    except Exception as e:
        print(f"❌ Exception during authenticated scraping: {str(e)}")
        return create_manual_recruiter_input_prompt(recruiter_url, str(e))

def is_valid_linkedin_profile_url(url: str) -> bool:
    """Check if URL is a valid LinkedIn profile URL"""
    try:
        parsed = urlparse(url)
        return (
            'linkedin.com' in parsed.netloc and 
            '/in/' in parsed.path
        )
    except:
        return False

def create_manual_recruiter_input_prompt(recruiter_url: str, error_message: str) -> dict:
    """Create a manual input prompt for recruiter profile"""
    return {
        "url": recruiter_url,
        "markdown": "",
        "html": "",
        "metadata": {},
        "error": "MANUAL_INPUT_REQUIRED",
        "original_error": error_message,
        "instructions": {
            "message": "Authenticated scraping failed. Please copy and paste the recruiter's profile information manually.",
            "steps": [
                "1. Open the recruiter's LinkedIn profile in your browser",
                "2. Copy their name, current position, background, and specializations",
                "3. Paste it in the manual input field",
                "4. Click 'Parse Recruiter Profile' to proceed"
            ]
        }
    }

# Include all the manual parsing functions from your original code
def parse_manual_recruiter_text(recruiter_text: str, recruiter_url: str) -> dict:
    """Parse manually entered recruiter profile text"""
    return {
        "recruiter_name": extract_recruiter_name_from_text(recruiter_text),
        "current_position": extract_position_from_text(recruiter_text),
        "current_company": extract_company_from_manual_text(recruiter_text),
        "location": extract_location_from_manual_text(recruiter_text),
        "specializations": extract_specializations_from_text(recruiter_text),
        "years_experience": extract_experience_from_text(recruiter_text),
        "education": extract_education_from_text(recruiter_text),
        "industry_focus": extract_industry_focus_from_text(recruiter_text),
        "source_url": recruiter_url,
        "source": "Manual input"
    }

def extract_recruiter_name_from_text(text: str) -> str:
    """Extract recruiter name from manual text"""
    lines = text.strip().split('\n')
    for line in lines[:3]:
        line = line.strip()
        if line and len(line) > 2 and len(line) < 50:
            line = re.sub(r'^(Name:\s*|Recruiter:\s*)', '', line, flags=re.IGNORECASE)
            if line and not any(word in line.lower() for word in ['position', 'company', 'title', 'at ']):
                return line
    return "Recruiter (Manual Input)"

def extract_position_from_text(text: str) -> str:
    """Extract position from manual text"""
    patterns = [
        r'Position:\s*([A-Z][a-zA-Z\s,&.-]+?)(?:\n|$)',
        r'Title:\s*([A-Z][a-zA-Z\s,&.-]+?)(?:\n|$)',
        r'([A-Z][a-zA-Z\s,&.-]+?)\s+at\s+',
        r'Current:\s*([A-Z][a-zA-Z\s,&.-]+?)(?:\n|$)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return "Position (Manual Input)"

def extract_company_from_manual_text(text: str) -> str:
    """Extract company from manual text"""
    patterns = [
        r'at\s+([A-Z][a-zA-Z\s&]+?)(?:\s|$|\n)',
        r'Company:\s*([A-Z][a-zA-Z\s&]+?)(?:\s|$|\n)',
        r'Works at\s+([A-Z][a-zA-Z\s&]+?)(?:\s|$|\n)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            company = match.group(1).strip()
            if len(company) > 2:
                return company
    
    return "Company (Manual Input)"

def extract_location_from_manual_text(text: str) -> str:
    """Extract location from manual text"""
    patterns = [
        r'Location:\s*([A-Z][a-zA-Z\s,.-]+?)(?:\n|$)',
        r'Based in\s+([A-Z][a-zA-Z\s,.-]+?)(?:\n|$)',
        r'([A-Z][a-zA-Z\s,.-]+?),\s*(?:United States|USA|US)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            return match.group(1).strip()
    
    return "Location (Manual Input)"

def extract_specializations_from_text(text: str) -> list:
    """Extract specializations from manual text"""
    patterns = [
        r'Specializes? in\s+([a-zA-Z\s,&.-]+?)(?:\n|$)',
        r'Focus(?:es)?\s+on\s+([a-zA-Z\s,&.-]+?)(?:\n|$)',
        r'Expert in\s+([a-zA-Z\s,&.-]+?)(?:\n|$)'
    ]
    
    specializations = []
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            spec = match.group(1).strip()
            if len(spec) > 3:
                specializations.append(spec)
    
    return specializations[:3] if specializations else ["Recruitment (Manual Input)"]

def extract_experience_from_text(text: str) -> str:
    """Extract experience from manual text"""
    patterns = [
        r'(\d+)\+?\s+years?\s+(?:of\s+)?experience',
        r'(\d+)\+?\s+years?\s+in\s+recruiting',
        r'Experience:\s*(\d+)\+?\s+years?'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return f"{match.group(1)}+ years"
    
    return "Experience (Manual Input)"

def extract_education_from_text(text: str) -> str:
    """Extract education from manual text"""
    patterns = [
        r'Education:\s*([A-Z][a-zA-Z\s,&.-]+?)(?:\n|$)',
        r'University of\s+([A-Z][a-zA-Z\s,&.-]+?)(?:\n|$)',
        r'([A-Z][a-zA-Z\s,&.-]+?)\s+University'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return "Education (Manual Input)"

def extract_industry_focus_from_text(text: str) -> list:
    """Extract industry focus from manual text"""
    patterns = [
        r'recruiting\s+for\s+([a-zA-Z\s,&.-]+?)(?:\n|\.)',
        r'focus\s+on\s+([a-zA-Z\s,&.-]+?)\s+roles',
        r'hiring\s+([a-zA-Z\s,&.-]+?)\s+professionals'
    ]
    
    focus_areas = []
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            focus = match.group(1).strip()
            if len(focus) > 3:
                focus_areas.append(focus)
    
    return focus_areas[:3] if focus_areas else ["General Recruitment (Manual Input)"]

def format_manual_recruiter_text(recruiter_text: str, recruiter_url: str) -> str:
    """Format manual recruiter text as markdown"""
    recruiter_name = extract_recruiter_name_from_text(recruiter_text)
    
    markdown = f"""# {recruiter_name}

**Source URL:** {recruiter_url}

## Recruiter Profile Information

{recruiter_text.strip()}

---
**Source:** Manual input from LinkedIn recruiter profile
"""
    return markdown

def fetch_recruiter_profile_sync(recruiter_url: str, manual_recruiter_text: str = None) -> dict:
    """Synchronous wrapper - maintains compatibility with existing code"""
    return fetch_recruiter_profile(recruiter_url, manual_recruiter_text)

def format_recruiter_profile_as_markdown(recruiter_data: dict) -> str:
    """
    Format recruiter data as structured markdown for better parsing
    """
    if recruiter_data.get('error'):
        return f"Error: {recruiter_data['error']}"
    
    markdown = recruiter_data.get('markdown', '')
    metadata = recruiter_data.get('metadata', {})
    
    # Add structured headers if the content doesn't have them
    if markdown and metadata:
        specializations_str = ', '.join(metadata.get('specializations', [])) if metadata.get('specializations') else 'Not specified'
        industry_focus_str = ', '.join(metadata.get('industry_focus', [])) if metadata.get('industry_focus') else 'Not specified'
        
        auth_status = "✅ Authenticated" if metadata.get('authentication_status') == 'Authenticated' else "⚠️ Public view"
        
        structured_markdown = f"""# {metadata.get('recruiter_name', 'Recruiter Profile')}

## Professional Details ({auth_status})
**Current Position:** {metadata.get('current_position', 'Not specified')}
**Company:** {metadata.get('current_company', 'Not specified')}
**Location:** {metadata.get('location', 'Not specified')}
**Experience:** {metadata.get('years_experience', 'Not specified')}

## Recruitment Focus
**Specializations:** {specializations_str}
**Industry Focus:** {industry_focus_str}
**Education:** {metadata.get('education', 'Not specified')}

## Profile Content
{markdown}

---
**Source:** {recruiter_data.get('url', 'Unknown')}
"""
        return structured_markdown
    
    return markdown if markdown else "No recruiter profile information available"