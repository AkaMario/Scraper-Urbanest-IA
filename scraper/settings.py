BOT_NAME = "urbanest_scraper"

SPIDER_MODULES = ["scraper.spiders"]
NEWSPIDER_MODULE = "scraper.spiders"

ROBOTSTXT_OBEY = False
DOWNLOAD_DELAY = 0
AUTOTHROTTLE_ENABLED = True
CONCURRENT_REQUESTS_PER_DOMAIN = 4
USER_AGENT = "UrbanestIA/0.1 (+local ethical research bot)"
LOG_LEVEL = "INFO"
