"""
auto_scrape_improved.py – Robust LinkedIn profile scraper with JSON extraction
──────────────────────────────────────────────────────────────────────────────
$ export LINKEDIN_EMAIL="you@example.com"
$ export LINKEDIN_PASSWORD="••••••••"
$ python auto_scrape_improved.py

# Run in headless mode (default):
$ python auto_scrape_improved.py

# Run with visible browser (for debugging):
$ export HEADLESS=false
$ python auto_scrape_improved.py

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
    # FIXED: Import missing required classes
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

PROFILE_URL  = "https://www.linkedin.com/in/otbabs/"
STATE_FILE   = Path("linkedin_state.json")

EMAIL = os.getenv("LINKEDIN_EMAIL")
PWD   = os.getenv("LINKEDIN_PASSWORD")
if not (EMAIL and PWD):
    sys.exit("❌  Set LINKEDIN_EMAIL and LINKEDIN_PASSWORD env vars first.")

# ───────────────────────── Enhanced helpers ─────────────────────────
async def save_state(ctx): 
    try:
        state = await ctx.storage_state()
        STATE_FILE.write_text(json.dumps(state))
        print("💾  Auth state saved successfully")
    except Exception as e:
        print(f"⚠️  Failed to save state: {e}")

async def load_state():    
    if STATE_FILE.exists():
        try:
            return {"storage_state": json.loads(STATE_FILE.read_text())}
        except Exception as e:
            print(f"⚠️  Failed to load state: {e}")
            STATE_FILE.unlink(missing_ok=True)
    return {}

async def wait_and_click(page, selector, timeout=10000, description="element"):
    """Enhanced click with better waiting and error handling"""
    try:
        print(f"🎯  Looking for {description}: {selector}")
        element = page.locator(selector).first
        await element.wait_for(state="visible", timeout=timeout)
        await asyncio.sleep(0.5)  # Small pause before clicking
        await element.click(timeout=5000)
        await asyncio.sleep(1)  # Pause after clicking
        print(f"✅  Clicked {description}")
        return True
    except PWTimeout:
        print(f"⏰  Timeout waiting for {description}")
        return False
    except Exception as e:
        print(f"❌  Error clicking {description}: {e}")
        return False

async def safe_fill(page, selector, value, description="field"):
    """Safe form filling with error handling"""
    try:
        await page.wait_for_selector(selector, timeout=10000)
        await asyncio.sleep(0.5)
        await page.fill(selector, "")  # Clear first
        await asyncio.sleep(0.3)
        await page.fill(selector, value)
        await asyncio.sleep(0.5)
        print(f"✅  Filled {description}")
        return True
    except Exception as e:
        print(f"❌  Error filling {description}: {e}")
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
    
    # Press escape as fallback
    await page.keyboard.press("Escape")
    await asyncio.sleep(1)

async def check_auth_status(page):
    """Check if we're properly authenticated"""
    auth_indicators = [
        # Signs we're logged in
        ("nav[role='navigation']", True),
        (".global-nav", True),
        ("button[data-tracking-control-name*='nav']", True),
        
        # Signs we're not logged in
        ("button.sign-in-modal__outlet-btn", False),
        (".blurred_overlay__title", False),
        ("button:has-text('Sign in')", False),
    ]
    
    for selector, should_exist in auth_indicators:
        try:
            is_visible = await page.locator(selector).first.is_visible()
            if should_exist and is_visible:
                print(f"✅  Auth indicator found: {selector}")
                return True
            elif not should_exist and is_visible:
                print(f"❌  Login required indicator: {selector}")
                return False
        except:
            continue
    
    # Check URL patterns
    if any(pattern in page.url for pattern in ["/authwall", "/login", "/checkpoint"]):
        print(f"❌  Auth required (URL): {page.url}")
        return False
    
    print("🤔  Auth status unclear, proceeding cautiously")
    return None

