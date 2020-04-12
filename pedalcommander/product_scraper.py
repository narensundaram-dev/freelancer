import logging
import argparse
import traceback
import configparser
from datetime import datetime as dt

import pandas as pd
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC


__author__ = "Narendran G"
__maintainer__ = "Narendran G"
__contact__ = "+91-8678910063"
__email__ = "narensundaram007@gmail.com"
__status__ = "Development"

log = logging.getLogger(__file__.split('/')[-1])


def config_logger(args):
    """
    This method is used to configure the logging format.

    :param args: script argument as `ArgumentParser instance`.
    :return: None
    """
    log_level = logging.INFO if args.log_level and args.log_level == 'INFO' else logging.DEBUG
    log.setLevel(log_level)
    log_handler = logging.StreamHandler()
    log_formatter = logging.Formatter('%(levelname)s: %(asctime)s - %(name)s:%(lineno)d - %(message)s')
    log_handler.setFormatter(log_formatter)
    log.addHandler(log_handler)


class ProductScraper(object):
    """
    Example urls:
        - Products page: https://pedalcommander.com/pages/product-result?rq=yr_2019~mk_nissan~md_titan~rk_platinum-reserve~qj_5-6
        - No products page: https://pedalcommander.com/pages/product-result?rq=yr_1998~mk_smart~md_fortwo-(450)~rk_all~qj_0-6
    """

    def __init__(self, args, conf, chrome, url):
        self.url = url
        self.args = args
        self.conf = conf
        self.chrome = chrome
        self.soup = None
        self.info = []

    @classmethod
    def setup(cls):
        pass

    @classmethod
    def cleanup(cls):
        pass

    def has_products(self):
        WebDriverWait(self.chrome, 60).until(EC.text_to_be_present_in_element((By.ID, "total_products"), 'Product'))
        soup = BeautifulSoup(self.chrome.page_source, "html.parser")
        summary = soup.find("span", attrs={"id": "total_products"}).get_text()
        return False if "no products" in summary.lower() else True

    def read(self):
        self.chrome.get(self.url)
        try:
            if self.has_products():
                WebDriverWait(self.chrome, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'product-thumb')))
                html = self.chrome.page_source
                self.soup = BeautifulSoup(html, "html.parser")
                dom_products = self.soup.find("div", attrs={"id": "products"})
                for dom_product in dom_products.find_all("div", attrs={"class": "product-thumb"}):
                    self.info.append({
                        "product_name": dom_product.next_sibling.next_element.get_text(),
                        "url": self.url,
                        "product_url": dom_product.next_element.attrs["href"],
                    })
            else:
                self.info.append({
                    "product_name": "No Products",
                    "url": self.url,
                    "product_url": "NA"
                })
            return self.info
        except (TimeoutException, BaseException) as e:
            log.debug(traceback.format_exc())
            log.error(e)


def get_args():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-log-level', '--log_level', type=str, choices=("INFO", "DEBUG"),
                            default="INFO", help='Where do you want to post the info?')
    return arg_parser.parse_args()


def get_conf():
    conf = configparser.ConfigParser()
    conf.read("conf.ini")
    return conf["CONFIG"]


def save(data):
    df = pd.DataFrame(data)
    df.to_excel("products.xlsx", index=False)


def main():
    args = get_args()
    config_logger(args)
    conf = get_conf()

    start = dt.now().strftime("%d-%m-%Y %H:%M:%S %p")
    log.info("Script starts at: {}".format(start))
    ProductScraper.setup()

    data = []
    chrome = webdriver.Chrome(conf["CHROME_DRIVER_PATH"])
    try:
        with open("links.txt", "r") as f:
            for url in f.readlines():
                scraper = ProductScraper(args, conf, chrome, url)
                info = scraper.read()
                data.extend(info)
                log.info("Fetched for: {}. Found: {}. Total: {}".format(url.strip(), len(info), len(data)))
    except BaseException as e:
        log.debug(e)
    finally:
        save(data)
        chrome.close()

    ProductScraper.cleanup()
    end = dt.now().strftime("%d-%m-%Y %H:%M:%S %p")
    log.info("Script ends at: {}".format(end))


if __name__ == '__main__':
    main()
