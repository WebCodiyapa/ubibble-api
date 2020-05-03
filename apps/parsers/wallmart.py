# -*- coding: utf-8 -*-
import os
import random
import re
import traceback

import requests
from lxml import html

from .common import HEADERS_LIST, increment_queue
from apps.core.models import Item

MAIN_LINK = 'https://www.walmart.com/search/?cat_id=0&query={0}&spelling=false'

def get_models_list(dom):
    meta_model = dom.xpath('.//meta[@itemprop="model"]/@content')
    if meta_model:
        meta_model = meta_model[0]
    else:
        return None
    meta_model = model_processing(meta_model)
    model_model = (''.join(dom.xpath('.//tr[contains(.,"Model")]/td[2]//text()'))).strip()
    man_part_num = (''.join(dom.xpath('.//tr[contains(.,"Manufacturer")]/td[2]//text()'))).strip()
    man_part_num_low = (''.join(dom.xpath('.//tr[contains(.,"manufacturer_part_number")]/td[2]//text()'))).strip()

    model_model = model_processing(model_model)
    man_part_num = model_processing(man_part_num)
    man_part_num_low = model_processing(man_part_num_low)
    return [meta_model, model_model, man_part_num, man_part_num_low]


def model_processing(model):
    model_processed = re.sub('-', '', model)
    model_processed = re.sub(' ', '', model_processed)
    return model_processed.lower()


def product_processing(link, processed_model, header, brand, original_model, parent_id, price):
    page = requests.get(link, headers={'User-Agent': header}).text
    dom = html.fromstring(page)
    models_list = get_models_list(dom)

    if not models_list:
        return False
    if processed_model not in models_list:
        return False

    title = get_title(dom)
    colors = get_colors(dom)
    rating = get_rating(dom)
    size = get_size(dom)
    picture = get_picture(dom)
    condition = get_condition(title)

    res = {
        'title': title,
        'brand': brand,
        'colors': colors,
        'sku': original_model,
        'rating': rating,
        'platform': Item.PLATFORM_VALUE_WALLMART,
        'picture': picture,
        'price': price,
        'condition': condition,
        'size': size,
        'url': link
    }
    return res


def get_condition(title):
    if 'Used' in title:
        condition = 'Used'
    elif 'Refurbished ' in title:
        condition = 'Refurbished'
    else:
        condition = 'New'
    return condition


def get_picture(dom):
    picture = dom.xpath('.//img[@data-tl-id="ProductPage-primary-image"]/@src')
    if picture:
        picture = picture[0]
    else:
        picture = dom.xpath('.//img[@class="hover-zoom-hero-image"]/@src')
        if picture:
            picture = picture[0]
        else:
            picture = None
    if picture.startswith("//"):
        picture = "http:"+picture
    return picture


def get_size(dom):
    size = dom.xpath(
        './/div[@class="variants-container variant-content-tiles-outer-wrapper" and (contains(.,"Capacity") or contains(.,"Size"))]//div[@class="variant-option-text"]/text()')
    if size:
        size = ', '.join(size)
    else:
        size = 'Default size'
    return size


def get_rating(dom):
    rating = dom.xpath('.//span[@class="ReviewsHeader-ratingPrefix font-bold"]/text()')
    if rating:
        rating = rating[0]
    else:
        rating = 0
    return rating


def get_colors(dom):
    colors = dom.xpath('.//span[contains(@title,"Color")]/@data-variant-id')
    if colors:
        for i in range(len(colors)):
            colors[i] = colors[i].split("-")[1:][0]
        colors = ', '.join(colors)
    else:
        colors = 'Default color'
    return colors


def get_title(dom):
    title = dom.xpath('.//h1[contains(@class, "prod-ProductTitle")]')
    if title:
        return title[0].text_content()
    else:
        return ''


def parse(brand, model_num, amazon_price, parent_id):
    res = None
    try:
        header = random.choice(HEADERS_LIST)
        boundary = amazon_price * 0.5
        model_processed = model_processing(model_num)

        query = brand + " " + model_num
        query = query.split(' ')
        query = '+'.join(query)
        link = MAIN_LINK.format(query) + '&grid=false'

        page = requests.get(link, headers={'User-Agent': header}).text
        if 'Sorry, no products matched' in page:
            raise ValueError("no items found")

        dom = html.fromstring(page)
        price_url_dict = extract_items(boundary, dom, model_processed)
        price_keys = sorted(price_url_dict)
        for price in price_keys:
            try:
                item_url = 'https://www.walmart.com' + price_url_dict[price]
                res = product_processing(item_url, model_processed, header, brand, model_num, parent_id, price)
                if res:
                    break
            except Exception as e:
                traceback.print_exc()

    except Exception as e:
        traceback.print_exc()

    Item.create(res, parent_id)
    increment_queue(parent_id, -1)
    return res


def filter_by_boundary(boundary, items):
    return {price: items[price] for price in items.keys() if price > boundary}


def extract_price_url_dict(items):
    result_items = {}
    for item in items:
        price_el = item.xpath('.//span[@class="price-main-block"]//span[@class="visuallyhidden"]')
        if not price_el:
            continue
        price = float(re.sub('[^0-9.]', '', price_el[0].text_content()))
        item_link = item.xpath('.//a[contains(@class,"product-title-link")]/@href')
        if not item_link:
            continue
        result_items[price] = item_link[0]
    return result_items


def filter_by_model_number(items, model_num):
    return [i for i in items if re.search(model_num, i.text_content(), re.IGNORECASE)]


def extract_items(boundary, dom, model_num):
    items_selector = './/div[contains(@data-tl-id,"ProductTileListView-")]'
    items = dom.xpath(items_selector)
    items = filter_by_model_number(items, model_num)
    items = extract_price_url_dict(items)
    return filter_by_boundary(boundary, items)


# if __name__ == '__main__':
#     brand = "Proctor Silex", "43672" , 20, 1
#     model_num = "43672"
#     boundary = 20
#     file = os.path.join(os.path.dirname(__file__), 'tests/data/wallmart_search_page.html')
#     result = extract_items(boundary, html.fromstring(open(file, "r").read()), model_num)
#     print(result)
#     res = parse(brand, model_num, 15, '')
