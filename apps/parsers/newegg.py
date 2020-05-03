# -*- coding: utf-8 -*-
import os
import random
import re
from time import sleep

import requests
import traceback
from lxml import html

from apps.parsers.common import HEADERS_LIST, increment_queue
from apps.core.models import Item


ORIGIN = 'https://www.newegg.com'


def get_rating(dom):
    rating = dom.xpath('.//span[@itemprop="ratingValue"]/@content')
    if rating:
        rating = rating[0]
    else:
        rating = 0
    return rating


def get_size(dom):
    size = dom.xpath('.//div[@class="grpSelector" and not(contains(.,"Color"))]//li/@title')
    size = ', '.join(size)
    if not size:
        size = 'Standard size'
    return size


def get_picture(dom):
    picture = dom.xpath('.//div[@class="objimages"]//img[not(contains(@class,"logo"))]/@src')
    if picture:
        picture = picture[0][2:]
    else:
        picture = None
    return picture


def get_title(dom):
    title = dom.xpath('.//h1[@id="grpdescrip_h"]/span')
    if not title:
        return ''
    return title[0].text.strip()


def get_colors(dom):
    colors = dom.xpath('.//div[@id="landingpage-property" and contains(.,"Color")]//button/@aria-label')
    colors = ', '.join(colors)
    if not colors:
        colors = 'Default color'
    return colors


def product_processing(prod_link, model, brand, parent_id, price):
    prod_link = prod_link + '&intl=nosplash'
    page = get_page_html(prod_link)
    dom = html.fromstring(page)
    res = {}

    if 'Choose a country.' in page:
        return None

    res['sku'] = model
    res['title'] = get_title(dom)
    res['colors'] = get_colors(dom)
    res['rating'] = get_rating(dom)
    res['size'] = get_size(dom)
    res['picture'] = get_picture(dom)
    res['platform'] = Item.PLATFORM_VALUE_NEWEGG
    res['url'] = prod_link
    res['price'] = price
    res['condition'] = 'New'
    res['brand'] = brand
    return res


def parse(brand, model_num, amazon_price, parent_id):
    res = None
    try:
        old_num = model_num
        model_num = model_num.lower()
        boundary = amazon_price * 0.5

        link = prepare_query_url(model_num)

        page = get_page_html(link)
        dom = html.fromstring(page)

        if "no-results-message" in page:
            raise ValueError("No results in page")

        price_url_dict = extract_items(boundary, dom, model_num)
        price_keys = sorted(price_url_dict)

        for price in price_keys:
            try:
                item_url = price_url_dict[price]
                res = product_processing(item_url, old_num, brand, parent_id, price)

                if res:
                    break
            except Exception as e:
                traceback.print_exc()

    except Exception:
        traceback.print_exc()

    Item.create(res, parent_id)
    increment_queue(parent_id, -1)
    return res


def get_page_html(link):
    page = requests.get(link, headers={'User-Agent': random.choice(HEADERS_LIST)}).text
    page = page.lower()
    return page


def prepare_query_url(model_num):
    base_url = 'https://www.newegg.com/p/pl?d={}&Order=PRICED&PageSize=96'
    query = model_num
    query = query.split(' ')
    query = '+'.join(query)
    url = base_url.format(query)
    return url


def filter_by_model_number(items, model_num):
    return [i for i in items if re.search(model_num, i.text_content(), re.IGNORECASE)]


def filter_by_boundary(boundary, items):
    return {price: items[price] for price in items.keys() if price > boundary}


def extract_price_url_dict(items):
    result_items = {}
    for item in items:
        try:
            price_el = item.xpath('./div[@class="item-action"]//li[@class="price-current"]')
            if not price_el:
                continue
            price = float(re.sub('[^0-9.]', '', price_el[0].find("strong").text + price_el[0].find("sup").text))
            item_link = item.xpath('./a[@class="item-title"]/@href')
            if not item_link:
                continue
            result_items[price] = item_link[0]
        except:
            continue
    return result_items


def extract_items(boundary, dom, model_num):
    items_selector = './/div[@class="item-info"]'
    items = dom.xpath(items_selector)
    items = filter_by_model_number(items, model_num)
    items = extract_price_url_dict(items)
    return filter_by_boundary(boundary, items)


# if __name__ == '__main__':
    #     file = os.path.join(os.path.dirname(__file__), 'tests/data/newegg_search_page.html')
    #     result = extract_items(100, html.fromstring(open(file, "r").read()), 'lc27f398fwnxza')
    #     print(result)
    # res = parse('samsung', 'lc27f398fwnxza', 300, 1)
#     print(res)
