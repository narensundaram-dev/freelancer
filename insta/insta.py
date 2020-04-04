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
        r"(\+91-)?(\+91)?([7-9]{1})([0-9]{9})",  # India
        r"^\(?([0-9]{3})\)?[-.●]?([0-9]{3})[-.●]?([0-9]{4})$",  # North america (https://www.oreilly.com/library/view/regular-expressions-cookbook/9781449327453/ch04s02.html)
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
        self.posts = set()
        self.users = {}

    def login(self):
        self.chrome.get("https://www.instagram.com/accounts/login/")
        time.sleep(3)
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
        # 1st page: 36 posts. further pages: 12 posts
        return math.ceil(1 + ((limit - 36) / 12))

    def load_posts(self):
        source = self.chrome.execute_script("return document.documentElement.outerHTML")
        # soup = BeautifulSoup(self.chrome.page_source, 'html.parser')
        soup = BeautifulSoup(source, 'html.parser')
        posts = self.get_posts(soup)
        self.posts = self.posts.union(posts)

    def scroll_to_bottom(self):
        limit, wait = self.get_scroll_limit(), int(self.conf["WAIT"])
        log.info("{} no. of pages has to be scrapped from Instagram".format(limit))
        log.info("{} no. of seconds will be awaited for posts to be loaded on each scroll".format(wait))

        last_height = self.chrome.execute_script("return document.body.scrollHeight")
        self.load_posts()
        count = 0
        while True:
            self.chrome.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(wait)
            self.load_posts()

            # If the page reaches the bottom and no more posts to load
            new_height = self.chrome.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                log.info("Instagram reaches the bottom. Quits scrolling.")
                break
            last_height = new_height

            # If the page reaches the limit to fetch the number of posts
            count += 1
            if count >= limit:
                log.info("Limit exceeds. Quits scrolling. Count: {}; Limit: {}".format(count, limit))
                break

            log.info("Instagram page scrolled to page {}".format(count+1))

    def get_posts(self, soup):
        posts = soup.article.contents[2].find_all("a", href=re.compile(r"^/p/.*"), limit=int(self.conf["LIMIT"]))
        return set(["{}{}".format(URL, post.attrs["href"]) for post in posts])

    @classmethod
    def get_user_name(cls, post):
        html = requests.get(post).text
        soup = BeautifulSoup(html, "html.parser")
        data_json = str(soup.find_all("script", text=re.compile(r"^window._sharedData.*"))[0].string).replace(
            "window._sharedData = ", "").replace(";", "")
        data = json.loads(data_json)
        return data["entry_data"]["PostPage"][0]["graphql"]["shortcode_media"]["owner"]["username"]

    @classmethod
    def get_user_email(cls, bio):
        data = []
        try:
            for pattern in cls.pattern_email:
                matches = re.findall(pattern, bio)
                data.extend(matches)
            return ", ".join(data)
        except Exception as e:
            print("\nPattern match failed")
            print("bio: ", bio)
            print("data: ", data, "\n")
        return ""

    @classmethod
    def get_user_phone(cls, bio):
        data = set()
        try:
            for pattern in cls.pattern_mobile:
                # matches = re.findall(pattern, bio)
                matches = re.finditer(pattern, bio, re.MULTILINE)
                for match in matches:
                    data.add(match.group())
            return ", ".join(list(data))
        except Exception as e:
            print("\nPattern match failed")
            print("bio: ", bio)
            print("data: ", data, "\n")
        return ""

    @classmethod
    def get_user_gender(cls, bio):
        if " female " in bio.lower():
            return "Female"
        elif " male " in bio.lower():
            return "Male"

    def get_user_info(self, username):
        url = "{}/{}/?__a=1".format(URL, username)
        log.info("Fetching user info from url: {}".format(url))

        # Ignoring requests usage since it redirects the login page sometimes
        cookies = self.chrome.get_cookies()
        session = requests.Session()
        for cookie in cookies:
            session.cookies.set(cookie["name"], cookie["value"])
        response = session.get(url).json()

        cookies_resp = [{'name': name, 'value': value} for name, value in response.cookies.get_dict().items()]
        for cookie in cookies_resp:
            self.chrome.add_cookie(cookie)

        # self.chrome.get(url)
        # time.sleep(0.5)
        # soup = BeautifulSoup(self.chrome.page_source, "html.parser")
        # response = json.loads(soup.body.pre.get_text())

        user = response["graphql"]["user"]
        bio = user["biography"]
        cls = Instagram
        return {
            "name": u"{}".format(user["full_name"]),
            "username": user["username"],
            "count_followers": user["edge_followed_by"]["count"],

            # To fetch it from user["biography"] using regex
            "gender": cls.get_user_gender(bio),
            "email": cls.get_user_email(bio),
            "phone": cls.get_user_phone(bio),
            "city": "",
            "biography": bio,
        }

    def get_users(self):
        try:
            url = '{}/explore/tags/{}'.format(URL, self.tag)
            self.chrome.get(url)
            log.info("Started scrapping data from {}".format(url))
            log.info("Instagram page no 1 is initially loaded.")
            self.scroll_to_bottom()
            log.info("{} no of posts has been fetched from Instagram. Scroll limit: {} pages".format(
                len(self.posts), self.get_scroll_limit()))

            log.info("Started fetching the user information from scrapped posts.")
            # added for testing purpose. will remove it on moving to prod.
            self.users["narensundaram.dev"] = self.get_user_info("narensundaram.dev")
            for post in self.posts:
                username = self.get_user_name(post)
                if username not in self.users:
                    try:
                        self.users[username] = self.get_user_info(username)
                    except:
                        log.debug("Failed to fetch data for username {}".format(username))
                        pass
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
