# -*- coding: utf-8 -*-
import random
import re

import requests
import traceback
from lxml import html
from lxml import etree


from .common import *
from apps.core.models import Item

# Константы
MAIN_LINK = 'https://www.bestbuy.com/site/searchpage.jsp?st={}'
REFERER = 'https://www.bestbuy.com/site/lenovo-smart-tab-p10-10-1-tablet-64gb-aurora-black/6321934.p?skuId=6321934'
ORIGIN = 'https://www.bestbuy.com'


def product_processing(prod_link, model, header, brand, parent_id):
    prod_link = prod_link + '&intl=nosplash'
    page = requests.get(prod_link, headers={'User-Agent': header, 'origin': ORIGIN}).text
    dom = html.fromstring(page)
    res = {}

    if 'Choose a country.' in page:
        return None

    res['sku'] = dom.xpath('//div[@class="model product-data"]//span[@class="product-data-value body-copy"]/text()[1]')[0]
    res['title'] = dom.xpath('.//h1[@class="heading-5 v-fw-regular"]/text()')[0]
    colors = dom.xpath('.//div[@class="variation-group image-group"]//a[@data-name]/@data-name')
    if bool(colors) is True:
        res['colors'] = ', '.join(colors)
    else:
        color = dom.xpath('.//li[contains(.,"Color") and not(contains(.,"Category"))]//div[@class="row-value col-xs-6 body-copy-lg v-fw-regular"]/text()')
        res['colors'] = ', '.join(color)

    rating = dom.xpath('.//div[@class="ugc-stat"]//span[@class="c-review-average"]/text()')
    if rating:
        res['rating'] = rating[0]
    else:
        res['rating'] = 0

    res['platform'] = Item.PLATFORM_VALUE_BESTBUY
    size = dom.xpath('.//div[@class="shop-variation-wrapper"][1]//*[@class="body-copy-lg v-fw-medium variation-name"]/text()')
    if size:
        res['size'] = ', '.join(size)
    else:
        res['size'] = 'Standard size'

    picture = dom.xpath('.//img[@class="primary-image "]/@src')
    if picture:
        picture = picture[0]
        res['picture'] = picture[:picture.index(';')]
    else:
        res['picture'] = None

    try:
        res['price'] = dom.xpath('.//div[@class="priceView-hero-price priceView-customer-price"]/span[1]/text()[2]')[0]
    except:
        return None # as no price found.

    res['url'] = prod_link
    res['condition'] = 'New'
    res['brand'] = brand

    return res

def parse(brand, model_num, amazon_price, parent_id):
    res = None
    try:
        old_num = model_num
        model_num = model_num.lower()
        boundary = amazon_price*0.5

        query = model_num
        query = query.split(' ')
        query = '+'.join(query)
        link = MAIN_LINK.format(query)

        header = random.choice(HEADERS_LIST)
        page = get_page(header, link)
        page = page.lower()
        dom = html.fromstring(page)

        if "no-results-message" in page:
            raise ValueError("No results in page")

        items = {}
        for item in dom.xpath('.//ol[@class="sku-item-list"]/li[@class="sku-item"]'):
            price_el = item.xpath('//div[contains(@class,"priceview-hero-price")]/span[2]')
            price = float(re.sub('[^0-9.]', '', str(etree.tostring(price_el[0])).split("$")[1]))
            item_link = item.xpath('//h4[@class="sku-header"]/a/@href')
            items[price] = item_link[0]
        items = {price: items[price] for price in items.keys() if price > boundary}
        item_keys = sorted(items)
        print(item_keys, item_keys)
        for key in item_keys:
            try:
                product_link = 'https://www.bestbuy.com' + items[key]
                res = product_processing(product_link, old_num, header, brand, parent_id)
                if res:
                    break
            except Exception as e:
                traceback.print_exc()

    except Exception as e:
        traceback.print_exc()
    increment_queue(parent_id, -1)
    Item.create(res, parent_id)
    return res


def get_page(header, link):
    page = requests.get(link, headers={'User-Agent': header, 'origin': ORIGIN}).text
    return page
