# -*- coding: utf-8 -*-
import csv
import os
import sys

from django.core.management.base import BaseCommand
from apps.parsers.tasks import amazon_model_update

from apps.core.models import Item, Category


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
            reader = csv.DictReader(csvfile, delimiter='\t')
            for row in reader:
                rating = 0
                try:
                    rating = float(row['star_rating'])
                except:
                    pass

                try:
                    product_base_url = "https://www.amazon.com/dp/"
                    asin = row['product_id']
                    i = Item.objects.create(
                        asin=asin,
                        title=row['product_title'],
                        rating=rating,
                        platform=Item.PLATFORM_VALUE_AMAZON,
                        url=product_base_url + asin,
                        price=-1
                    )
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    print(exc_type, fname, exc_tb.tb_lineno)

                    print("!!! GOT EXCEPTION during adding product %s" % (e))
                    continue

                category = None
                if row['product_category']:
                    name = row['product_category'].lower()
                    category = self.category_cache.get(name, None)
                    if category is None:
                        category = self.create_category(name)
                        self.category_cache[name] = category
                i.category = category
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
