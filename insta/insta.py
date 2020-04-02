import re
import time
import json
import requests

from selenium import webdriver
from bs4 import BeautifulSoup as bs

URL = "https://www.instagram.com"
# TODO: TAG should be from CLA
TAG = "streetbrand"


class InstagramScrapy:

    def __init__(self):
        # TODO: chromedriver should be from CLA
        self.chrome = webdriver.Chrome('/home/naren/Downloads/chromedriver')
        self.posts = []
        self.users = {}

    # TODO: limit, wait should be configurable
    def scroll_to_bottom(self, limit=1, wait=5):
        last_height = self.chrome.execute_script("return document.body.scrollHeight")
        count = 0
        while True:
            if count >= limit:
                break

            self.chrome.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(wait)

            new_height = self.chrome.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break

            last_height = new_height
            count += 1

    def get_posts(self, soup):
        posts = soup.article.contents[2].find_all("a", href=re.compile("^/p/.*"))
        return ["{}{}".format(URL, post.attrs["href"]) for post in posts]

    def get_user_name(self, post):
        html = requests.get(post).text
        soup = bs(html, "html.parser")
        data_json = str(soup.find_all("script", text=re.compile("^window._sharedData.*"))[0].string).replace(
            "window._sharedData = ", "").replace(";", "")
        data = json.loads(data_json)
        return data["entry_data"]["PostPage"][0]["graphql"]["shortcode_media"]["owner"]["username"]

    def get_user_info(self, username):
        url = "{}/{}/?__a=1".format(URL, username)
        response = requests.get(url).json()
        user = response["graphql"]["user"]
        return {
            "name": u"{}".format(user["full_name"]),
            "username": user["username"],
            "count_followers": user["edge_followed_by"]["count"],

            "gender": "",
            "city": "",
            "email": "",
            "phone": ""
        }

    def get_users(self):
        try:
            self.chrome.get('{}/explore/tags/'.format(URL) + TAG)
            self.scroll_to_bottom()

            soup = bs(self.chrome.page_source, 'html.parser')
            self.posts = self.get_posts(soup)

            for post in self.posts:
                username = self.get_user_name(post)
                self.users[username] = self.get_user_info(username)

            # TODO: Write it as excel file
            with open("users.json", "w+") as fobj:
                json.dump(self.users, fobj, indent=4)
        finally:
            self.chrome.close()


def main():
    InstagramScrapy().get_users()


if __name__ == '__main__':
    main()
