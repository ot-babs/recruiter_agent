"""
LinkedIn Profile Scraper - Enhanced version for job_scraper module
────────────────────────────────────────────────────────────────

Robust LinkedIn profile scraper with multiple fallback methods:
- Basic CSS extraction with crawl4ai
- Manual extraction with BeautifulSoup  
- Stealth mode with Playwright
- Manual input as final fallback

Dependencies:
pip install crawl4ai playwright beautifulsoup4
"""
import os, json, asyncio, sys, time, re
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

# Try to import crawl4ai, fallback to manual extraction if not available
try:
    from crawl4ai import AsyncWebCrawler
    from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
    from crawl4ai import CrawlerRunConfig, CacheMode
    CRAWL4AI_AVAILABLE = True
except ImportError:
    print("⚠️  crawl4ai not installed, will use manual extraction")
    CRAWL4AI_AVAILABLE = False

# Try to import BeautifulSoup for fallback
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

def get_linkedin_credentials():
    """Get LinkedIn credentials from environment variables"""
    email = os.getenv("LINKEDIN_EMAIL")
    password = os.getenv("LINKEDIN_PASSWORD")
    return email, password

# ───────────────────────── Enhanced helpers ─────────────────────────
async def wait_and_click(page, selector, timeout=10000, description="element"):
    """Enhanced click with better waiting and error handling"""
    try:
        element = page.locator(selector).first
        await element.wait_for(state="visible", timeout=timeout)
        await asyncio.sleep(0.5)
        await element.click(timeout=5000)
        await asyncio.sleep(1)
        return True
    except PWTimeout:
        return False
    except Exception:
        return False

async def safe_fill(page, selector, value, description="field"):
    """Safe form filling with error handling"""
    try:
        await page.wait_for_selector(selector, timeout=10000)
        await asyncio.sleep(0.5)
        await page.fill(selector, "")
        await asyncio.sleep(0.3)
        await page.fill(selector, value)
        await asyncio.sleep(0.5)
        return True
    except Exception:
        return False

async def close_banners_enhanced(page):
    """Enhanced banner closing with more selectors"""
    banner_selectors = [
        "button:has-text('Accept cookies')",
        "button:has-text('Accept')",
        "button[aria-label='Dismiss']",
        "button[aria-label='Close']",
        "button.artdeco-modal__dismiss",
        "button[data-tracking-control-name*='dismiss']",
        ".msg-overlay-bubble-header__dismiss",
        ".artdeco-toast-item__dismiss"
    ]
    
    for selector in banner_selectors:
        try:
            if await page.locator(selector).first.is_visible():
                await page.locator(selector).first.click(timeout=2000)
                await asyncio.sleep(0.5)
        except:
            continue
    
    await page.keyboard.press("Escape")
    await asyncio.sleep(1)

async def check_auth_status(page):
    """Check if we're properly authenticated"""
    auth_indicators = [
        ("nav[role='navigation']", True),
        (".global-nav", True),
        ("button[data-tracking-control-name*='nav']", True),
        ("button.sign-in-modal__outlet-btn", False),
        (".blurred_overlay__title", False),
        ("button:has-text('Sign in')", False),
    ]
    
    for selector, should_exist in auth_indicators:
        try:
            is_visible = await page.locator(selector).first.is_visible()
            if should_exist and is_visible:
                return True
            elif not should_exist and is_visible:
                return False
        except:
            continue
    
    if any(pattern in page.url for pattern in ["/authwall", "/login", "/checkpoint"]):
        return False
    
    return None

async def enhanced_tab_login(ctx, email, password, max_retries=3):
    """Enhanced login via new tab with retries"""
    for attempt in range(max_retries):
        tab = None
        try:
            tab = await ctx.new_page()
            await tab.goto("https://www.linkedin.com/login", timeout=30000)
            await asyncio.sleep(2)
            
            if not await safe_fill(tab, "#username", email, "email"):
                continue
            if not await safe_fill(tab, "#password", password, "password"):
                continue
            
            await asyncio.sleep(1)
            
            try:
                async with tab.expect_navigation(
                    url=lambda u: "/login" not in u and "/challenge" not in u, 
                    timeout=30000
                ):
                    await tab.click("button[type='submit']")
                    
                await asyncio.sleep(2)
                return True
                
            except PWTimeout:
                continue
                
        except Exception:
            continue
        finally:
            if tab:
                await tab.close()
                await asyncio.sleep(1)
    
    return False

