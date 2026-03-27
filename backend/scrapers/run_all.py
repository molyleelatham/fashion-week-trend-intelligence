"""
Runs all three scrapers in sequence.
Run: python -m backend.scrapers.run_all
"""
from loguru import logger
from backend.scrapers import vogue, bof, reddit


def main():
    logger.info("=== Starting full scrape run ===")

    logger.info("--- Vogue Runway ---")
    try:
        vogue.scrape()
    except Exception as e:
        logger.error(f"Vogue scraper failed: {e}")

    logger.info("--- Business of Fashion ---")
    try:
        bof.scrape()
    except Exception as e:
        logger.error(f"BoF scraper failed: {e}")

    logger.info("--- Reddit ---")
    try:
        reddit.scrape()
    except Exception as e:
        logger.error(f"Reddit scraper failed: {e}")

    logger.info("=== Full scrape complete ===")


if __name__ == "__main__":
    main()
