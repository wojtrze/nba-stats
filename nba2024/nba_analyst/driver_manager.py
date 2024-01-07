from webdriver_manager.chrome import ChromeDriverManager
import logging
import time
from selenium import webdriver

logger = logging.getLogger(__name__)
def install_chromedriver():
    driver_manager = ChromeDriverManager()

    # Check if driver is already installed
    try:
        # Attempt to start a Chrome webdriver
        driver = webdriver.Chrome()
        driver.quit()
    except Exception:
        # Driver not installed, proceed with installation
        pass
    else:
        logger.info("ChromeDriver already installed.")
        return

    # Install ChromeDriver using a retry mechanism
    for attempt in range(5):
        logger.info(f"Attempting ChromeDriver installation (attempt {attempt + 1})...")
        try:
            driver_manager.install()
        except Exception as e:
            logger.error(f"Error installing ChromeDriver: {e}")
            time.sleep(2 ** attempt)  # Exponential backoff
        else:
            logger.info("ChromeDriver installation successful.")
            break
    else:
        logger.error("Failed to install ChromeDriver after 5 attempts.")
        raise RuntimeError("Failed to install ChromeDriver.")