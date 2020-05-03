# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from datetime import datetime, timedelta

from celery import shared_task
from constance import config
from django.db import transaction
from lxml import html

from apps.core.models import Item, SearchPage
from apps.parsers.common import WebDriver


@shared_task
def amazon_check_for_update_date():
    limit = config.AMAZON_MODEL_UPDATE_LIMIT
    update_gap = config.AMAZON_MODEL_UPDATE_TIME_GAP
    items = Item.objects.select_for_update().filter(parent=None,
                                                    update_date__lte=datetime.now() - timedelta(days=update_gap))[:limit]
    with transaction.atomic():
        Item.objects.filter(id__in=[i.id for i in items]).update(update_date=datetime.now())
        items = [(item.url, item.id) for item in items]
        amazon_model_update.delay(items)


@shared_task
def amazon_check_for_not_in_stock():
    limit = config.AMAZON_MODEL_UPDATE_LIMIT
    update_gap = config.AMAZON_MODEL_UPDATE_TIME_GAP
    items = Item.objects.select_for_update().filter(parent=None, in_stock=False,
                                                    update_date__lte=datetime.now() - timedelta(days=update_gap))[:limit]
    with transaction.atomic():
        Item.objects.filter(id__in=[i.id for i in items]).update(update_date=datetime.now())
        items = [(item.url, item.id) for item in items]
        amazon_model_update.delay(items)

@shared_task
def amazon_check_for_no_sku():
    limit = config.AMAZON_MODEL_UPDATE_LIMIT
    update_gap = config.AMAZON_MODEL_UPDATE_TIME_GAP
    items = Item.objects.select_for_update().filter(parent=None, sku=None,
                                                    update_date__lte=datetime.now() - timedelta(days=update_gap))[:limit]
    with transaction.atomic():
        Item.objects.filter(id__in=[i.id for i in items]).update(update_date=datetime.now())
        items = [(item.url, item.id) for item in items]
        amazon_model_update.delay(items)



@shared_task
def amazon_model_update(items):
    from .amazon import update_item
    webdriver = WebDriver()
    for item in items:
        update_item(*item, webdriver)
    webdriver.quit()


@shared_task
def amazon_model_create(asins):
    from .amazon import parse_new_item
    webdriver = WebDriver()
    for asin in asins:
        parse_new_item(asin, webdriver)
    webdriver.quit()



@shared_task
def track_amazon_search_pages():
    search_pages = SearchPage.objects.all()
    for page in search_pages:
        process_amazon_search_page(page.category_url)


def process_amazon_search_page(search_page):

    def pagination_finished(curr_page, dom):
        if bool(dom.xpath('.//ul[@class="a-pagination"]/li[contains(@class,"a-last") '
                                             ' and contains(@class,"a-disabled")]')):
            return True
        if curr_page > config.AMAZON_SEARCH_PAGE_DEPTH != 0:
            return True
        return False

    webdriver = WebDriver()
    page_number = search_page.curr_page
    batch_amount = 500
    asins_batch = []

    while True:
        webdriver.get(search_page.category_url.format(page_number))
        dom = html.fromstring(webdriver.get_source())

        # accumulating asins batch
        item_links = [str(link) for link in dom.xpath('.//a/@href') if "/dp/" in str(link)]
        asin_list = [l.split("/")[3] for l in item_links if len(l.split("/")) > 3]
        existed_asins = [item.asin for item in Item.objects.filter(asin__in=asin_list)]
        asins_to_parse = [asin for asin in asin_list if not asin in existed_asins]
        asins_batch += asins_to_parse

        # processing asins batch
        if len(asins_batch) > batch_amount or pagination_finished(page_number, dom):
            amazon_model_create.delay(asins_batch)
            asins_batch = []
        search_page.curr_page = page_number
        search_page.save()
        # check for exit from the loop
        page_number += 1
        if pagination_finished(page_number, dom):
            break
    search_page.curr_page = 1
    search_page.save()
    webdriver.quit()


@shared_task
def amazon_model_create(asins):
    from .amazon import parse_new_item
    webdriver = WebDriver()
    for asin in asins:
        parse_new_item(asin, webdriver)
    webdriver.quit()


@shared_task
def parse_alternative_wallmart(brand, model_num, amazon_price, parent_id):
    from .wallmart import parse
    parse(brand, model_num, amazon_price, parent_id)


@shared_task
def parse_alternative_ebay(brand, model_num, amazon_price, parent_id):
    from .ebay import parse
    parse(brand, model_num, amazon_price, parent_id)


@shared_task
def parse_alternative_bestbuy(brand, model_num, amazon_price, parent_id):
    from .bestbuy import parse
    parse(brand, model_num, amazon_price, parent_id)


@shared_task
def parse_alternative_newegg(brand, model_num, amazon_price, parent_id):
    from .newegg import parse
    parse(brand, model_num, amazon_price, parent_id)
