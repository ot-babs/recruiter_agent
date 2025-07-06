import asyncio
import os
import re
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from config import settings

async def scrape_linkedin_company(company_url: str) -> dict:
    """
    Directly scrape a specific LinkedIn company URL using crawl4ai
    """
    try:
        # Browser configuration with LinkedIn-optimized settings
        browser_config = BrowserConfig(
            headless=True,
            browser_type="chromium",
            viewport_width=1920,
            viewport_height=1080,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Cache-Control": "max-age=0",
                "Cookie": f"li_at={settings.LI_AT_COOKIE}" if hasattr(settings, 'LI_AT_COOKIE') and settings.LI_AT_COOKIE != "your_linkedin_cookie_value" else ""
            },
            extra_args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-web-security"
            ],
            verbose=True
        )
        
        # Crawl configuration for company page content
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            # LinkedIn company page specific JavaScript
            js_code=[
                "window.scrollTo(0, document.body.scrollHeight);",
                "await new Promise(resolve => setTimeout(resolve, 3000));",
                "document.querySelector('.org-top-card-summary')?.scrollIntoView();",
                "await new Promise(resolve => setTimeout(resolve, 2000));",
                "document.querySelector('.org-about-us')?.scrollIntoView();",
                "await new Promise(resolve => setTimeout(resolve, 2000));",
                "window.scrollTo(0, 0);"
            ],
            page_timeout=30000,
            delay_before_return_html=3.0,
            remove_overlay_elements=True,
            process_iframes=True,
            magic=True,  # Enable anti-detection features
            simulate_user=True,
            word_count_threshold=50
        )
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(
                url=company_url,
                config=run_config
            )
            
            if result.success:
                print(f"✅ Successfully scraped company page")
                print(f"Status: {result.status_code}")
                print(f"Content length: {len(result.markdown)}")
                
                # Debug: print what we actually got
                print(f"First 500 chars: {result.markdown[:500]}")
                
                # Check if we got meaningful content
                if len(result.markdown.strip()) < 200:
                    return {
                        "url": company_url,
                        "error": "Company page content too short - likely blocked or login required"
                    }
                
                # Parse company information
                company_data = parse_company_content(result.markdown, company_url)
                
                return {
                    "url": company_url,
                    "markdown": result.markdown,
                    "html": result.cleaned_html,
                    "metadata": company_data,
                }
            else:
                print(f"❌ Failed to scrape company page: {result.error_message}")
                return {
                    "url": company_url,
                    "error": f"Company scraping failed: {result.error_message}",
                    "markdown": "",
                    "html": "",
                    "metadata": {},
                }
                
    except Exception as e:
        return {
            "url": company_url,
            "error": f"Company scraping exception: {str(e)}",
            "markdown": "",
            "html": "",
            "metadata": {},
        }

