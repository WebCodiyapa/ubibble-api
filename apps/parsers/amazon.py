import os
import re
import sys
import json
import time
import traceback
from subprocess import call, check_call, CalledProcessError
from os import devnull

from django.utils import timezone
from lxml import html
from apps.core.models import Item, Color, Size, Category, Brand
from apps.parsers.common import create_category




PROXY_TOR = 'socks5://127.0.0.1:9050'

def message(text):
    print(text)

def tor():
    fnull = open(devnull, 'w')
    try:
        tor_restart = check_call(["sudo", "service", "tor", "restart"], stdout=fnull, stderr=fnull)
        time.sleep(5)

        if tor_restart is 0:
            print(" {0}".format("[\033[92m+\033[0m] Anonymizer status \033[92m[ON]\033[0m"))
            print(" {0}".format("[\033[92m*\033[0m] Getting public IP, please wait..."))
            retries = 0
            my_public_ip = None
            while retries < 12 and not my_public_ip:
                retries += 1
    except CalledProcessError as err:
        print("\033[91m[!] Command failed: %s\033[0m" % ' '.join(err.cmd))


def get_model_number(source_page):
    dom2 = html.fromstring(source_page)
    if dom2.xpath('.//b[contains(.,"Item model")]/text()'):
        return dom2.xpath('.//li[contains(.,"Item model")]/text()')[0].strip()
    begin = 'Item model number'
    end = '</td>'
    start = source_page.find(begin) + len(begin) if begin in source_page else None
    stop = source_page[start:].find(end) if end in source_page else None
    model_num = source_page[start:start + stop]
    model_num = model_num.strip()
    start = model_num.rfind('>')
    model_num = model_num[start + 1:].strip()
    if len(model_num) == 0:
        model_num = dom2.xpath('.//tr[contains(.,"Item model number")]/td[2]/text()')
        model_num = ''.join(model_num)
        model_num = model_num.strip()
    if len(model_num) < 5:
        message('This item model is too short. It must be a mistake.')
        model_num = ''
    return model_num


def get_in_stock(dom):
    in_stock = dom.xpath('.//div[@id="availability"]/span[contains(.,"In Stock") or contains(.,"Available from")]')
    in_stock = len(in_stock) > 0
    return in_stock


def get_rating(dom):
    rating = dom.xpath('.//span[@id="acrPopover"]/@title')
    if rating:
        rating = rating[0][:3]
    else:
        rating = 'No rating for this product yet'
    return rating


def get_sizes(dom):
    sizes = dom.xpath('.//div[@id="variation_size_name"]//li[contains(@title,"Click to select")]/@title')
    if bool(sizes) is True:
        sizes = [i[16:] for i in sizes]
        sizes = ', '.join(sizes)
    else:
        sizes = 'Only default size available'
    return sizes


def get_colors(dom):
    colors = dom.xpath('.//div[@id="variation_color_name"]//li[contains(@title,"Click to select")]/@title')
    if bool(colors) is True:
        colors = [i[16:] for i in colors]
        colors = ', '.join(colors)
    else:
        colors = 'Only default color available'
    return colors

def price_to_float(price_str):
    return float(re.sub('[^0-9.]', '', price_str))

def get_price(dom):
    price = dom.xpath('.//span[@id="priceblock_ourprice"]/text()')
    if price:
        return price_to_float(price[0])
    price = dom.xpath('.//td[@class="comparison_baseitem_column"]//span[@class="a-offscreen"]/text()')
    if price:
        return price_to_float(price[0])
    return 0

def get_brand(dom):
    brand = dom.xpath('.//a[@id="bylineInfo"]/text()')[0].strip()
    return brand


def get_category(dom):
    category = dom.xpath("//div[@id='wayfinding-breadcrumbs_feature_div']/ul/li[not(@class)]/span/a/text()")
    category = ' > '.join([i.strip() for i in category]) if category else None
    return category


def get_image(dom):
    image = dom.xpath('.//img[@id="landingImage"]/@data-old-hires')
    if image:
        image = image[0]
    return image


def parse_new_item(asin, mydriver):
    try:
        url = "https://www.amazon.com/dp/" + asin
        mydriver.get(url)
        page = mydriver.get_source()
        dom = html.fromstring(page)
        try:
            title = dom.xpath('.//span[@id="productTitle"]/text()')[0].strip()
        except:
            message('Amazon has blocked our IP. We are changing it')
            tor()
            return

        model_num = get_model_number(dom)
        brand = get_brand(dom)
        category = get_category(dom)
        colors = get_colors(dom)
        sizes = get_sizes(dom)
        rating = get_rating(dom)
        image = get_image(dom)
        price = get_price(dom)

        i = Item.objects.create(
            sku=model_num,
            asin=asin,
            title=title,
            rating=rating,
            platform=Item.PLATFORM_VALUE_AMAZON,
            picture_url=image,
            price=price,
            url=url,
            update_date=timezone.now()
        )
        size, _ = Size.objects.get_or_create(name=sizes.lower())
        brand, _ = Brand.objects.get_or_create(name=brand.lower(), slug=brand.lower())
        category = create_category(category.lower())
        condition = None
        for c in colors.lower().split(', '):
            color, _ = Color.objects.get_or_create(name=c)
            i.colors.add(color)
        i.size = size
        i.brand = brand
        i.condition = condition
        i.category = category
        i.save()

    except Exception as e:
        message('!!!!!!!!!!!!!!!!!!!!!!!! A non-critical error occured!!!!!!!!!!!!!!!!!')
        traceback.print_exc()
        message('Код ошибки закончен')


def update_item(url, parent_id, webdriver, data=None):
    try:
        webdriver.get(url)
        page = webdriver.get_source()
        dom = html.fromstring(page)

        colors = get_colors(dom)
        sizes = get_sizes(dom)
        rating = get_rating(dom)
        in_stock = get_in_stock(dom)
        model_num = get_model_number(page)

        # asin = url.split("/")[-2]
        # json_el = dom.xpath(
        #     './/script[@type="a-state" and contains(.,"{0}") and contains(.,"itemDetails")]'.format(asin))
        # if in_stock and len(json_el) > 0:
        #     json_el = json.loads(json_el[0].text)
        #     itemDetails = json_el["itemDetails"]
        #     for k in itemDetails:
        #         if itemDetails[k]["asin"] == asin:
        #             price = itemDetails[k]["price"]
        price = get_price(dom)

        i = Item.objects.filter(id=parent_id)
        for c in colors.lower().split(', '):
            color, _ = Color.objects.get_or_create(name=c)
            i[0].colors.add(color)
        sizes, _ = Size.objects.get_or_create(name=sizes)
        i.update(
            sku=model_num,
            in_stock=in_stock,
            price=price,
            rating=rating,
            size=sizes,
            update_date=timezone.now()
        )
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)

        print("!!! GOT EXCEPTION during adding product %s" % e)
