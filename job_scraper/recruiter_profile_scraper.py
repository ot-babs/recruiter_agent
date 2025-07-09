import asyncio
import os
import re
import random
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from config import settings

def get_random_user_agent():
    """Generate random user agents to avoid detection"""
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
    ]
    return random.choice(agents)

async def scrape_linkedin_recruiter_profile(recruiter_url: str) -> dict:
    """
    Directly scrape a specific LinkedIn recruiter profile URL using crawl4ai
    """
    try:
        # Browser configuration WITHOUT authentication - appears as regular visitor
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
                "Cache-Control": "no-cache"
                # NO COOKIES - this eliminates detection risk
            },
            extra_args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                "--disable-extensions",
                "--no-first-run"
            ],
            verbose=False  # Reduce logs for stealth
        )
        
        # Human-like crawl configuration with randomized timing
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            # Randomized human-like scrolling
            js_code=[
                f"await new Promise(resolve => setTimeout(resolve, {random.randint(1000, 2000)}));",
                "window.scrollTo(0, window.innerHeight * 0.3);",
                f"await new Promise(resolve => setTimeout(resolve, {random.randint(800, 1500)}));",
                "window.scrollTo(0, window.innerHeight * 0.7);",
                f"await new Promise(resolve => setTimeout(resolve, {random.randint(1000, 2000)}));",
                "window.scrollTo(0, document.body.scrollHeight);",
                f"await new Promise(resolve => setTimeout(resolve, {random.randint(2000, 4000)}));",
                "window.scrollTo(0, 0);",
                f"await new Promise(resolve => setTimeout(resolve, {random.randint(500, 1000)}));"
            ],
            page_timeout=45000,
            delay_before_return_html=random.uniform(3.0, 6.0),
            remove_overlay_elements=True,
            process_iframes=False,
            magic=True,
            simulate_user=True,
            word_count_threshold=100
        )
        
        # Add random delay before scraping
        await asyncio.sleep(random.uniform(1, 3))
        
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
                
                # Check if we got meaningful content
                if len(result.markdown.strip()) < 200:
                    return {
                        "url": recruiter_url,
                        "error": "Recruiter profile content too short - likely blocked or login required"
                    }
                
                # Parse recruiter information
                recruiter_data = parse_recruiter_profile_content(result.markdown, recruiter_url)
                
                return {
                    "url": recruiter_url,
                    "markdown": result.markdown,
                    "html": result.cleaned_html,
                    "metadata": recruiter_data,
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

def parse_recruiter_profile_content(markdown_content: str, recruiter_url: str) -> dict:
    """
    Extract recruiter metadata from scraped markdown content
    """
    # Extract recruiter name
    name_patterns = [
        r'^#\s+(.+?)(?:\n|$)',  # First markdown heading
        r'([A-Z][a-zA-Z\s.-]+?)\s+\|\s+LinkedIn',
        r'^(.+?)(?:\n.*?at\s+)',  # Name followed by position
        r'([A-Z][a-zA-Z\s.-]+?)(?:\s+LinkedIn\s+Profile|$)'
    ]
    
    recruiter_name = "Recruiter"
    for pattern in name_patterns:
        match = re.search(pattern, markdown_content, re.MULTILINE)
        if match:
            potential_name = match.group(1).strip()
            if len(potential_name) > 2 and len(potential_name) < 50 and not any(word in potential_name.lower() for word in ['linkedin', 'profile', 'company']):
                recruiter_name = potential_name.replace(" | LinkedIn", "").strip()
                break
    
    # Extract current position/title
    position_patterns = [
        r'([A-Z][a-zA-Z\s,&.-]+?)\s+at\s+([A-Z][a-zA-Z\s&.,Inc-]+?)(?:\n|$)',
        r'Current:\s*([A-Z][a-zA-Z\s,&.-]+?)(?:\n|$)',
        r'Title:\s*([A-Z][a-zA-Z\s,&.-]+?)(?:\n|$)',
        r'Position:\s*([A-Z][a-zA-Z\s,&.-]+?)(?:\n|$)'
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
                current_position = match.group(1).strip()
            break
    
    # Extract location
    location_patterns = [
        r'Location:\s*([A-Z][a-zA-Z\s,.-]+?)(?:\n|$)',
        r'Based in\s+([A-Z][a-zA-Z\s,.-]+?)(?:\n|$)',
        r'([A-Z][a-zA-Z\s,.-]+?),\s*(?:United States|USA|US)',
        r'([A-Z][a-zA-Z\s,.-]+?)\s+Area'
    ]
    
    location = "Not specified"
    for pattern in location_patterns:
        match = re.search(pattern, markdown_content, re.MULTILINE)
        if match:
            potential_location = match.group(1).strip()
            if len(potential_location) > 2 and len(potential_location) < 50:
                location = potential_location
                break
    
    # Extract specializations/focus areas
    specialization_patterns = [
        r'Specializes? in\s+([a-zA-Z\s,&.-]+?)(?:\n|$)',
        r'Focus(?:es)?\s+on\s+([a-zA-Z\s,&.-]+?)(?:\n|$)',
        r'Expert in\s+([a-zA-Z\s,&.-]+?)(?:\n|$)',
        r'Recruiting\s+([a-zA-Z\s,&.-]+?)(?:\n|$)',
        r'Talent Acquisition.*?([a-zA-Z\s,&.-]+?)(?:\n|$)'
    ]
    
    specializations = []
    for pattern in specialization_patterns:
        matches = re.finditer(pattern, markdown_content, re.IGNORECASE)
        for match in matches:
            spec = match.group(1).strip()
            if len(spec) > 3 and len(spec) < 100:
                specializations.append(spec)
    
    # Extract years of experience
    experience_patterns = [
        r'(\d+)\+?\s+years?\s+(?:of\s+)?experience',
        r'(\d+)\+?\s+years?\s+in\s+recruiting',
        r'Over\s+(\d+)\s+years?',
        r'(\d+)\+?\s+years?\s+talent'
    ]
    
    years_experience = "Not specified"
    for pattern in experience_patterns:
        match = re.search(pattern, markdown_content, re.IGNORECASE)
        if match:
            years_experience = f"{match.group(1)}+ years"
            break
    
    # Extract education (basic)
    education_patterns = [
        r'Education.*?([A-Z][a-zA-Z\s,&.-]+?)(?:\n|$)',
        r'University of\s+([A-Z][a-zA-Z\s,&.-]+?)(?:\n|$)',
        r'([A-Z][a-zA-Z\s,&.-]+?)\s+University',
        r'Degree.*?([A-Z][a-zA-Z\s,&.-]+?)(?:\n|$)'
    ]
    
    education = "Not specified"
    for pattern in education_patterns:
        match = re.search(pattern, markdown_content, re.IGNORECASE)
        if match:
            potential_edu = match.group(1).strip()
            if len(potential_edu) > 3 and len(potential_edu) < 100:
                education = potential_edu
                break
    
    # Extract recruiting focus/industries
    industry_focus_patterns = [
        r'recruiting\s+for\s+([a-zA-Z\s,&.-]+?)(?:\n|\.)',
        r'focus\s+on\s+([a-zA-Z\s,&.-]+?)\s+roles',
        r'([a-zA-Z\s,&.-]+?)\s+recruitment',
        r'hiring\s+([a-zA-Z\s,&.-]+?)\s+professionals'
    ]
    
    industry_focus = []
    for pattern in industry_focus_patterns:
        matches = re.finditer(pattern, markdown_content, re.IGNORECASE)
        for match in matches:
            focus = match.group(1).strip()
            if len(focus) > 3 and len(focus) < 50:
                industry_focus.append(focus)
    
    return {
        "recruiter_name": recruiter_name,
        "current_position": current_position,
        "current_company": current_company,
        "location": location,
        "specializations": specializations[:3],  # Limit to top 3
        "years_experience": years_experience,
        "education": education,
        "industry_focus": industry_focus[:3],  # Limit to top 3
        "source_url": recruiter_url
    }

def fetch_recruiter_profile(recruiter_url: str, manual_recruiter_text: str = None) -> dict:
    """
    Main function: try direct scraping first, then fall back to manual input
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
    
    print(f"🎯 Attempting to scrape recruiter profile directly from URL")
    
    try:
        # Try direct URL scraping
        result = asyncio.run(scrape_linkedin_recruiter_profile(recruiter_url))
        
        if result.get("error"):
            print(f"❌ Direct recruiter profile scraping failed: {result['error']}")
            return create_manual_recruiter_input_prompt(recruiter_url, result['error'])
        else:
            print("✅ Direct recruiter profile scraping successful!")
            return result
            
    except Exception as e:
        print(f"❌ Exception during direct recruiter profile scraping: {str(e)}")
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
            "message": "Direct recruiter profile scraping failed. Please copy and paste the recruiter's profile information manually.",
            "steps": [
                "1. Open the recruiter's LinkedIn profile in your browser",
                "2. Copy their name, current position, background, and specializations",
                "3. Paste it in the manual input field",
                "4. Click 'Parse Recruiter Profile' to proceed"
            ]
        }
    }

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
            # Remove common prefixes
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
        
        structured_markdown = f"""# {metadata.get('recruiter_name', 'Recruiter Profile')}

## Professional Details
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