def parse_company_content(markdown_content: str, company_url: str) -> dict:
    """
    Extract company metadata from scraped markdown content
    """
    # Extract company name
    company_name_patterns = [
        r'^#\s+(.+?)(?:\n|$)',  # First markdown heading
        r'([A-Z][a-zA-Z\s&.,Inc-]+?)\s+\|\s+LinkedIn',
        r'^(.+?)\s+LinkedIn',
        r'About\s+([A-Z][a-zA-Z\s&.,Inc-]+?)(?:\n|$)'
    ]
    
    company_name = "Unknown Company"
    for pattern in company_name_patterns:
        match = re.search(pattern, markdown_content, re.MULTILINE)
        if match:
            potential_name = match.group(1).strip()
            if len(potential_name) > 1 and len(potential_name) < 100:
                company_name = potential_name.replace(" | LinkedIn", "").strip()
                break
    
    # Extract industry
    industry_patterns = [
        r'Industry:\s*([A-Z][a-zA-Z\s,&.-]+?)(?:\n|$)',
        r'([A-Z][a-zA-Z\s,&.-]+?)\s+industry',
        r'We are\s+(?:a|an)\s+([a-zA-Z\s,&.-]+?)\s+company'
    ]
    
    industry = "Not specified"
    for pattern in industry_patterns:
        match = re.search(pattern, markdown_content, re.IGNORECASE)
        if match:
            potential_industry = match.group(1).strip()
            if len(potential_industry) > 3 and len(potential_industry) < 50:
                industry = potential_industry
                break
    
    # Extract company size
    size_patterns = [
        r'(\d+(?:,\d+)*(?:-\d+(?:,\d+)*)?)\s+employees',
        r'Size:\s*(\d+(?:,\d+)*(?:-\d+(?:,\d+)*)?)',
        r'Company size:\s*(\d+(?:,\d+)*(?:-\d+(?:,\d+)*)?)'
    ]
    
    company_size = "Not specified"
    for pattern in size_patterns:
        match = re.search(pattern, markdown_content, re.IGNORECASE)
        if match:
            company_size = f"{match.group(1)} employees"
            break
    
    # Extract headquarters/location
    location_patterns = [
        r'Headquarters:\s*([A-Z][a-zA-Z\s,.-]+?)(?:\n|$)',
        r'Location:\s*([A-Z][a-zA-Z\s,.-]+?)(?:\n|$)',
        r'Based in\s+([A-Z][a-zA-Z\s,.-]+?)(?:\n|$)',
        r'([A-Z][a-zA-Z\s,.-]+?),\s*(?:United States|USA|US)'
    ]
    
    headquarters = "Not specified"
    for pattern in location_patterns:
        match = re.search(pattern, markdown_content, re.MULTILINE)
        if match:
            potential_location = match.group(1).strip()
            if len(potential_location) > 2 and len(potential_location) < 100:
                headquarters = potential_location
                break
    
    # Extract founded year
    founded_patterns = [
        r'Founded:\s*(\d{4})',
        r'Founded in\s+(\d{4})',
        r'Since\s+(\d{4})',
        r'Established\s+(\d{4})'
    ]
    
    founded = "Not specified"
    for pattern in founded_patterns:
        match = re.search(pattern, markdown_content)
        if match:
            founded = match.group(1)
            break
    
    return {
        "company_name": company_name,
        "industry": industry,
        "company_size": company_size,
        "headquarters": headquarters,
        "founded": founded,
        "source_url": company_url
    }

def fetch_recruiter_info(company_url: str, manual_company_text: str = None) -> dict:
    """
    Main function: try direct scraping first, then fall back to manual input
    """
    
    # If manual text is provided, use that
    if manual_company_text and manual_company_text.strip():
        print("✅ Using manual company description input")
        return {
            "url": company_url,
            "markdown": format_manual_company_text(manual_company_text, company_url),
            "html": "",
            "metadata": parse_manual_company_text(manual_company_text, company_url)
        }
    
    # Validate LinkedIn company URL
    if not is_valid_linkedin_company_url(company_url):
        return create_manual_company_input_prompt(company_url, "Invalid LinkedIn company URL")
    
    print(f"🎯 Attempting to scrape company page directly from URL")
    
    try:
        # Try direct URL scraping
        result = asyncio.run(scrape_linkedin_company(company_url))
        
        if result.get("error"):
            print(f"❌ Direct company scraping failed: {result['error']}")
            return create_manual_company_input_prompt(company_url, result['error'])
        else:
            print("✅ Direct company scraping successful!")
            return result
            
    except Exception as e:
        print(f"❌ Exception during direct company scraping: {str(e)}")
        return create_manual_company_input_prompt(company_url, str(e))

def is_valid_linkedin_company_url(url: str) -> bool:
    """Check if URL is a valid LinkedIn company URL"""
    try:
        parsed = urlparse(url)
        return (
            'linkedin.com' in parsed.netloc and 
            '/company/' in parsed.path
        )
    except:
        return False

def create_manual_company_input_prompt(company_url: str, error_message: str) -> dict:
    """Create a manual input prompt for company info"""
    return {
        "url": company_url,
        "markdown": "",
        "html": "",
        "metadata": {},
        "error": "MANUAL_INPUT_REQUIRED",
        "original_error": error_message,
        "instructions": {
            "message": "Direct company scraping failed. Please copy and paste the company information manually.",
            "steps": [
                "1. Open the LinkedIn company page in your browser",
                "2. Copy the company description and key details",
                "3. Paste it in the manual input field",
                "4. Click 'Parse Company Information' to proceed"
            ]
        }
    }

