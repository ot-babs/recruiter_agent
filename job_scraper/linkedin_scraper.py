import asyncio
import random
import time
from urllib.parse import urlparse, parse_qs
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
import requests
from fake_useragent import UserAgent

class LinkedInScraperEnhanced:
    def __init__(self):
        self.ua = UserAgent()
        self.session_delays = [2, 3, 4, 5, 6]  # Random delays between requests
        
    def get_random_user_agent(self):
        """Generate realistic user agents"""
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
        ]
        return random.choice(agents)
    
    def get_clean_browser_config(self):
        """Browser config without authentication - appears as regular visitor"""
        return BrowserConfig(
            headless=True,
            browser_type="chromium",
            viewport_width=random.randint(1366, 1920),
            viewport_height=random.randint(768, 1080),
            headers={
                "User-Agent": self.get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Cache-Control": "no-cache",
                # NO COOKIES - this is key
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
                "--disable-sync",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-field-trial-config",
                "--disable-back-forward-cache"
            ],
            verbose=False  # Reduce logs for stealth
        )
    
    def get_human_like_crawl_config(self):
        """Simulate realistic human browsing patterns"""
        return CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            js_code=[
                # Simulate realistic human scrolling
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
            page_timeout=45000,  # Longer timeout for natural loading
            delay_before_return_html=random.uniform(3.0, 6.0),
            remove_overlay_elements=True,
            process_iframes=False,  # Reduce complexity
            magic=True,
            simulate_user=True,
            word_count_threshold=50
        )

    async def scrape_with_fallback(self, url: str, scrape_type: str = "job") -> dict:
        """
        Primary scraping method with intelligent fallback strategy
        """
        
        # Method 1: Direct scraping (no auth)
        try:
            result = await self._scrape_unauthenticated(url, scrape_type)
            if result.get("success") and len(result.get("content", "")) > 200:
                return result
        except Exception as e:
            print(f"Method 1 failed: {str(e)}")
        
        # Method 2: Public LinkedIn endpoint scraping
        try:
            result = await self._scrape_public_endpoint(url, scrape_type)
            if result.get("success"):
                return result
        except Exception as e:
            print(f"Method 2 failed: {str(e)}")
            
        # Method 3: Alternative data sources
        try:
            result = await self._scrape_alternative_sources(url, scrape_type)
            if result.get("success"):
                return result
        except Exception as e:
            print(f"Method 3 failed: {str(e)}")
        
        # Final fallback: Manual input required
        return self._create_manual_fallback(url, scrape_type)
    
    async def _scrape_unauthenticated(self, url: str, scrape_type: str) -> dict:
        """Scrape without authentication - gets public data only"""
        
        # Random delay before scraping
        await asyncio.sleep(random.choice(self.session_delays))
        
        browser_config = self.get_clean_browser_config()
        crawl_config = self.get_human_like_crawl_config()
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=url, config=crawl_config)
            
            if result.success and len(result.markdown.strip()) > 200:
                return {
                    "success": True,
                    "content": result.markdown,
                    "html": result.cleaned_html,
                    "method": "unauthenticated_direct",
                    "url": url
                }
            else:
                return {"success": False, "error": "Insufficient content or blocked"}
    
    async def _scrape_public_endpoint(self, url: str, scrape_type: str) -> dict:
        """Try to access LinkedIn's public-facing endpoints"""
        
        if "/jobs/view/" in url:
            # Extract job ID and try public job endpoint
            job_id = self._extract_job_id(url)
            if job_id:
                public_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
                return await self._fetch_api_endpoint(public_url, "job_api")
        
        elif "/company/" in url:
            # Try public company page
            public_url = url.replace("/company/", "/company/") + "?trk=public_profile"
            return await self._scrape_unauthenticated(public_url, "company")
            
        return {"success": False, "error": "No public endpoint available"}
    
    async def _fetch_api_endpoint(self, api_url: str, endpoint_type: str) -> dict:
        """Fetch from LinkedIn's API endpoints that don't require auth"""
        
        headers = {
            "User-Agent": self.get_random_user_agent(),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://www.linkedin.com/",
            "Connection": "keep-alive",
        }
        
        try:
            # Use requests for API calls (faster than browser)
            response = requests.get(api_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "content": response.text,
                    "method": f"api_{endpoint_type}",
                    "url": api_url
                }
            else:
                return {"success": False, "error": f"API returned {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": f"API call failed: {str(e)}"}
    
    async def _scrape_alternative_sources(self, url: str, scrape_type: str) -> dict:
        """Use alternative job board aggregators that mirror LinkedIn data"""
        
        alternatives = {
            "job": [
                "https://www.indeed.com",
                "https://www.glassdoor.com", 
                "https://www.ziprecruiter.com"
            ],
            "company": [
                "https://www.crunchbase.com",
                "https://www.glassdoor.com"
            ]
        }
        
        # This would require implementing specific scrapers for each alternative
        # For now, return failure to trigger manual input
        return {"success": False, "error": "Alternative sources not implemented"}
    
    def _create_manual_fallback(self, url: str, scrape_type: str) -> dict:
        """Create manual input prompt when all scraping fails"""
        return {
            "success": False,
            "error": "MANUAL_INPUT_REQUIRED",
            "url": url,
            "scrape_type": scrape_type,
            "instructions": {
                "message": f"Automated {scrape_type} scraping failed. Please provide the information manually.",
                "steps": [
                    f"1. Open the LinkedIn {scrape_type} URL in your browser",
                    f"2. Copy the relevant {scrape_type} information",
                    "3. Paste it in the manual input field",
                    "4. Click 'Parse Information' to proceed"
                ]
            }
        }
    
    def _extract_job_id(self, url: str) -> str:
        """Extract job ID from LinkedIn URL"""
        import re
        match = re.search(r'/jobs/view/(\d+)', url)
        return match.group(1) if match else None

