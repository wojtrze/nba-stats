# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import requests
import lxml
from bs4 import BeautifulSoup
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
import html5lib

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:20.0) Gecko/20100101 Firefox/20.0'}


def get_historical_results():
    url = f'https://www.wynikilotto.net.pl/lotto/wyniki/'
    page = requests.get(url, headers)
    soup = BeautifulSoup(page.text, 'html.parser')
    table_body = soup.find_all('table')
    result_df = pd.read_html(str(table_body))
    return result_df


# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    DRIVER_PATH = 'C:\chromedriver\chromedriver.exe'
    driver = webdriver.Chrome(executable_path=DRIVER_PATH)
    driver.get('https://www.wynikilotto.net.pl/lotto/wyniki/')
    ile = driver.find_element(By.XPATH, "//select[@name='ile']")
    select = Select(ile)
    select.select_by_visible_text("Wszystkie")
    OK_button = driver.find_element(By.XPATH, "//button[text()='OK']")
    OK_button.click()
    results_table = driver.find_element(By.XPATH, "//table[@class='tabela']").get_attribute("outerHTML")
    df = pd.read_html(str(results_table))
    print(df)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