async def enhanced_modal_login(page, email, password, max_retries=2):
    """Enhanced modal login with better handling"""
    for attempt in range(max_retries):
        try:
            if not await wait_and_click(page, "button.sign-in-modal__outlet-btn", description="sign-in button"):
                continue
            
            await asyncio.sleep(2)
            
            modal_email_selector = "input[name='session_key']"
            modal_pwd_selector = "input[name='session_password']"
            
            if not await safe_fill(page, modal_email_selector, email, "modal email"):
                continue
            if not await safe_fill(page, modal_pwd_selector, password, "modal password"):
                continue
            
            await asyncio.sleep(1)
            
            try:
                async with page.expect_navigation(url=lambda u: "/login" not in u, timeout=30000):
                    submit_clicked = await wait_and_click(page, "button[data-id='sign-in-form__submit-btn']", description="modal submit button")
                    if not submit_clicked:
                        continue
                
                await asyncio.sleep(2)
                return True
                
            except PWTimeout:
                continue
                
        except Exception:
            continue
    
    return False

async def scroll_page_slowly(page):
    """Scroll through the page to load all content"""
    scroll_distances = [400, 800, 1200, 1600, 2000, 2400, 2800]
    
    for i, distance in enumerate(scroll_distances):
        await page.mouse.wheel(0, distance - (scroll_distances[i-1] if i > 0 else 0))
        await asyncio.sleep(1.5)
        await close_banners_enhanced(page)

# ───────────────────────── Content extraction functions ─────────────────────────
LINKEDIN_EXTRACTION_SCHEMA = {
    "name": "LinkedIn Profile Extractor",
    "baseSelector": "body",
    "fields": [
        {
            "name": "name",
            "selector": "h1.text-heading-xlarge, h1[data-test-id='text-heading-xlarge'], .pv-text-details__left-panel h1",
            "type": "text"
        },
        {
            "name": "headline",
            "selector": ".text-body-medium.break-words, .pv-text-details__left-panel h2, .text-body-medium",
            "type": "text"
        },
        {
            "name": "location",
            "selector": ".text-body-small.inline.t-black--light.break-words, .pv-text-details__left-panel .text-body-small, .text-body-small",
            "type": "text"
        },
        {
            "name": "about",
            "selector": "#about ~ * .full-width, [data-section='summary'] .pv-about-section, .pv-about-section, .artdeco-card .pv-about-section",
            "type": "text"
        },
        {
            "name": "experience",
            "selector": "#experience ~ * .artdeco-list__item, .pv-profile-section__list-item, .pv-entity__summary-info",
            "type": "text",
            "many": True
        },
        {
            "name": "education",
            "selector": "#education ~ * .artdeco-list__item, .pv-education-section .pv-profile-section__list-item, .pv-entity__summary-info",
            "type": "text",
            "many": True
        },
        {
            "name": "skills",
            "selector": "#skills ~ * .artdeco-list__item, .pv-skill-category-entity, .pv-skill-entity",
            "type": "text",
            "many": True
        },
        {
            "name": "certifications",
            "selector": "#licenses_and_certifications ~ * .artdeco-list__item, .pv-certifications-section .pv-profile-section__list-item",
            "type": "text",
            "many": True
        }
    ]
}

def clean_text(text):
    """Clean extracted text content"""
    if not text:
        return ""
    
    text = re.sub(r'\s+', ' ', text.strip())
    
    ui_patterns = [
        r'Show more.*?Show less',
        r'See more.*?See less', 
        r'…see more',
        r'Show all \d+ experiences?',
        r'Show all \d+ educations?',
        r'\d+ mutual connections?',
        r'Connect\s*Message\s*More',
        r'Follow\s*Message\s*More',
        r'View profile.*?View profile',
        r'Send message.*?Send message'
    ]
    
    for pattern in ui_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    return text.strip()

def parse_experience_item(text):
    """Parse individual experience/education item"""
    if not text:
        return {}
    
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    result = {}
    
    if lines:
        result['title'] = lines[0]
    
    if len(lines) > 1:
        result['organization'] = lines[1]
    
    date_patterns = [
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}',
        r'\d{4}\s*[-–—]\s*\d{4}',
        r'\d{4}\s*[-–—]\s*Present',
        r'\d{1,2}/\d{4}'
    ]
    
    for line in lines:
        for pattern in date_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                result['duration'] = line
                break
    
    desc_lines = []
    for line in lines[2:]:
        is_duration = any(re.search(pattern, line, re.IGNORECASE) for pattern in date_patterns)
        if not is_duration:
            desc_lines.append(line)
    
    if desc_lines:
        result['description'] = ' '.join(desc_lines)
    
    return result

