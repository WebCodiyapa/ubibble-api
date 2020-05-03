import random

from django.db import transaction
from django.db.models import F
from selenium import webdriver
from selenium.webdriver import ChromeOptions
from apps.core.models import Item, Category

HEADERS_LIST = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/605.1.15 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/605.1 Edge/19.17763',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.80 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:65.0) Gecko/20100101 Firefox/65.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:64.0) Gecko/20100101 Firefox/64.0',
    'Mozilla/5.0 (Windows NT 10.0; rv:63.0) Gecko/20100101 Firefox/63.0',
    'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:63.0) Gecko/20100101 Firefox/63.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36 OPR/56.0.3051.52',
    'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3198.0 Safari/537.36 OPR/49.0.2711.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36 OPR/52.0.2871.99',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.170 Safari/537.36 OPR/53.0.2907.99',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.84 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36 Edge/17.17134',
]


def increment_queue(parent_id, inc):
    with transaction.atomic():
        item = Item.objects.select_for_update().get(id=parent_id)
        count = item.is_processing
        item.is_processing = count + inc
        item.save()


def create_category(category_string):
    categories = category_string.split(">")
    is_parent = True
    parent_cat = None
    for c in categories:
        if is_parent:
            parent_cat, _ = Category.objects.get_or_create(name=c.strip())
            is_parent = False
        else:
            parent_cat, _ = Category.objects.get_or_create(name=c.strip(), parent=parent_cat)

    return parent_cat

class WebDriver():
    def __init__(self):
        self.options = ChromeOptions()
        self.options.add_argument('--window-size=1366,768')
        self.options.add_argument('--user-agent={0}'.format(random.choice(HEADERS_LIST)))
        self.options.add_argument('--headless')
        # experimental options
        self.blink_settings_list = []
        self.disabled_features_list = []
        self.chrome_prefs = {}

        self.chrome_prefs['profile.default_content_setting_values.notifications'] = 2
        self.chrome_prefs['profile.default_content_setting_values.images'] = 2
        self.blink_settings_list.append('imagesEnabled=false')
        self.blink_settings_list.append('loadsImagesAutomatically=false')
        self.blink_settings_list.append('mediaPlaybackRequiresUserGesture=true')
        self.disabled_features_list.append('PreloadMediaEngagementData')
        self.disabled_features_list.append('AutoplayIgnoreWebAudio')
        self.disabled_features_list.append('MediaEngagementBypassAutoplayPolicies')
        if self.disabled_features_list:
            self.options.add_argument(f"--disable-features={','.join(self.disabled_features_list)}")
        if self.blink_settings_list:
            self.options.add_argument(f"--blink-settings={','.join(self.blink_settings_list)}")
        if self.chrome_prefs:
            self.options.add_experimental_option('prefs', self.chrome_prefs)
        self.options.add_argument('--disable-device-discovery-notifications')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--no-sandbox')
        #
        self.options.add_argument('--allow-insecure-localhost')
        # experiment end.
        self.mydriver = webdriver.Chrome(options=self.options)

    # Get html-object of current page in browser.
    def page(self):
        page_text = self.mydriver.page_source
        return html.fromstring(page_text)

    # Find element by XPath.
    def xpath(self, path):
        return self.mydriver.find_element_by_xpath(path)

    # Find a list of elements by Xpath.
    def xpathes(self, path):
        return self.mydriver.find_elements_by_xpath(path)

    # Go to the page.
    def get(self, url):
        self.mydriver.get(url)

    # Get source code of a page as str value.
    def get_source(self):
        return self.mydriver.page_source

    # Close the browser.
    def quit(self):
        self.mydriver.quit()

