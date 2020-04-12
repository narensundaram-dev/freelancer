import logging
import argparse
import traceback
import configparser
from datetime import datetime as dt

import pandas as pd
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
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


class PCManager(object):
    url = "https://pedalcommander.com/"

    def __init__(self, args, conf):
        self.args = args
        self.conf = conf
        self.chrome = webdriver.Chrome(conf["CHROME_DRIVER_PATH"])
        self.url = PCManager.url
        self.data = []
        # self.urls = {}

    @classmethod
    def setup(cls):
        pass

    @classmethod
    def cleanup(cls):
        pass

    def get_years(self):
        WebDriverWait(self.chrome, 60).until(EC.presence_of_element_located((By.ID, 'dropdown-field_1')))
        html = self.chrome.page_source
        soup = BeautifulSoup(html, "html.parser")
        children = list(soup.find("select", attrs={"id": "dropdown-field_1"}).children)[1:]
        years = dict(zip(map(lambda x: x.attrs["value"], children), map(lambda x: x.get_text(), children)))
        return years

    def get_makes(self, year="yr_2020"):
        select = Select(self.chrome.find_element_by_id("dropdown-field_1"))
        select.select_by_value(year)

        WebDriverWait(self.chrome, 60).until(EC.presence_of_element_located((By.ID, 'dropdown-field_2')))
        soup = BeautifulSoup(self.chrome.page_source, "html.parser")
        children = list(soup.find("select", attrs={"id": "dropdown-field_2"}).children)[1:]
        makes = dict(zip(map(lambda x: x.attrs["value"], children), map(lambda x: x.get_text(), children)))
        return makes

    def get_models(self, make="mk_acura"):
        select = Select(self.chrome.find_element_by_id("dropdown-field_2"))
        select.select_by_value(make)

        WebDriverWait(self.chrome, 60).until(EC.presence_of_element_located((By.ID, 'dropdown-field_3')))
        soup = BeautifulSoup(self.chrome.page_source, "html.parser")
        children = list(soup.find("select", attrs={"id": "dropdown-field_3"}).children)[1:]
        models = dict(zip(map(lambda x: x.attrs["value"], children), map(lambda x: x.get_text(), children)))
        return models

    def get_sub_models(self, model="md_ilx"):
        select = Select(self.chrome.find_element_by_id("dropdown-field_3"))
        select.select_by_value(model)

        WebDriverWait(self.chrome, 60).until(EC.presence_of_element_located((By.ID, 'dropdown-field_4')))
        soup = BeautifulSoup(self.chrome.page_source, "html.parser")
        children = list(soup.find("select", attrs={"id": "dropdown-field_4"}).children)[1:]
        sub_models = dict(zip(map(lambda x: x.attrs["value"], children), map(lambda x: x.get_text(), children)))
        return sub_models

    def get_engines(self, sub_model="rk_a-spec"):
        select = Select(self.chrome.find_element_by_id("dropdown-field_4"))
        select.select_by_value(sub_model)

        WebDriverWait(self.chrome, 60).until(EC.presence_of_element_located((By.ID, 'dropdown-field_5')))
        soup = BeautifulSoup(self.chrome.page_source, "html.parser")
        children = list(soup.find("select", attrs={"id": "dropdown-field_5"}).children)[1:]
        engines = dict(zip(map(lambda x: x.attrs["value"], children), map(lambda x: x.get_text(), children)))
        return engines

    def load(self):
        page_loaded = False
        try:
            self.chrome.get(self.url)
            try:
                self.chrome.get(self.url)
                page_loaded = WebDriverWait(self.chrome, 60).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'dropdowns')))
            except TimeoutException as err:
                log.error("Timeout error!")
                exit(1)

            return True if page_loaded else False
        except Exception as e:
            log.debug(e)
            log.error("Error loading the pedal-commander.")

    def get_url(self, key_year, key_make, key_model, key_sub_model, key_engine):
        url = "{}{}?rq={}~{}~{}~{}~{}".format(
            self.url, "/pages/product-result", key_year, key_make, key_model, key_sub_model, key_engine)
        return url

    def read(self):
        count = 0
        try:
            if self.load():
                for key_year, year in self.get_years().items():
                    for key_make, make in self.get_makes(key_year).items():
                        for key_model, model in self.get_models(key_make).items():
                            for key_sub_model, sub_model in self.get_sub_models(key_model).items():
                                for key_engine, engine in self.get_engines(key_sub_model).items():
                                    self.data.append({
                                        "year": year,
                                        "make": make,
                                        "model": model,
                                        "sub_model": sub_model,
                                        "engine": engine,
                                        "url": self.get_url(key_year, key_make, key_model, key_sub_model, key_engine)
                                    })
                                    count += 1
                                    log.info("Fetched combination for: {}, {}, {}, {}, {}. So far: {}".format(
                                        year, make, model, sub_model, engine, count))
            else:
                log.error("Error loading the pedal-commander. Please check your internet connection.")
                exit(1)
        except Exception as e:
            log.info(e)
        finally:
            self.chrome.close()
            return self

    def save(self):
        df = pd.DataFrame(self.data)
        df.to_excel("data.xlsx", index=False)


