import asyncio
import os
import re
from urllib.parse import urlparse, parse_qs
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from config import settings

async def scrape_specific_linkedin_job(job_url: str) -> dict:
    """
    Directly scrape a specific LinkedIn job URL using crawl4ai with robust selectors
    """
    try:
        # Browser configuration with LinkedIn authentication
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
                "Cookie": f"li_at={settings.LI_AT_COOKIE}" if settings.LI_AT_COOKIE != "your_linkedin_cookie_value" else ""
            },
            extra_args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-web-security"
            ],
            verbose=True
        )
        
        # Simplified crawl configuration - don't wait for specific selectors
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            # Simple JavaScript to ensure page loads
            js_code=[
                "window.scrollTo(0, document.body.scrollHeight);",
                "await new Promise(resolve => setTimeout(resolve, 5000));",
                "window.scrollTo(0, 0);",
                "await new Promise(resolve => setTimeout(resolve, 2000));"
            ],
            # Remove wait_for condition that's causing timeout
            page_timeout=30000,
            delay_before_return_html=5.0,
            remove_overlay_elements=True,
            process_iframes=True,
            magic=True,
            simulate_user=True,
            word_count_threshold=10
        )
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(
                url=job_url,
                config=run_config
            )
            
            if result.success:
                print(f"✅ Successfully scraped job page directly")
                print(f"Status: {result.status_code}")
                print(f"Content length: {len(result.markdown)}")
                
                # Debug: show first 500 chars
                print(f"First 500 chars: {result.markdown[:500]}")
                
                # Check if we got meaningful content
                if len(result.markdown.strip()) < 100:
                    return {
                        "url": job_url,
                        "error": "Page content too short - likely blocked or login required"
                    }
                
                # Extract job details from the scraped content
                job_data = parse_job_content(result.markdown, job_url)
                
                return {
                    "url": job_url,
                    "markdown": result.markdown,
                    "html": result.cleaned_html,
                    "metadata": job_data
                }
            else:
                print(f"❌ Failed to scrape job page: {result.error_message}")
                return {
                    "url": job_url,
                    "error": f"Direct scraping failed: {result.error_message}"
                }
                
    except Exception as e:
        return {
            "url": job_url,
            "error": f"Scraping exception: {str(e)}"
        }

def parse_job_content(markdown_content: str, job_url: str) -> dict:
    """
    Extract job metadata from scraped markdown content with improved patterns
    """
    job_id = extract_job_id_from_url(job_url)
    
    # More flexible title extraction
    title_patterns = [
        r'^#\s+(.+)$',  # Markdown heading
        r'Job\s+Title:\s*(.+)',
        r'^(.+?)\s+at\s+.+$',  # "Software Engineer at Company"
        r'^([A-Z][^a-z]*[a-z].*?)(?:\n|$)'  # First capitalized line
    ]
    
    title = "Job Title"
    for pattern in title_patterns:
        match = re.search(pattern, markdown_content, re.MULTILINE)
        if match:
            potential_title = match.group(1).strip()
            if len(potential_title) > 5 and len(potential_title) < 100:
                title = potential_title
                break
    
    # Improved company extraction
    company_patterns = [
        r'at\s+([A-Z][a-zA-Z\s&.,Inc-]+?)(?:\s*\n|\s*$)',
        r'Company:\s*([A-Z][a-zA-Z\s&.,Inc-]+?)(?:\s*\n|\s*$)',
        r'([A-Z][a-zA-Z\s&.,Inc-]+?)\s+is\s+(?:seeking|looking|hiring)',
        r'Join\s+([A-Z][a-zA-Z\s&.,Inc-]+?)(?:\s*\n|\s*$)',
        r'About\s+([A-Z][a-zA-Z\s&.,Inc-]+?)(?:\s*\n|\s*$)'
    ]
    
    company = "Unknown Company"
    for pattern in company_patterns:
        match = re.search(pattern, markdown_content, re.IGNORECASE)
        if match:
            potential_company = match.group(1).strip()
            if len(potential_company) > 1 and len(potential_company) < 50:
                company = potential_company
                break
    
    # Enhanced location extraction
    location_patterns = [
        r'Location:\s*([A-Z][a-zA-Z\s,.-]+?)(?:\n|$)',
        r'(?:^|\n)([A-Z][a-zA-Z\s,.-]*?)(?:,\s*(?:CA|NY|TX|FL|WA|Remote|USA))',
        r'(Remote|Hybrid|On-site)',
        r'([A-Z][a-zA-Z\s,.-]+?),\s*(?:United States|US|USA)'
    ]
    
    location = "Location not specified"
    for pattern in location_patterns:
        match = re.search(pattern, markdown_content, re.MULTILINE)
        if match:
            potential_location = match.group(1).strip()
            if len(potential_location) > 2 and len(potential_location) < 50:
                location = potential_location
                break
    
    return {
        "job_id": job_id,
        "title": title,
        "company": company,
        "location": location,
        "posted_date": "Recently posted",
        "apply_link": job_url,
        "company_link": "",
        "insights": []
    }