async def extract_with_crawl4ai(html_content, url):
    """Use crawl4ai to extract structured content"""
    if not CRAWL4AI_AVAILABLE:
        return manual_extraction_fallback(html_content)
    
    try:
        async with AsyncWebCrawler(verbose=False) as crawler:
            basic_data = {}
            markdown_content = ""
            
            # Method 1: CSS extraction
            try:
                extraction_strategy = JsonCssExtractionStrategy(
                    schema=LINKEDIN_EXTRACTION_SCHEMA,
                    verbose=False
                )
                
                result = await crawler.arun(
                    url=f"raw://{html_content}",
                    config=CrawlerRunConfig(
                        extraction_strategy=extraction_strategy,
                        cache_mode=CacheMode.BYPASS
                    )
                )
                
                if result.success and result.extracted_content:
                    try:
                        raw_data = json.loads(result.extracted_content)
                        basic_data = process_extracted_data(raw_data)
                    except json.JSONDecodeError:
                        pass
            except Exception:
                pass
            
            # Method 2: Get markdown content
            try:
                result = await crawler.arun(
                    url=f"raw://{html_content}",
                    config=CrawlerRunConfig(
                        cache_mode=CacheMode.BYPASS,
                        word_count_threshold=10,
                        excluded_tags=['script', 'style', 'nav', 'footer']
                    )
                )
                
                if result.success and hasattr(result, 'markdown'):
                    markdown_content = result.markdown.raw_markdown if hasattr(result.markdown, 'raw_markdown') else str(result.markdown)
                    
            except Exception:
                pass
            
            # Return results with markdown for external parsing
            result_data = basic_data if basic_data else manual_extraction_fallback(html_content)
            if markdown_content:
                result_data['markdown'] = markdown_content
                result_data['extraction_method'] = 'crawl4ai_with_markdown'
            
            return result_data
                
    except Exception:
        return manual_extraction_fallback(html_content)

def process_extracted_data(raw_data):
    """Process and clean the extracted data"""
    processed = {}
    
    if isinstance(raw_data, list) and len(raw_data) > 0:
        data = raw_data[0]
    elif isinstance(raw_data, dict):
        data = raw_data
    else:
        return {}
    
    # Clean basic fields
    for field in ['name', 'headline', 'location', 'about']:
        if field in data and data[field]:
            value = data[field]
            if isinstance(value, list) and value:
                value = value[0] if len(value) == 1 else ' '.join(value)
            if isinstance(value, str):
                processed[field] = clean_text(value)
    
    # Process experience items
    if 'experience' in data and data['experience']:
        processed['experience'] = []
        experiences = data['experience'] if isinstance(data['experience'], list) else [data['experience']]
        for exp in experiences:
            if isinstance(exp, str):
                parsed_exp = parse_experience_item(clean_text(exp))
                if parsed_exp:
                    processed['experience'].append(parsed_exp)
    
    # Process education items  
    if 'education' in data and data['education']:
        processed['education'] = []
        educations = data['education'] if isinstance(data['education'], list) else [data['education']]
        for edu in educations:
            if isinstance(edu, str):
                parsed_edu = parse_experience_item(clean_text(edu))
                if parsed_edu:
                    processed['education'].append(parsed_edu)
    
    # Process skills
    if 'skills' in data and data['skills']:
        skills_list = []
        skills = data['skills'] if isinstance(data['skills'], list) else [data['skills']]
        for skill in skills:
            if isinstance(skill, str):
                clean_skill = clean_text(skill)
                if clean_skill and len(clean_skill) < 100:
                    skills_list.append(clean_skill)
        processed['skills'] = skills_list
    
    # Process certifications
    if 'certifications' in data and data['certifications']:
        certs_list = []
        certs = data['certifications'] if isinstance(data['certifications'], list) else [data['certifications']]
        for cert in certs:
            if isinstance(cert, str) and clean_text(cert):
                certs_list.append(clean_text(cert))
        processed['certifications'] = certs_list
    
    return processed

