import re
import time
import json
import logging
import requests
import argparse
import configparser
from datetime import datetime as dt

import pandas as pd


URL = "https://www.instagram.com"
SCOPE = ('basic', 'public_content')
log = logging.getLogger(__file__.split('/')[-1])


class Instagram:

    pattern_email = (
        r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)",
    )

    pattern_mobile = (
        # India
        r"(\+91-)?(\+91)?([7-9]{1})([0-9]{9})",

        # North america (https://www.oreilly.com/library/view/regular-expressions-cookbook/9781449327453/ch04s02.html)
        r"^\(?([0-9]{3})\)?[-.●]?([0-9]{3})[-.●]?([0-9]{4})$",

        # General
        r"(([+][(]?[0-9]{1,3}[)]?)|([(]?[0-9]{4}[)]?))\s*[)]?[-\s\.]?[(]?[0-9]{1,3}[)]?([-\s\.]?[0-9]{3})([-\s\.]?[0-9]{3,4})",
    )

    def __init__(self, tag, conf):
        self.tag = tag
        self.conf = conf

        self.posts = set()
        self.users = {}

    @classmethod
    def get_user_email(cls, bio):
        data = []
        try:
            for pattern in cls.pattern_email:
                matches = re.findall(pattern, bio)
                data.extend(matches)
            return ", ".join(data)
        except Exception as e:
            log.info("\nPattern match failed")
            log.info("bio: {}".format(bio))
            log.info("data: {}\n".format(data))
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
            log.info("\nPattern match failed")
            log.info("bio: {}".format(bio))
            log.info("data: {}\n".format(data))
        return ""

    @staticmethod
    def get_user_gender(bio):
        if " female " in bio.lower():
            return "Female"
        elif " male " in bio.lower():
            return "Male"

    @staticmethod
    def get_post(code):
        url = "{}/p/{}/?__a=1".format(URL, code)
        response = requests.get(url)
        if response.status_code == 200:
            try:
                return response.json()
            except Exception as err:
                log.error("Error getting the post information from {}".format(url))
                # log.exception("\nException: \n{}\n".format(response.text))
        return False

    @staticmethod
    def get_user(username):
        url = "{}/{}/?__a=1".format(URL, username)
        log.debug("Fetching user info from url: {}".format(url))
        response = requests.get(url)
        if response.status_code == 200:
            try:
                return response.json()
            except Exception as err:
                log.error("Error getting the information for {}".format(username))
                # log.exception("\nException: \n{}\n".format(response.text))
        return False

    def get_users(self):
        users = {}
        count = 0

        for post in self.posts:
            post_info = Instagram.get_post(post)
            if post_info:
                username = post_info["graphql"]["shortcode_media"]["owner"]["username"]
                if username not in users:
                    user = Instagram.get_user(username)
                    if user:
                        count += 1

                        info = user["graphql"]["user"]
                        bio = info["biography"]
                        users[username] = {
                            "name": u"{}".format(info["full_name"]),
                            "username": info["username"],
                            "count_followers": info["edge_followed_by"]["count"],

                            # To fetch it from user["biography"] using regex
                            "gender": Instagram.get_user_gender(bio),
                            "email": Instagram.get_user_email(bio),
                            "phone": Instagram.get_user_phone(bio),
                            "city": "",
                            "biography": bio,
                        }
                    if count and count % 10 == 0:
                        log.info("{} no of users added so far ...".format(count))
        # time.sleep(0.5)
        self.users = users
        return self.users

    def get_posts(self):
        posts = set()
        end_cursor = ''
        count = 1
        while True:
            url = "{}/explore/tags/{}/?__a=1&max_id={}".format(URL, self.tag, end_cursor)
            r = requests.get(url)
            data = json.loads(r.text)

            end_cursor = data['graphql']['hashtag']['edge_hashtag_to_media']['page_info'][
                'end_cursor']  # value for the next page
            edges = data['graphql']['hashtag']['edge_hashtag_to_media']['edges']

            for item in edges:
                posts.add(item['node']["shortcode"])

            log.info("Instagram page scrolled to page {}. Loaded {} no of posts".format(count, len(posts)))
            count += 1
            if len(posts) >= int(self.conf["LIMIT"]):
                break

            # time.sleep(2)
        self.posts = posts
        return self.posts

    def get(self):
        log.info("Started getting the recent posts from Instagram.")
        posts = self.get_posts()
        log.info("*** {} no of posts has been fetched from Instagram ***".format(len(posts)))

        log.info("Started getting the users from extracted posts in Instagram.")
        users = self.get_users()
        log.info("*** {} no of users has been fetched from Instagram ***".format(len(users)))

        df = pd.DataFrame(list(users.values()))
        df.to_excel("users.xls", index=False)


def get_conf():
    conf = configparser.ConfigParser()
    conf.read("conf.ini")
    return conf["CONFIG"]


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

    start = dt.now().strftime("%d-%m-%Y %H:%M:%S %p")
    log.info("Script starts at: {}".format(start))
    log.info("Tag name: '{}' is given to fetch from Instagram".format(args.tag))

    Instagram(tag=args.tag.lower(), conf=conf).get()

    end = dt.now().strftime("%d-%m-%Y %H:%M:%S %p")
    log.info("Script ends at: {}".format(end))


if __name__ == '__main__':
    main()
