import random
import re
import requests
import os
import sys

from lxml import html
from .common import *
from apps.core.models import Item

MAIN_LINK = 'https://www.ebay.com/sch/i.html?_from=R40&_trksid=m570.l1313&_nkw={0}&_sacat=0&_ipg=200'


def parse(brand, model_num, amazon_price, parent_id):
    try:
        if brand in model_num:
            query = model_num
        else:
            query = brand + ' ' + model_num
        query = model_num
        query = query.split(' ')
        query = '+'.join(query)
        link = MAIN_LINK.format(query)

        header = random.choice(HEADERS_LIST)
        page = requests.get(link, headers={'User-Agent':header}).text
        dom = html.fromstring(page)

        if 'srp-save-null-search__heading' in page:
            raise ValueError("no items found")

        ad_per_page = dom.xpath('.//h1[@class="srp-controls__count-heading"]/span[1]/text()')
        ad_per_page = re.findall('[0-9]', ad_per_page[0])
        ad_per_page = int(''.join(ad_per_page)) + 1
        # First we are looking for the cheapest New product.
        current_prices = dom.xpath('.//li[position()<{0} and @class="s-item   "]//div[@class="s-item__info clearfix" and contains (.,"Brand New")]//div[@class="s-item__detail s-item__detail--primary"][1]//span[@class="s-item__price"]/text()[1]'.format(ad_per_page))
        current_prices = [float(re.sub(',','',price[1:])) for price in current_prices]
        current_links = dom.xpath('.//li[position()<{0} and @class="s-item   "]//div[@class="s-item__info clearfix" and contains (.,"Brand New") and not(contains(.,"See Price"))]/a/@href'.format(ad_per_page))

        current_dictionary = {}
        boundary = amazon_price*0.5
        for i in range(len(current_prices)):
            if current_prices[i] > boundary:
                current_dictionary[current_links[i]]=current_prices[i]

        check_counter = 0
        while True:
            if len(current_dictionary) == 0:
                break
            minimal = min(current_dictionary.values())
            for name, age in current_dictionary.items():
                if age == minimal:
                    minimal_n = name
                    break

            page_loc = requests.get(minimal_n, headers={'User-Agent':header}).text
            dom_loc = html.fromstring(page_loc)
            curr_cat = dom_loc.xpath('.//a[@class="scnd"]/span[@itemprop="name"]/text()')[0].strip()

            check_counter =+1
            if check_counter>50:
                break

            title = dom_loc.xpath('.//h1[@id="itemTitle"]/text()')[0]
            colors = dom_loc.xpath('.//select[@name="Color" or @name="Item Color"]/option[contains(@id,"opt")]/text()')
            if colors:
                ', '.join(colors)
                colors = colors
            else:
                colors = dom_loc.xpath('.//tr[contains(.,"Colour") and not(contains(.,"Manufact"))]/td[4]/text()')
                if colors:
                    colors = colors[0]
                    colors = colors.strip()
                else:
                    colors = dom_loc.xpath('.//h2[@itemprop="color"]/text()')
                    if colors:
                        colors = colors[0]
                        colors = colors.strip()
                    else:
                        colors = 'N/A'
            rating = dom_loc.xpath('.//a[@class="reviews-star-rating"]/@title')
            if rating:
                rating = rating[0][:3]
            else:
                rating = 0
            platform = 'eBay'
            size = ''.join(dom_loc.xpath('.//select[@name="Size"]/option[contains(@id,"opt")]/text()'))
            if not size:
                size = 'No size mentioned'
            picture = dom_loc.xpath('.//img[@class="img img500 " or @class="img img300 "]/@src')
            if picture:
                picture = picture[0]
            price = minimal
            if dom_loc.xpath('.//*[@id="prcIsum"]/text()'):
                price = dom_loc.xpath('.//*[@id="prcIsum"]/text()')[0]
                price = price.strip()
                price = price[4:]
            condition = 'Brand New'
            link = minimal_n
            total = [title,brand,colors,model_num,rating,platform,size,picture,price,condition,link]
            res = {
                'title': title,
                'brand': brand,
                'colors': colors,
                'sku': model_num,
                'rating': rating,
                'platform': Item.PLATFORM_VALUE_EBAY,
                'picture': picture,
                'price': price,
                'condition': condition,
                'size': size,
                'url': link
            }

            Item.create(res, parent_id)
            break

        # Now we are looking for the cheapest used product.
        current_prices = dom.xpath('.//li[position()<{0} and @class="s-item   "]//div[@class="s-item__info clearfix" and not(contains (.,"Brand New")) and '
                                   'not(contains(.,"Parts"))]//div[@class="s-item__detail s-item__detail--primary"][1]//span[@class="s-item__price"]/text()[1]'.format(ad_per_page))
        current_prices = [float(re.sub(',', '', price[1:])) for price in current_prices]
        current_links = dom.xpath('.//li[position()<{0} and @class="s-item   "]//div[@class="s-item__info clearfix" and not(contains (.,"Brand New")) and '
                                   'not(contains(.,"Parts")) and not(contains(.,"See Price"))]/a/@href'.format(ad_per_page))
        boundary = amazon_price * 0.4
        current_dictionary = {}
        for i in range(len(current_prices)):
            if current_prices[i] > boundary:
                current_dictionary[current_links[i]]=current_prices[i]

        while True:
            if len(current_dictionary) == 0:
                break
            minimal = min(current_dictionary.values())
            for name, age in current_dictionary.items():
                if age == minimal:
                    minimal_n = name
                    break

            check_counter =+1
            if check_counter>50:
                break

            page_loc = requests.get(minimal_n, headers={'User-Agent':header}).text
            dom_loc = html.fromstring(page_loc)
            curr_cat = dom_loc.xpath('.//a[@class="scnd"]/span[@itemprop="name"]/text()')[0].strip()
            title = dom_loc.xpath('.//h1[@id="itemTitle"]/text()')[0]
            colors = dom_loc.xpath('.//select[@name="Color" or @name="Item Color"]/option[contains(@id,"opt")]/text()')
            if colors:
                ', '.join(colors)
                colors = colors
            else:
                colors = dom_loc.xpath('.//tr[contains(.,"Colour") and not(contains(.,"Manufact"))]/td[4]/text()')
                if colors:
                    colors = colors[0]
                    colors = colors.strip()
                else:
                    colors = dom_loc.xpath('.//h2[@itemprop="color"]/text()')
                    if colors:
                        colors = colors[0]
                        colors = colors.strip()
                    else:
                        colors = 'N/A'

            rating = dom_loc.xpath('.//a[@class="reviews-star-rating"]/@title')
            if rating:
                rating = rating[0][:3]
            else:
                rating = 'No ratings yet'
            platform = 'eBay'
            size = ''.join(dom_loc.xpath('.//select[@name="Size"]/option[contains(@id,"opt")]/text()'))
            if not size:
                size = 'No size mentioned'
            picture = dom_loc.xpath('.//img[@class="img img500 " or @class="img img300 "]/@src')
            if picture:
                picture = picture[0]
            price = minimal
            if dom_loc.xpath('.//*[@id="prcIsum"]/text()'):
                price = dom_loc.xpath('.//*[@id="prcIsum"]/text()')[0]
                price = price.strip()
                price = price[4:]
            condition = 'Used'
            link = minimal_n

            total = [title,brand,colors,model_num,rating,platform,size,picture,price,condition,link]
            res = {
                'title': title,
                'brand': brand,
                'colors': colors,
                'sku': model_num,
                'rating': rating,
                'platform': Item.PLATFORM_VALUE_EBAY,
                'picture': picture,
                'price': price,
                'condition': condition,
                'size': size,
                'url': link
            }

            Item.create(res, parent_id);
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)

        print("!!! GOT EXCEPTION during adding product %s" % (e))
    increment_queue(parent_id, -1)