def manual_extraction_fallback(html_content):
    """Enhanced manual extraction fallback using BeautifulSoup"""
    if not BS4_AVAILABLE:
        return {
            'extraction_method': 'raw_html_fallback',
            'note': 'Neither crawl4ai nor BeautifulSoup available - saved raw HTML only',
            'html_length': len(html_content)
        }
    
    soup = BeautifulSoup(html_content, 'html.parser')
    profile_data = {}
    
    # Enhanced name extraction
    name_selectors = [
        'h1.text-heading-xlarge',
        'h1[data-test-id="text-heading-xlarge"]',
        '.pv-text-details__left-panel h1',
        '.pv-top-card h1'
    ]
    
    name = ""
    for selector in name_selectors:
        element = soup.select_one(selector)
        if element:
            name = clean_text(element.get_text())
            if name:
                break
    profile_data['name'] = name
    
    # Enhanced headline extraction
    headline_selectors = [
        '.text-body-medium.break-words',
        '.pv-text-details__left-panel h2',
        '.text-body-medium',
        '.pv-top-card h2'
    ]
    
    headline = ""
    for selector in headline_selectors:
        element = soup.select_one(selector)
        if element:
            headline = clean_text(element.get_text())
            if headline and len(headline) > 10:
                break
    profile_data['headline'] = headline
    
    # Enhanced location extraction
    location_selectors = [
        '.text-body-small.inline.t-black--light.break-words',
        '.pv-text-details__left-panel .text-body-small',
        '.text-body-small',
        '.pv-top-card .text-body-small'
    ]
    
    location = ""
    for selector in location_selectors:
        elements = soup.select(selector)
        for element in elements:
            text = clean_text(element.get_text())
            if text and any(keyword in text.lower() for keyword in ['area', 'city', 'state', 'country', ',']):
                location = text
                break
        if location:
            break
    profile_data['location'] = location
    
    # Enhanced about section extraction
    about_selectors = [
        '.pv-about-section',
        '[data-section="summary"]',
        '.artdeco-card .pv-about-section'
    ]
    
    about = ""
    for selector in about_selectors:
        element = soup.select_one(selector)
        if element:
            about = clean_text(element.get_text())
            if about and len(about) > 20:
                break
    profile_data['about'] = about
    
    # Enhanced experience extraction
    experience_selectors = [
        '.pv-entity__summary-info',
        '.pv-profile-section__list-item',
        '.artdeco-list__item'
    ]
    
    experiences = []
    for selector in experience_selectors:
        elements = soup.select(selector)
        for element in elements:
            text = clean_text(element.get_text())
            if text and len(text) > 20:
                parsed_exp = parse_experience_item(text)
                if parsed_exp and parsed_exp.get('title'):
                    experiences.append(parsed_exp)
    profile_data['experience'] = experiences[:10]
    
    # Enhanced skills extraction
    skills_selectors = [
        '.pv-skill-entity',
        '.pv-skill-category-entity',
        '.artdeco-list__item'
    ]
    
    skills = []
    for selector in skills_selectors:
        elements = soup.select(selector)
        for element in elements:
            text = clean_text(element.get_text())
            if text and len(text) < 100 and len(text) > 2:
                skills.append(text)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_skills = []
    for skill in skills:
        if skill.lower() not in seen:
            seen.add(skill.lower())
            unique_skills.append(skill)
    
    profile_data['skills'] = unique_skills[:20]
    profile_data['extraction_method'] = 'enhanced_beautifulsoup'
    
    return profile_data

