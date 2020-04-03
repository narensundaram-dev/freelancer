import re
import time
import math
import json
import logging
import requests
import argparse
import configparser
from datetime import datetime as dt

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver


URL = "https://www.instagram.com"
SCOPE = ('basic', 'public_content')
log = logging.getLogger(__file__.split('/')[-1])


class Instagram:

    pattern_mobile = (
        r"(([+][(]?[0-9]{1,3}[)]?)|([(]?[0-9]{4}[)]?))\s*[)]?[-\s\.]?[(]?[0-9]{1,3}[)]?([-\s\.]?[0-9]{3})([-\s\.]?[0-9]{3,4})",
    )
    pattern_email = (
        r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)",
    )

    def __init__(self, tag, conf, cred):
        self.tag = tag
        self.conf = conf
        self.cred = cred
        self.chrome = webdriver.Chrome(self.conf["CHROME_DRIVER_PATH"])
        log.info("Chrome is started using chromedriver: {}".format(self.conf["CHROME_DRIVER_PATH"]))

        self.login()
        self.posts = []
        self.users = {}

    def login(self):
        self.chrome.get("https://www.instagram.com/accounts/login/")
        time.sleep(5)
        try:
            dom_username = self.chrome.find_element_by_xpath('//*[@name="username"]')
            dom_password = self.chrome.find_element_by_xpath('//*[@name="password"]')
            dom_login_btn = self.chrome.find_element_by_xpath('//*[@type="submit"]')

            dom_username.send_keys(self.cred["USERNAME"])
            dom_password.send_keys(self.cred["PASSWORD"])
            dom_login_btn.click()
            time.sleep(5)
        except BaseException as err:
            log.error("Error: ", err)

    def get_scroll_limit(self):
        limit = int(self.conf["LIMIT"])
        # 1st page: 36 posts. further pages: 9 posts
        return math.ceil(1 + ((limit - 36) / 9))

    def scroll_to_bottom(self):
        limit, wait = self.get_scroll_limit(), int(self.conf["WAIT"])
        log.info("{} no. of pages has to be scrapped from Instagram".format(limit))
        log.info("{} no. of seconds will be awaited for posts to be loaded on each scroll".format(wait))

        last_height = self.chrome.execute_script("return document.body.scrollHeight")
        count = 0
        while True:
            self.chrome.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(wait)

            # If the page reaches the bottom and no more posts to load
            new_height = self.chrome.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

            # If the page reaches the limit to fetch the number of posts
            count += 1
            if count >= limit:
                break

            log.info("Instagram page scrolled to page {}".format(count+1))

    def get_posts(self, soup):
        posts = soup.article.contents[2].find_all("a", href=re.compile("^/p/.*"), limit=int(self.conf["LIMIT"]))
        log.info("{} no of posts has been fetched from Instagram. Scroll limit: {}".format(
            len(posts), self.get_scroll_limit()))
        return ["{}{}".format(URL, post.attrs["href"]) for post in posts]

    @classmethod
    def get_user_name(cls, post):
        html = requests.get(post).text
        soup = BeautifulSoup(html, "html.parser")
        data_json = str(soup.find_all("script", text=re.compile("^window._sharedData.*"))[0].string).replace(
            "window._sharedData = ", "").replace(";", "")
        data = json.loads(data_json)
        return data["entry_data"]["PostPage"][0]["graphql"]["shortcode_media"]["owner"]["username"]

    @classmethod
    def get_user_email(cls, bio):
        data = []
        for pattern in cls.pattern_email:
            matches = re.findall(pattern, bio)
            data.extend(matches)
        return ", ".join(data)

    @classmethod
    def get_user_phone(cls, bio):
        data = []
        for pattern in cls.pattern_mobile:
            matches = re.findall(pattern, bio)
            data.extend(matches)
        return ", ".join(data)

    @classmethod
    def get_user_gender(cls, bio):
        if "female" in bio.lower():
            return "Female"
        elif "male" in bio.lower() and "female" not in bio.lower():
            return "Male"

    @classmethod
    def get_user_info(cls, username):
        url = "{}/{}/?__a=1".format(URL, username)
        log.debug("Fetching user info from url: {}".format(url))
        response = requests.get(url).json()
        user = response["graphql"]["user"]
        bio = user["biography"]
        return {
            "name": u"{}".format(user["full_name"]),
            "username": user["username"],
            "count_followers": user["edge_followed_by"]["count"],

            # To fetch it from user["biography"] using regex
            "city": "",
            "gender": cls.get_user_gender(bio),
            "email": cls.get_user_email(bio),
            "phone": cls.get_user_phone(bio)
        }

    def get_users(self):
        try:
            url = '{}/explore/tags/{}'.format(URL, self.tag)
            self.chrome.get(url)
            log.info("Started scrapping data from {}".format(url))
            log.info("Instagram page no 1 is initially loaded.")
            self.scroll_to_bottom()

            soup = BeautifulSoup(self.chrome.page_source, 'html.parser')

            # BUG: self.chrome.page_source is not loading all the posts. Max 45 posts are loaded.
            with open("source.html", "w+") as fobj:
                fobj.write(self.chrome.page_source)

            self.posts = self.get_posts(soup)

            log.info("Started fetching the user information from scrapped posts.")
            self.users["narensundaram.dev"] = self.get_user_info("narensundaram.dev")

            for post in self.posts:
                username = self.get_user_name(post)
                if username not in self.users:
                    self.users[username] = self.get_user_info(username)
            log.info("{} no of users fetched from extracted posts on Instagram".format(len(self.users)))

            df = pd.DataFrame(list(self.users.values()))
            df.to_excel("users.xls", index=False)
        finally:
            self.chrome.close()


def get_conf():
    conf = configparser.ConfigParser()
    conf.read("conf.ini")
    return conf["CONFIG"]


def get_insta_cred():
    conf = configparser.ConfigParser()
    conf.read("conf.ini")
    return conf["INSTAGRAM"]


def get_args():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-t', '--tag', type=str, default="streetbrand",
                            help='Enter the tag-name (Eg: streetbrand) to scrap from Instagram.')
    arg_parser.add_argument('-log-level', '--log_level', type=str, choices=("INFO", "DEBUG"),
                            default="INFO", help='Where do you want to post the info?')
    return arg_parser.parse_args()


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


def main():
    args = get_args()
    config_logger(args)
    conf = get_conf()
    cred = get_insta_cred()

    start = dt.now().strftime("%d-%m-%Y %H:%M:%S %p")
    log.info("Script starts at: {}".format(start))
    log.info("Tag name: '{}' is given to fetch from Instagram".format(args.tag))

    Instagram(tag=args.tag.lower(), conf=conf, cred=cred).get_users()

    end = dt.now().strftime("%d-%m-%Y %H:%M:%S %p")
    log.info("Script ends at: {}".format(end))


if __name__ == '__main__':
    main()
