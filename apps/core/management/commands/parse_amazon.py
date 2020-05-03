# -*- coding: utf-8 -*-
import csv
import os
import sys
import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models import User, Brand, Color, Size, Item, Condition, Category


class Command(BaseCommand):
    size_cache = {}
    condition_cache = {}
    colors_cache = {}
    brand_cache = {}
    category_cache = {}

    def add_arguments(self, parser):
        parser.add_argument('filename', help="File to load")

    def handle(self, *args, **options):
        filename = options.get('filename')

        with open(filename) as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')

            for row in reader:
                rating = 0
                try:
                    rating = float(row['rating'])
                except:
                    pass

                try:
                    # getting ASIN from 5-th position
                    # EXAMPLE url https://www.amazon.com/product-slug/dp/B07CJW2WDC/
                    asin = row['url'].split("/")[5]
                    i = Item.objects.create(
                        sku=row['sku'].lower(),
                        asin=asin,
                        title=row['title'],
                        rating=rating,
                        platform=Item.PLATFORM_VALUE_AMAZON,
                        picture_url=row['picture'],
                        price=row['price'].replace('$', '').split('-')[0].replace(',', ''),
                        url=row['url']
                    )
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    print(exc_type, fname, exc_tb.tb_lineno)

                    print("!!! GOT EXCEPTION during adding product %s" % (e))
                    continue


                size = None
                if row['size']:
                    name = row['size'].lower()
                    size = self.size_cache.get(name, None)
                    if size is None:
                        size, _ = Size.objects.get_or_create(name=name)
                        self.size_cache[name] = size
                i.size = size

                condition = None
                if row['condition']:
                    name = row['condition'].lower()
                    condition = self.condition_cache.get(name, None)
                    if condition is None:
                        condition, _ = Condition.objects.get_or_create(name=name)
                        self.condition_cache[name] = condition
                i.condition = condition

                category = None
                if row['category']:
                    name = row['category'].lower()
                    category = self.category_cache.get(name, None)
                    if category is None:
                        category = self.create_category(name)
                        self.category_cache[name] = category
                i.category = category

                brand = None
                if row['brand']:
                    name = row['brand'].lower()
                    brand = self.brand_cache.get(name, None)
                    if brand is None:
                        brand, _ = Brand.objects.get_or_create(name=name, slug=name)
                        self.brand_cache[name] = brand
                i.brand = brand

                if row['colors']:
                    for c in row['colors'].lower().split(', '):
                        color = self.colors_cache.get(c, None)
                        if color is None:
                            color, _ = Color.objects.get_or_create(name=c)
                            self.colors_cache[c] = color
                            i.colors.add(color)
                i.save()


    def create_category(self, category_string):
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