# Usage functions that replace your existing scrapers
async def scrape_linkedin_job_enhanced(job_url: str) -> dict:
    """Enhanced job scraping without account detection risk"""
    scraper = LinkedInScraperEnhanced()
    return await scraper.scrape_with_fallback(job_url, "job")

async def scrape_linkedin_company_enhanced(company_url: str) -> dict:
    """Enhanced company scraping without account detection risk"""
    scraper = LinkedInScraperEnhanced()
    return await scraper.scrape_with_fallback(company_url, "company")

async def scrape_linkedin_recruiter_enhanced(recruiter_url: str) -> dict:
    """Enhanced recruiter scraping without account detection risk"""
    scraper = LinkedInScraperEnhanced()
    return await scraper.scrape_with_fallback(recruiter_url, "recruiter")

# Synchronous wrappers for compatibility
def fetch_linkedin_job_enhanced(job_url: str, manual_job_text: str = None) -> dict:
    """Drop-in replacement for your existing fetch_linkedin_job_sync"""
    if manual_job_text and manual_job_text.strip():
        # Handle manual input same as before
        return {
            "url": job_url,
            "markdown": format_manual_job_text(manual_job_text, job_url),
            "html": "",
            "metadata": parse_manual_job_data(manual_job_text, job_url)
        }
    
    # Use enhanced scraping
    result = asyncio.run(scrape_linkedin_job_enhanced(job_url))
    
    if result.get("success"):
        return {
            "url": job_url,
            "markdown": result["content"],
            "html": result.get("html", ""),
            "metadata": parse_job_content(result["content"], job_url),
            "method": result.get("method", "unknown")
        }
    else:
        return {
            "url": job_url,
            "error": result.get("error", "Unknown error"),
            "markdown": "",
            "html": "",
            "metadata": {}
        }

# Helper functions (implement these based on your existing parsing logic)
def format_manual_job_text(job_text: str, job_url: str) -> str:
    """Format manual job text - reuse your existing implementation"""
    pass

def parse_manual_job_data(job_text: str, job_url: str) -> dict:
    """Parse manual job data - reuse your existing implementation"""
    pass

def parse_job_content(content: str, job_url: str) -> dict:
    """Parse job content - reuse your existing implementation"""
    pass