def fetch_linkedin_job(job_url: str, manual_job_text: str = None) -> dict:
    """
    Main function: try direct scraping first, then fall back to manual input
    """
    
    # If manual text is provided, use that
    if manual_job_text and manual_job_text.strip():
        print("✅ Using manual job description input")
        return {
            "url": job_url,
            "markdown": format_manual_job_text(manual_job_text, job_url),
            "html": "",
            "metadata": {
                "job_id": extract_job_id_from_url(job_url),
                "title": extract_title_from_text(manual_job_text),
                "company": extract_company_from_text(manual_job_text),
                "location": extract_location_from_text(manual_job_text),
                "posted_date": "Manual input",
                "apply_link": job_url,
                "company_link": "",
                "insights": []
            }
        }
    
    # Check if we have a valid LinkedIn job URL
    job_id = extract_job_id_from_url(job_url)
    if not job_id:
        return create_manual_input_prompt(job_url, "Invalid LinkedIn job URL")
    
    print(f"🎯 Attempting to scrape job ID: {job_id} directly from URL")
    
    try:
        # Try direct URL scraping
        result = asyncio.run(scrape_specific_linkedin_job(job_url))
        
        if result.get("error"):
            print(f"❌ Direct scraping failed: {result['error']}")
            return create_manual_input_prompt(job_url, result['error'])
        else:
            print("✅ Direct scraping successful!")
            return result
            
    except Exception as e:
        print(f"❌ Exception during direct scraping: {str(e)}")
        return create_manual_input_prompt(job_url, str(e))

def extract_title_from_text(text: str) -> str:
    """Extract job title from manual text"""
    lines = text.strip().split('\n')
    for line in lines[:5]:
        line = line.strip()
        if line and len(line) > 10 and not line.lower().startswith(('about', 'we are', 'posted', 'company')):
            return line
    return "Job Title (Manual Input)"

def extract_company_from_text(text: str) -> str:
    """Extract company name from manual text"""
    patterns = [
        r'at\s+([A-Z][a-zA-Z\s&]+?)(?:\s|$)',
        r'Company:\s*([A-Z][a-zA-Z\s&]+?)(?:\s|$)',
        r'([A-Z][a-zA-Z\s&]+?)\s+is\s+(?:seeking|looking|hiring)',
        r'Join\s+([A-Z][a-zA-Z\s&]+?)(?:\s|$)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            company = match.group(1).strip()
            if len(company) > 2:
                return company
    
    return "Company (Manual Input)"

def extract_location_from_text(text: str) -> str:
    """Extract location from manual text"""
    patterns = [
        r'Location:\s*([A-Z][a-zA-Z\s,]+?)(?:\n|$)',
        r'Based in\s+([A-Z][a-zA-Z\s,]+?)(?:\n|$)',
        r'(Remote|Hybrid|On-site)',
        r'([A-Z][a-zA-Z\s,]+?)(?:,\s*(?:CA|NY|TX|FL|WA))'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip() if hasattr(match.group(1), 'strip') else match.group(0).strip()
    
    return "Location (Manual Input)"

def create_manual_input_prompt(job_url: str, error_message: str) -> dict:
    """Create a manual input prompt"""
    return {
        "url": job_url,
        "markdown": "",
        "html": "",
        "metadata": {},
        "error": "MANUAL_INPUT_REQUIRED",
        "original_error": error_message,
        "instructions": {
            "message": "Direct job scraping failed. Please copy and paste the job description manually.",
            "steps": [
                "1. Open the LinkedIn job URL in your browser",
                "2. Copy the entire job description text",
                "3. Paste it in the manual input field below",
                "4. Click 'Parse Job Description' to proceed"
            ]
        }
    }

def format_manual_job_text(job_text: str, job_url: str) -> str:
    """Format manual job text as markdown"""
    job_id = extract_job_id_from_url(job_url)
    title = extract_title_from_text(job_text)
    
    markdown = f"""# {title}

**Source URL:** {job_url}
**Job ID:** {job_id or 'Unknown'}

## Job Description

{job_text.strip()}

---
**Source:** Manual input from LinkedIn job posting
"""
    return markdown

def fetch_linkedin_job_sync(job_url: str, manual_job_text: str = None) -> dict:
    """Synchronous wrapper"""
    return fetch_linkedin_job(job_url, manual_job_text)

def extract_job_id_from_url(url: str) -> str:
    """Extract job ID from LinkedIn job URL"""
    try:
        match = re.search(r'/jobs/view/(\d+)', url)
        if match:
            return match.group(1)
        
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        if 'currentJobId' in query_params:
            return query_params['currentJobId'][0]
            
        return None
    except:
        return None