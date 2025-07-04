import os

class Settings:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-key-here")
    # For LinkedIn scraping (Selenium/Playwright config)
    BROWSER = os.getenv("SCRAPER_BROWSER", "chrome")  # could be "chrome", "firefox", etc.
    SLOW_MO = int(os.getenv("SCRAPER_SLOW_MO", 200))  # milliseconds between actions

    # Add more config as needed (e.g. for database, debug mode, etc.)

settings = Settings()