def parse_manual_company_text(company_text: str, company_url: str) -> dict:
    """Parse manually entered company text"""
    return {
        "company_name": extract_company_name_from_text(company_text),
        "industry": extract_industry_from_text(company_text),
        "company_size": extract_size_from_text(company_text),
        "headquarters": extract_location_from_text(company_text),
        "founded": extract_founded_from_text(company_text),
        "source_url": company_url,
        "source": "Manual input"
    }

def extract_company_name_from_text(text: str) -> str:
    """Extract company name from manual text"""
    lines = text.strip().split('\n')
    for line in lines[:3]:
        line = line.strip()
        if line and len(line) > 2 and len(line) < 100:
            # Remove common prefixes
            line = re.sub(r'^(About\s+|Company:\s*)', '', line, flags=re.IGNORECASE)
            if line:
                return line
    return "Company Name (Manual Input)"

def extract_industry_from_text(text: str) -> str:
    """Extract industry from manual text"""
    patterns = [
        r'Industry:\s*([A-Z][a-zA-Z\s,&.-]+?)(?:\n|$)',
        r'([A-Z][a-zA-Z\s,&.-]+?)\s+industry',
        r'We are\s+(?:a|an)\s+([a-zA-Z\s,&.-]+?)\s+company'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return "Industry (Manual Input)"

def extract_size_from_text(text: str) -> str:
    """Extract company size from manual text"""
    patterns = [
        r'(\d+(?:,\d+)*(?:-\d+(?:,\d+)*)?)\s+employees',
        r'Size:\s*(\d+(?:,\d+)*(?:-\d+(?:,\d+)*)?)',
        r'Company size:\s*(\d+(?:,\d+)*(?:-\d+(?:,\d+)*)?)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return f"{match.group(1)} employees"
    
    return "Size (Manual Input)"

def extract_location_from_text(text: str) -> str:
    """Extract location from manual text"""
    patterns = [
        r'Headquarters:\s*([A-Z][a-zA-Z\s,.-]+?)(?:\n|$)',
        r'Location:\s*([A-Z][a-zA-Z\s,.-]+?)(?:\n|$)',
        r'Based in\s+([A-Z][a-zA-Z\s,.-]+?)(?:\n|$)',
        r'([A-Z][a-zA-Z\s,.-]+?),\s*(?:United States|USA|US)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            return match.group(1).strip()
    
    return "Location (Manual Input)"

def extract_founded_from_text(text: str) -> str:
    """Extract founded year from manual text"""
    patterns = [
        r'Founded:\s*(\d{4})',
        r'Founded in\s+(\d{4})',
        r'Since\s+(\d{4})',
        r'Established\s+(\d{4})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    return "Founded (Manual Input)"

def format_manual_company_text(company_text: str, company_url: str) -> str:
    """Format manual company text as markdown"""
    company_name = extract_company_name_from_text(company_text)
    
    markdown = f"""# {company_name}

**Source URL:** {company_url}

## Company Information

{company_text.strip()}

---
**Source:** Manual input from LinkedIn company page
"""
    return markdown

def fetch_recruiter_info_sync(company_url: str, manual_company_text: str = None) -> dict:
    """Synchronous wrapper - maintains compatibility with existing code"""
    return fetch_recruiter_info(company_url, manual_company_text)

def format_company_info_as_markdown(company_data: dict) -> str:
    """
    Format company data as structured markdown for better parsing
    """
    if company_data.get('error'):
        return f"Error: {company_data['error']}"
    
    markdown = company_data.get('markdown', '')
    metadata = company_data.get('metadata', {})
    
    # Add structured headers if the content doesn't have them
    if markdown and metadata:
        structured_markdown = f"""# {metadata.get('company_name', 'Company Information')}

## Company Overview
**Industry:** {metadata.get('industry', 'Not specified')}
**Size:** {metadata.get('company_size', 'Not specified')}
**Headquarters:** {metadata.get('headquarters', 'Not specified')}
**Founded:** {metadata.get('founded', 'Not specified')}

## About the Company
{markdown}

---
**Source:** {company_data.get('url', 'Unknown')}
"""
        return structured_markdown
    
    return markdown if markdown else "No company information available"