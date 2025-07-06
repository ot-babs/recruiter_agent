import os
from dotenv import load_dotenv

load_dotenv()
class Settings:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-key-here")
    # For LinkedIn scraping (Selenium/Playwright config)
    BROWSER = os.getenv("SCRAPER_BROWSER", "chrome")  # could be "chrome", "firefox", etc.
    SLOW_MO = int(os.getenv("SCRAPER_SLOW_MO", 200))  # milliseconds between actions
    LI_AT_COOKIE=os.getenv("LI_AT_COOKIE","your_linkedin_cookie_value")


    # Add more config as needed (e.g. for database, debug mode, etc.)

settings = Settings()