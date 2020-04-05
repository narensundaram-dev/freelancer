import os
import time
import shutil
import logging
import argparse
import configparser
from datetime import datetime as dt

import requests
import pandas as pd
from bs4 import BeautifulSoup, Tag, NavigableString

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC


__author__ = "Narendran G"
__email__ = "narensundaram007@gmail.com / +91-8678910063"
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


class WebsiteContentModified(Exception):
    pass


class Product(object):

    def __init__(self, id, soup, destination):
        log.info("Getting information for product id: {}".format(id))
        self.id = id.strip()
        self.soup = soup
        self.destination = destination
        self.product_path = os.path.join(self.destination, "{}") + "-" + self.id

    @property
    def name(self):
        try:
            name = r"{}".format(self.soup.head.find("meta", attrs={"name": "twitter:title"}).attrs["content"])
            name = name.replace("/", " ").replace('"', "").replace("'", "").strip()
            path = self.product_path.format(name)
            os.makedirs(path, exist_ok=True)
            return name
        except (Exception, WebsiteContentModified) as e:
            log.debug("Product name is missing for product with id: {}".format(self.id))
            return ""

    @property
    def description(self):
        try:
            descriptions = self.soup.body.find("div", attrs={"class": "ProductDescriptions"})
            children = list(list(descriptions.children)[1].children)
            children_filtered = list(filter(lambda x: not isinstance(x, NavigableString), children))
            return "\n".join(list(map(lambda x: x.get_text(), children_filtered)))
        except (Exception, WebsiteContentModified) as e:
            log.debug("Product description is missing for product with id: {}".format(self.id))
            return ""

    @property
    def price(self):
        try:
            return float(self.soup.head.find("meta", attrs={"property": "og:price:amount"}).attrs["content"])
        except (Exception, WebsiteContentModified) as e:
            log.debug("Product price is missing for product with id: {}".format(self.id))
            return 0.0

    @property
    def currency(self):
        try:
            return self.soup.head.find("meta", attrs={"property": "og:price:currency"}).attrs["content"]
        except (Exception, WebsiteContentModified) as e:
            log.debug("Product price currency is missing for product with id: {}".format(self.id))
            return ""

    @property
    def price_gbp(self):
        try:
            if self.currency == "GBP":
                return self.price
            elif self.currency == "USD":
                return round(self.price / 0.81, 2)
            return "{} {}".format(self.price, self.currency)
        except (Exception, WebsiteContentModified) as e:
            log.debug("Product price GBP is missing for product with id: {}".format(self.id))
            return 0.0

    @property
    def availability(self):
        try:
            siblings = list(self.soup.body.find("meta", attrs={"itemprop": "availability"}).next_siblings)
            return list(filter(lambda x: isinstance(x, Tag), siblings))[0].text.strip()
        except (Exception, WebsiteContentModified) as e:
            log.debug("Product availability is missing for product with id: {}".format(self.id))
            return 0.0

    @property
    def images(self):
        try:
            photo_frame = list(self.soup.body.find("div", id="PhotoFrame").next_siblings)
            siblings = list(filter(lambda x: isinstance(x, Tag), photo_frame))
            return list(map(lambda x: "https://{}".format(x.attrs["href"][2:]), siblings))
        except (Exception, WebsiteContentModified) as e:
            log.debug("Product images is missing for product with id: {}".format(self.id))
            return []

    def store_description(self):
        path = os.path.join(self.product_path.format(self.name), "description.txt")
        with open(path, 'w+') as f:
            f.write(self.description)

    def store_images(self):
        for idx, url_image in enumerate(self.images):
            response = requests.get(url_image, stream=True)
            if response.status_code == 200:
                path = os.path.join(self.product_path.format(self.name), "image_{}".format(idx+1))
                with open(path, "wb") as f:
                    shutil.copyfileobj(response.raw, f)
                del response

    def get(self):
        self.store_description()
        self.store_images()
        return {
            "name": self.name,
            "price": "{} {}".format(self.price, self.currency),
            "price_gbp": self.price_gbp,
            "availability": self.availability
        }


class FastTechScraper(object):

    url = "https://www.fasttech.com/products/{}"

    def __init__(self, args, conf):
        self.args = args
        self.conf = conf
        self.chrome = webdriver.Chrome(self.conf["CHROME_DRIVER_PATH"])
        self.products = {}

    def scrap(self):
        try:
            with open("products.txt", "r") as f:
                for product_id in f.readlines():
                    if product_id.strip():
                        page_loaded = False
                        try:
                            self.chrome.get(FastTechScraper.url.format(product_id))
                            page_loaded = WebDriverWait(self.chrome, 10).until(
                                EC.presence_of_element_located((By.ID, 'content_Price')))
                        except TimeoutException as err:
                            log.error("Timeout error!")
                            exit(1)

                        if page_loaded:
                            html = self.chrome.page_source
                            soup = BeautifulSoup(html, "html.parser")
                            self.products[product_id] = Product(
                                id=product_id, soup=soup, destination=self.args.destination).get()

                        wait = int(self.conf["AWAIT"])
                        time.sleep(wait)
        finally:
            self.chrome.close()

        df = pd.DataFrame(list(self.products.values()))
        xlsx_path = os.path.join(self.args.destination, "products.xlsx")
        df.to_excel(xlsx_path, index=False)


def get_args():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-d', '--destination', type=str,
                            help='Enter the destination path where the product details has to be saved.')
    arg_parser.add_argument('-log-level', '--log_level', type=str, choices=("INFO", "DEBUG"),
                            default="INFO", help='Where do you want to post the info?')
    return arg_parser.parse_args()


def get_conf():
    conf = configparser.ConfigParser()
    conf.read("conf.ini")
    return conf["CONFIG"]


def main():
    args = get_args()
    config_logger(args)
    conf = get_conf()

    os.makedirs(args.destination, exist_ok=True)

    start = dt.now().strftime("%d-%m-%Y %H:%M:%S %p")
    log.info("Script starts at: {}".format(start))
    log.info("Destination: '{}' is given to save the crawled data.".format(args.destination))

    FastTechScraper(args=args, conf=conf).scrap()

    end = dt.now().strftime("%d-%m-%Y %H:%M:%S %p")
    log.info("Script ends at: {}".format(end))


if __name__ == '__main__':
    main()
