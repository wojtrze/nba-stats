from webdriver_manager.chrome import ChromeDriverManager

def install_chromedriver():
    driver_manager = ChromeDriverManager()
    driver_manager.install()