async def enhanced_tab_login(ctx, max_retries=3):
    """Enhanced login via new tab with retries"""
    for attempt in range(max_retries):
        tab = None
        try:
            print(f"🔐  Login attempt {attempt + 1}/{max_retries}")
            tab = await ctx.new_page()
            
            await tab.goto("https://www.linkedin.com/login", timeout=30000)
            await asyncio.sleep(2)
            
            # Fill credentials
            if not await safe_fill(tab, "#username", EMAIL, "email"):
                continue
            if not await safe_fill(tab, "#password", PWD, "password"):
                continue
            
            # Submit form
            print("🚀  Submitting login form...")
            await asyncio.sleep(1)
            
            # Wait for navigation away from login page
            try:
                async with tab.expect_navigation(
                    url=lambda u: "/login" not in u and "/challenge" not in u, 
                    timeout=30000
                ):
                    await tab.click("button[type='submit']")
                    
                print("✅  Login successful!")
                await asyncio.sleep(2)
                return True
                
            except PWTimeout:
                print("⏰  Login navigation timeout")
                continue
                
        except Exception as e:
            print(f"❌  Login attempt failed: {e}")
            continue
        finally:
            if tab:
                await tab.close()
                await asyncio.sleep(1)
    
    return False

async def enhanced_modal_login(page, max_retries=2):
    """Enhanced modal login with better handling"""
    for attempt in range(max_retries):
        try:
            print(f"🔐  Modal login attempt {attempt + 1}/{max_retries}")
            
            # Click the sign-in button to open modal
            if not await wait_and_click(
                page, 
                "button.sign-in-modal__outlet-btn", 
                description="sign-in button"
            ):
                continue
            
            # Wait for modal to appear
            await asyncio.sleep(2)
            
            # Fill modal form
            modal_email_selector = "input[name='session_key']"
            modal_pwd_selector = "input[name='session_password']"
            
            if not await safe_fill(page, modal_email_selector, EMAIL, "modal email"):
                continue
            if not await safe_fill(page, modal_pwd_selector, PWD, "modal password"):
                continue
            
            # Submit modal form
            print("🚀  Submitting modal login...")
            await asyncio.sleep(1)
            
            try:
                async with page.expect_navigation(
                    url=lambda u: "/login" not in u, 
                    timeout=30000
                ):
                    submit_clicked = await wait_and_click(
                        page,
                        "button[data-id='sign-in-form__submit-btn']",
                        description="modal submit button"
                    )
                    if not submit_clicked:
                        continue
                
                print("✅  Modal login successful!")
                await asyncio.sleep(2)
                return True
                
            except PWTimeout:
                print("⏰  Modal login navigation timeout")
                continue
                
        except Exception as e:
            print(f"❌  Modal login failed: {e}")
            continue
    
    return False

async def scroll_page_slowly(page):
    """Scroll through the page to load all content"""
    print("📜  Scrolling page slowly...")
    
    scroll_distances = [400, 800, 1200, 1600, 2000, 2400, 2800]
    
    for i, distance in enumerate(scroll_distances):
        print(f"   Scroll {i + 1}/{len(scroll_distances)} (to {distance}px)")
        await page.mouse.wheel(0, distance - (scroll_distances[i-1] if i > 0 else 0))
        await asyncio.sleep(1.5)  # Longer pauses
        
        # Close any popups that might appear
        await close_banners_enhanced(page)