def get_args():
    arg_parser = argparse.ArgumentParser()
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

    start = dt.now().strftime("%d-%m-%Y %H:%M:%S %p")
    log.info("Script starts at: {}".format(start))
    PCManager.setup()

    manager = PCManager(args, conf)
    manager.read().save()

    PCManager.cleanup()
    end = dt.now().strftime("%d-%m-%Y %H:%M:%S %p")
    log.info("Script ends at: {}".format(end))


if __name__ == '__main__':
    main()


# class PCScraper(object):
#
#     def __init__(self, url):
#         self.chrome = webdriver.Chrome(r"C:\Users\ngnanasu\Documents\chromedriver\chromedriver.exe")
#         self.url = url
#         self.data = []
#         self.soup = None
#
#     def get_page_type(self):
#         try:
#             WebDriverWait(self.chrome, 20).until(EC.presence_of_element_located((By.ID, 'products')))
#             return "list"
#         except TimeoutException as e:
#             try:
#                 WebDriverWait(self.chrome, 20).until(EC.presence_of_element_located((By.ID, 'template-product')))
#                 return "detail"
#             except TimeoutException as e:
#                 return ""
#
#     def get_product_urls(self):
#         urls = []
#         type_ = self.get_page_type()
#         if type_ == "list":
#             WebDriverWait(self.chrome, 20).until(EC.presence_of_element_located((By.CLASS_NAME, 'product-thumb')))
#             soup = BeautifulSoup(self.chrome.page_source, "html.parser")
#             product_thumbs = soup.find_all("div", attrs={"class": "product-thumb"})
#             for thumb in product_thumbs:
#                 urls.append(thumb.next_element.attrs["href"])
#         elif type_ == "detail":
#             return urls.append(self.chrome.current_url)
#         return urls
#
#     @classmethod
#     def get_product_description(cls, soup):
#         header, content = "", ""
#         dom_desc = soup.find("div", attrs={"itemprop": "description"}).contents
#         dom_desc_filtered = list(filter(lambda x: not isinstance(x, NavigableString), dom_desc))
#         dom_desc_header = list(filter(lambda x: x.name == "h2", dom_desc_filtered))
#         if dom_desc_header:
#             header = "\n".join([dom.get_text() for dom in dom_desc_header])
#         dom_desc_content = list(filter(lambda x: x.name == "ol", dom_desc_filtered))
#         if dom_desc_content:
#             dom_desc_content_filtered = list(
#                 filter(lambda x: not isinstance(x, NavigableString), dom_desc_content[0].contents))
#             content = "\n".join([dom.get_text() for dom in dom_desc_content_filtered])
#         description = header + "\n\n" + content
#         return description
#
#     def get_product_info(self, product_url):
#         info = {}
#
#         self.chrome.get(product_url)
#         loaded = WebDriverWait(self.chrome, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'money')))
#         if loaded:
#             soup = BeautifulSoup(self.chrome.page_source, "html.parser")
#             info.update({
#                 "name": soup.find("h1", attrs={"class": "product__title"}).get_text(),
#                 "description": self.get_product_description(soup),
#                 "price": soup.find_all("span", attrs={"class": "money"})[0].get_text(),
#                 "price_discount": soup.find_all("span", attrs={"class": "money"})[1].get_text()
#             })
#
#         return info
#
#     def get(self):
#         self.chrome.get(self.url)
#         product_urls = self.get_product_urls()
#         for product_url in product_urls:
#             info = self.get_product_info(product_url)
#             self.data.append(info)
#         self.chrome.close()
#         return self.data
