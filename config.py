# config.py - Updated to remove LinkedIn cookie dependencies

import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # OpenAI API for job parsing
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # Remove LinkedIn cookie dependency - we'll scrape without authentication
    # LI_AT_COOKIE = os.getenv("LI_AT_COOKIE", "")  # Commented out - no longer needed
    
    # Rate limiting settings for respectful scraping
    SCRAPING_DELAY_MIN = int(os.getenv("SCRAPING_DELAY_MIN", "2"))  # Minimum delay between requests
    SCRAPING_DELAY_MAX = int(os.getenv("SCRAPING_DELAY_MAX", "6"))  # Maximum delay between requests
    
    # Retry settings
    MAX_RETRY_ATTEMPTS = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
    RETRY_DELAY = int(os.getenv("RETRY_DELAY", "5"))
    
    # Alternative data sources configuration
    ENABLE_ALTERNATIVE_SOURCES = os.getenv("ENABLE_ALTERNATIVE_SOURCES", "true").lower() == "true"
    
    # Proxy settings (optional - for advanced users)
    USE_PROXY = os.getenv("USE_PROXY", "false").lower() == "true"
    PROXY_LIST = os.getenv("PROXY_LIST", "").split(",") if os.getenv("PROXY_LIST") else []
    
    # User agent rotation
    ROTATE_USER_AGENTS = os.getenv("ROTATE_USER_AGENTS", "true").lower() == "true"
    
    # Fallback to manual input threshold
    MIN_CONTENT_LENGTH = int(os.getenv("MIN_CONTENT_LENGTH", "200"))
    
    # Debug settings
    DEBUG_SCRAPING = os.getenv("DEBUG_SCRAPING", "false").lower() == "true"
    SAVE_SCRAPED_CONTENT = os.getenv("SAVE_SCRAPED_CONTENT", "false").lower() == "true"

settings = Settings()

# Additional utility functions for scraping configuration
def get_scraping_headers():
    """Generate clean headers without authentication"""
    import random
    
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0"
    ]
    
    return {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0"
        # Note: NO authentication cookies
    }

def get_browser_args():
    """Get browser arguments for stealth scraping"""
    return [
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
        "--disable-back-forward-cache",
        "--disable-ipc-flooding-protection",
        "--enable-features=NetworkService,NetworkServiceInProcess",
        "--disable-component-extensions-with-background-pages",
        "--disable-background-networking"
    ]

# Environment variable template for .env file
ENV_TEMPLATE = """
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# LinkedIn Cookie (REMOVED - no longer needed)
# LI_AT_COOKIE=  # This is now obsolete and should not be used

# Scraping Configuration
SCRAPING_DELAY_MIN=2
SCRAPING_DELAY_MAX=6
MAX_RETRY_ATTEMPTS=3
RETRY_DELAY=5

# Advanced Options (optional)
ENABLE_ALTERNATIVE_SOURCES=true
USE_PROXY=false
PROXY_LIST=
ROTATE_USER_AGENTS=true
MIN_CONTENT_LENGTH=200

# Debug Options
DEBUG_SCRAPING=false
SAVE_SCRAPED_CONTENT=false
"""