# ───────────────────────── Content extraction functions ─────────────────────────
# Updated schema format for crawl4ai 0.7.0
LINKEDIN_EXTRACTION_SCHEMA = {
    "name": "LinkedIn Profile Extractor",
    "baseSelector": "body",  # Extract from the entire page
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
    
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove common LinkedIn UI elements
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
    
    # Try to extract title (usually first line)
    if lines:
        result['title'] = lines[0]
    
    # Try to extract company/organization (usually second line)  
    if len(lines) > 1:
        result['organization'] = lines[1]
    
    # Look for date patterns
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
    
    # Extract description (remaining lines)
    desc_lines = []
    for line in lines[2:]:  # Skip title and company
        # Skip duration lines
        is_duration = any(re.search(pattern, line, re.IGNORECASE) 
                         for pattern in date_patterns)
        if not is_duration:
            desc_lines.append(line)
    
    if desc_lines:
        result['description'] = ' '.join(desc_lines)
    
    return result

async def extract_with_crawl4ai(html_content, url):
    """Use crawl4ai to extract structured content - FIXED VERSION"""
    if not CRAWL4AI_AVAILABLE:
        print("⚠️  Crawl4ai not available, using manual extraction")
        return manual_extraction_fallback(html_content)
    
    try:
        async with AsyncWebCrawler(verbose=False) as crawler:
            # Try Method 1: JsonCssExtractionStrategy with corrected schema
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
                        return process_extracted_data(raw_data)
                    except json.JSONDecodeError as e:
                        print(f"⚠️  JSON parsing failed: {e}")
                        # Fall through to Method 2
            except Exception as e:
                print(f"⚠️  JsonCssExtractionStrategy failed: {e}")
            
            # Try Method 2: Use markdown conversion and manual parsing
            try:
                print("🔄  Trying markdown conversion approach...")
                result = await crawler.arun(
                    url=f"raw://{html_content}",
                    config=CrawlerRunConfig(
                        cache_mode=CacheMode.BYPASS,
                        word_count_threshold=10,
                        excluded_tags=['script', 'style', 'nav', 'footer']
                    )
                )
                
                if result.success and hasattr(result, 'markdown'):
                    # Extract data from markdown
                    markdown_text = result.markdown.raw_markdown if hasattr(result.markdown, 'raw_markdown') else str(result.markdown)
                    return extract_from_markdown(markdown_text)
                    
            except Exception as e:
                print(f"⚠️  Markdown conversion failed: {e}")
            
            # If both methods fail, use manual extraction
            print("⚠️  All crawl4ai methods failed, falling back to manual parsing")
            return manual_extraction_fallback(html_content)
                
    except Exception as e:
        print(f"⚠️  Crawl4ai error: {e}, falling back to manual parsing")
        return manual_extraction_fallback(html_content)

def extract_from_markdown(markdown_text):
    """Extract profile data from markdown text"""
    profile_data = {}
    
    lines = markdown_text.split('\n')
    
    # Extract name (usually the first major heading)
    for line in lines[:20]:  # Check first 20 lines
        if line.strip().startswith('#') and not line.strip().startswith('##'):
            profile_data['name'] = clean_text(line.replace('#', '').strip())
            break
    
    # Extract headline (usually follows the name)
    for i, line in enumerate(lines[:30]):
        if profile_data.get('name') and profile_data['name'] in line:
            # Check next few lines for headline
            for j in range(i+1, min(i+5, len(lines))):
                if lines[j].strip() and not lines[j].startswith('#'):
                    profile_data['headline'] = clean_text(lines[j])
                    break
            break
    
    # Extract sections using common LinkedIn section markers
    section_markers = {
        'about': ['About', 'Summary'],
        'experience': ['Experience', 'Work Experience', 'Employment'],
        'education': ['Education', 'Academic'],
        'skills': ['Skills', 'Technical Skills', 'Competencies'],
        'certifications': ['Licenses', 'Certifications', 'Certificates']
    }
    
    current_section = None
    section_content = []
    
    for line in lines:
        # Check if this line is a section header
        for section, markers in section_markers.items():
            if any(marker in line and (line.startswith('#') or line.isupper()) for marker in markers):
                # Save previous section
                if current_section and section_content:
                    process_section_content(profile_data, current_section, section_content)
                
                current_section = section
                section_content = []
                break
        else:
            # Not a section header, add to current section
            if current_section and line.strip():
                section_content.append(line)
    
    # Process last section
    if current_section and section_content:
        process_section_content(profile_data, current_section, section_content)
    
    return profile_data

def process_section_content(profile_data, section, content):
    """Process content for a specific section"""
    if section == 'about':
        profile_data['about'] = clean_text(' '.join(content))
    
    elif section in ['experience', 'education']:
        items = []
        current_item = []
        
        for line in content:
            # New item markers (bullets, numbers, or significant spacing)
            if (line.strip().startswith(('•', '-', '*', '·')) or 
                (len(current_item) > 2 and line.strip() and 
                 any(pattern in line for pattern in ['at ', 'At ', ' - ', ' | ']))):
                
                if current_item:
                    item_text = '\n'.join(current_item)
                    parsed = parse_experience_item(clean_text(item_text))
                    if parsed:
                        items.append(parsed)
                current_item = [line]
            else:
                current_item.append(line)
        
        # Process last item
        if current_item:
            item_text = '\n'.join(current_item)
            parsed = parse_experience_item(clean_text(item_text))
            if parsed:
                items.append(parsed)
        
        profile_data[section] = items
    
    elif section == 'skills':
        skills = []
        for line in content:
            # Remove bullets and clean
            cleaned = clean_text(line.strip('•-*·● '))
            if cleaned and len(cleaned) < 100:
                skills.append(cleaned)
        profile_data['skills'] = skills[:20]  # Limit skills

def process_extracted_data(raw_data):
    """Process and clean the extracted data"""
    processed = {}
    
    # Handle the new data structure from crawl4ai 0.7.0
    # If raw_data is a list, take the first item (since we're using body as baseSelector)
    if isinstance(raw_data, list) and len(raw_data) > 0:
        data = raw_data[0]
    elif isinstance(raw_data, dict):
        data = raw_data
    else:
        print(f"⚠️  Unexpected data structure: {type(raw_data)}")
        return {}
    
    # Clean basic fields
    for field in ['name', 'headline', 'location', 'about']:
        if field in data and data[field]:
            # Handle both string and list values
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
                if clean_skill and len(clean_skill) < 100:  # Filter out long descriptions
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
            if name:  # Only break if we found actual text
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
            if headline and len(headline) > 10:  # Make sure it's substantial
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
            # Look for location-like patterns
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
            if about and len(about) > 20:  # Make sure it's substantial
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
            if text and len(text) > 20:  # Filter out short snippets
                parsed_exp = parse_experience_item(text)
                if parsed_exp and parsed_exp.get('title'):
                    experiences.append(parsed_exp)
    profile_data['experience'] = experiences[:10]  # Limit to prevent duplication
    
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
            if text and len(text) < 100 and len(text) > 2:  # Reasonable skill length
                skills.append(text)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_skills = []
    for skill in skills:
        if skill.lower() not in seen:
            seen.add(skill.lower())
            unique_skills.append(skill)
    
    profile_data['skills'] = unique_skills[:20]  # Limit to prevent noise
    
    # Add extraction metadata
    profile_data['extraction_method'] = 'enhanced_beautifulsoup'
    profile_data['note'] = 'Enhanced manual extraction with better selectors and parsing'
    
    return profile_data

# ───────────────────────── Enhanced main ─────────────────────────
async def main():
    # Set to True for headless mode, False for debugging
    HEADLESS_MODE = os.getenv("HEADLESS", "true").lower() == "true"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS_MODE,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-gpu", 
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-images" if HEADLESS_MODE else "",  # Faster loading in headless
                "--disable-javascript-harmony-shipping",
                "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding",
                "--disable-backgrounding-occluded-windows",
                "--disable-ipc-flooding-protection",
                "--window-size=1440,900"
            ],
        )
        
        ctx = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            **await load_state(),
        )

        page = await ctx.new_page()
        
        try:
            print(f"[1] 🌐  Navigating to {PROFILE_URL}")
            await page.goto(PROFILE_URL, timeout=30000)
            
            # Extra pause in headless mode for stability
            if HEADLESS_MODE:
                await asyncio.sleep(5)
            else:
                await asyncio.sleep(3)
            
            # Check initial auth status
            auth_status = await check_auth_status(page)
            
            # Handle different auth scenarios
            if "/login" in page.url or "/checkpoint" in page.url:
                print("[2] 🔄  Redirected to login page")
                if await enhanced_tab_login(ctx):
                    await save_state(ctx)
                    print("🔄  Retrying profile page...")
                    await page.goto(PROFILE_URL, timeout=30000)
                    await asyncio.sleep(3)
                else:
                    raise RuntimeError("❌  Tab login failed")
            
            elif auth_status == False:
                print("[2] 🔍  Login overlay detected")
                if await enhanced_modal_login(page):
                    await save_state(ctx)
                else:
                    print("🔄  Trying tab login as fallback...")
                    if await enhanced_tab_login(ctx):
                        await save_state(ctx)
                        await page.goto(PROFILE_URL, timeout=30000)
                        await asyncio.sleep(3)
                    else:
                        raise RuntimeError("❌  All login methods failed")
            
            # Final auth check
            final_auth = await check_auth_status(page)
            if final_auth == False:
                raise RuntimeError("❌  Still not authenticated after login attempts")
            
            print("[3] 🧹  Cleaning up page...")
            await page.wait_for_selector("main", timeout=15000)
            await close_banners_enhanced(page)
            await asyncio.sleep(2)
            
            print("[4] 📜  Scrolling page...")
            await scroll_page_slowly(page)
            
            print("[5] 📄  Extracting content...")
            html = await page.content()
            print(f"     Raw HTML: {len(html):,} characters")
            
            # Extract structured data
            print("[6] 🔍  Processing with crawl4ai...")
            profile_data = await extract_with_crawl4ai(html, PROFILE_URL)
            
            # Add metadata
            profile_data['metadata'] = {
                'profile_url': PROFILE_URL,
                'scraped_at': datetime.now().isoformat(),
                'html_length': len(html),
                'extraction_tool': 'crawl4ai + playwright' if CRAWL4AI_AVAILABLE else 'manual + playwright',
                'headless_mode': HEADLESS_MODE
            }
            
            # Save results
            timestamp = int(time.time())
            
            # Save JSON
            json_file = Path(f"profile_{timestamp}.json")
            json_file.write_text(json.dumps(profile_data, indent=2, ensure_ascii=False))
            
            # Save HTML backup
            html_file = Path(f"profile_{timestamp}.html")
            html_file.write_text(html, encoding='utf-8')
            
            print(f"\n🎉  SUCCESS!")
            print(f"    📄  JSON data: {json_file} ({json_file.stat().st_size:,} bytes)")
            print(f"    🌐  HTML backup: {html_file} ({html_file.stat().st_size:,} bytes)")
            print(f"    👤  Profile: {profile_data.get('name', 'Unknown')}")
            if profile_data.get('headline'):
                print(f"    💼  Headline: {profile_data['headline'][:60]}...")
            if 'experience' in profile_data:
                print(f"    🏢  Experience items: {len(profile_data['experience'])}")
            if 'skills' in profile_data:
                print(f"    🔧  Skills found: {len(profile_data['skills'])}")
            
        except Exception as e:
            print(f"💥  Script failed: {e}")
            
            # Save screenshot for debugging
            try:
                await page.screenshot(path="error_screenshot.png")
                print("📸  Error screenshot saved: error_screenshot.png")
            except:
                pass
        
        finally:
            await asyncio.sleep(2)  # Final pause
            await browser.close()

if __name__ == "__main__":
    headless_status = "headless" if os.getenv("HEADLESS", "true").lower() == "true" else "visible"
    extraction_method = "crawl4ai + manual fallback" if CRAWL4AI_AVAILABLE else "manual extraction only"
    print(f"🚀  Starting enhanced LinkedIn scraper in {headless_status} mode...")
    print(f"📊  Extraction method: {extraction_method}")
    asyncio.run(main())