# ───────────────────────── Main scraping function ─────────────────────────
async def scrape_linkedin_profile_enhanced(profile_url, manual_input=None):
    """
    Enhanced LinkedIn profile scraper with multiple fallback methods
    Returns: dict with profile data and metadata
    """
    if manual_input:
        return {
            'markdown': manual_input,
            'extraction_method': 'manual_input',
            'profile_url': profile_url,
            'scraped_at': datetime.now().isoformat()
        }
    
    email, password = get_linkedin_credentials()
    if not (email and password):
        return {
            'error': 'LinkedIn credentials not found',
            'message': 'Set LINKEDIN_EMAIL and LINKEDIN_PASSWORD environment variables'
        }
    
    headless_mode = os.getenv("HEADLESS", "true").lower() == "true"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless_mode,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-gpu", 
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-images" if headless_mode else "",
                "--window-size=1440,900"
            ],
        )
        
        ctx = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            )
        )

        page = await ctx.new_page()
        
        try:
            await page.goto(profile_url, timeout=30000)
            
            if headless_mode:
                await asyncio.sleep(5)
            else:
                await asyncio.sleep(3)
            
            auth_status = await check_auth_status(page)
            
            # Handle authentication
            if "/login" in page.url or "/checkpoint" in page.url:
                if await enhanced_tab_login(ctx, email, password):
                    await page.goto(profile_url, timeout=30000)
                    await asyncio.sleep(3)
                else:
                    raise RuntimeError("Login failed")
            elif auth_status == False:
                if await enhanced_modal_login(page, email, password):
                    pass  # Already on the page
                else:
                    if await enhanced_tab_login(ctx, email, password):
                        await page.goto(profile_url, timeout=30000)
                        await asyncio.sleep(3)
                    else:
                        raise RuntimeError("All login methods failed")
            
            # Final auth check
            final_auth = await check_auth_status(page)
            if final_auth == False:
                raise RuntimeError("Still not authenticated after login attempts")
            
            await page.wait_for_selector("main", timeout=15000)
            await close_banners_enhanced(page)
            await asyncio.sleep(2)
            
            await scroll_page_slowly(page)
            
            html = await page.content()
            
            # Extract structured data
            profile_data = await extract_with_crawl4ai(html, profile_url)
            
            # Add metadata
            profile_data['metadata'] = {
                'profile_url': profile_url,
                'scraped_at': datetime.now().isoformat(),
                'html_length': len(html),
                'extraction_tool': 'enhanced_linkedin_scraper',
                'headless_mode': headless_mode
            }
            
            return profile_data
            
        except Exception as e:
            return {
                'error': 'Scraping failed',
                'details': str(e),
                'profile_url': profile_url
            }
        
        finally:
            await browser.close()

def fetch_linkedin_profile_sync(profile_url, manual_input=None):
    """
    Synchronous wrapper for the enhanced LinkedIn profile scraper
    """
    try:
        return asyncio.run(scrape_linkedin_profile_enhanced(profile_url, manual_input))
    except Exception as e:
        return {
            'error': 'MANUAL_INPUT_REQUIRED',
            'original_error': str(e),
            'profile_url': profile_url,
            'message': 'Enhanced scraping failed. Manual input required.'
        }

def format_linkedin_profile_as_markdown(profile_data):
    """
    Format the scraped profile data as markdown for display
    """
    if profile_data.get('error'):
        return f"**Error:** {profile_data['error']}\n\n{profile_data.get('message', '')}"
    
    markdown = ""
    
    # Basic information
    if profile_data.get('name'):
        markdown += f"# {profile_data['name']}\n\n"
    
    if profile_data.get('headline'):
        markdown += f"**{profile_data['headline']}**\n\n"
    
    if profile_data.get('location'):
        markdown += f"📍 {profile_data['location']}\n\n"
    
    # About section
    if profile_data.get('about'):
        markdown += f"## About\n{profile_data['about']}\n\n"
    
    # Experience
    if profile_data.get('experience'):
        markdown += "## Experience\n"
        for exp in profile_data['experience']:
            if exp.get('title'):
                markdown += f"**{exp['title']}**"
                if exp.get('organization'):
                    markdown += f" at {exp['organization']}"
                markdown += "\n"
                if exp.get('duration'):
                    markdown += f"*{exp['duration']}*\n"
                if exp.get('description'):
                    markdown += f"{exp['description']}\n"
                markdown += "\n"
    
    # Education
    if profile_data.get('education'):
        markdown += "## Education\n"
        for edu in profile_data['education']:
            if edu.get('title'):
                markdown += f"**{edu['title']}**"
                if edu.get('organization'):
                    markdown += f" - {edu['organization']}"
                markdown += "\n"
                if edu.get('duration'):
                    markdown += f"*{edu['duration']}*\n"
                markdown += "\n"
    
    # Skills
    if profile_data.get('skills'):
        markdown += "## Skills\n"
        skills_text = " • ".join(profile_data['skills'][:15])  # Limit display
        markdown += f"{skills_text}\n\n"
    
    # Use provided markdown if available and formatted version is empty
    if not markdown.strip() and profile_data.get('markdown'):
        return profile_data['markdown']
    
    return markdown if markdown.strip() else "No profile information available"