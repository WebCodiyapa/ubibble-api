import datetime
import os

from django.test import TestCase
from django.utils import timezone
from lxml import html
from rest_framework.test import APIClient
from apps.core.models import Item
import amazon as am
import newegg as egg
import wallmart as wm

class ParsersTestCase(TestCase):

    def setUp(self):
        self.api_client = APIClient()
        self.item = Item.objects.create(price=120, is_processing=0, parent=None, cached_date=timezone.now(), update_date=timezone.now())
        Item.objects.create(parent=self.item, price=5)
        self.item_no_update_date = Item.objects.create(price=130, is_processing=0, parent=None, cached_date=timezone.now())
        self.newegg_search_page = os.path.join(os.path.dirname(__file__), 'data/newegg_search_page.html')
        self.wallmart_search_page = os.path.join(os.path.dirname(__file__), 'data/wallmart_search_page.html')
        self.newegg_item_page = os.path.join(os.path.dirname(__file__), 'data/newegg_item_page.html')
        self.wallmart_item_page = os.path.join(os.path.dirname(__file__), 'data/wallmart_item_page.html')

    def test_amazon_parser_selectors(self):
        file = os.path.join(os.path.dirname(__file__), 'data/amazon_item.html')
        with open(file, "r") as file:
            data = file.read()
            dom = html.fromstring(data)
            price = am.get_price(dom)
            self.assertEqual("$7.18", price)
            sku = am.get_model_number(data)
            self.assertEqual("L6LUC024-CS-R", sku)
            in_stock = am.get_in_stock(dom)
            self.assertEqual(True, in_stock)
            rating = am.get_rating(dom)
            self.assertEqual(rating, "4.1")
            sizes = am.get_sizes(dom)
            self.assertEqual("3 Feet, 6 Feet, 6 Inches, 9 Feet", sizes)
            colors = am.get_colors(dom)
            self.assertEqual("White, Black", colors)
            category = am.get_category(dom)
            self.assertEqual("Electronics > Computers & Accessories > Computer Accessories & Peripherals", category)
            image = am.get_image(dom)
            self.assertEqual("https://images-na.ssl-images-amazon.com/images/I/61RIfxJhRQL._SL1288_.jpg", image)
            brand = am.get_brand(dom)
            self.assertEqual("AmazonBasics", brand)


    def test_newegg_search_page_prices(self):
        with open(self.newegg_search_page, "r") as file:
            boundary_300_results = [415.47, 434.97, 579.58, 606.78]
            boundary_500_results = [579.58, 606.78]
            data = file.read()
            dom = html.fromstring(data)
            model_num = 'lc27f398fwnxza'
            items = egg.extract_items(300, dom, model_num)
            self.assertEqual(boundary_300_results, sorted(items.keys()))
            items = egg.extract_items(500, dom, model_num)
            self.assertEqual(boundary_500_results, sorted(items.keys()))

    def test_newegg_item_page_selectors(self):
        with open(self.newegg_item_page, "r") as file:
            data = file.read()
            dom = html.fromstring(data)
            expected_image = 'c1.neweggimages.com/neweggimage/productimage/a22f_1_20161012955591872.jpg'
            expected_title = 'samsung lc27f398fwnxza 27-inch curved led monitor - 1080p - 3000:1 - 60 hz - hdmi'
            expected_size = 'Standard size'
            expected_rating = 0
            expected_colors = 'Default color'
            self.assertEqual(expected_size, egg.get_size(dom))
            self.assertEqual(expected_rating, egg.get_rating(dom))
            self.assertEqual(expected_colors, egg.get_colors(dom))
            self.assertEqual(expected_title, egg.get_title(dom))
            self.assertEqual(expected_image, egg.get_picture(dom))


    def test_walmart_search_page_prices(self):
        with open(self.wallmart_search_page, "r") as file:
            model_num = "43672"
            data = file.read()
            dom = html.fromstring(data)
            items = wm.extract_items(10, dom, model_num)
            expected_items = {26.99: '/ip/Proctor-Silex-12-Cup-Programmable-Coffeemaker-Model-43672/16913485'}
            self.assertEqual(expected_items, items)

    def test_walmart_item_page_selectors(self):
        with open(self.wallmart_item_page, "r") as file:
            data = file.read()
            dom = html.fromstring(data)
            expected_image = 'http://i5.walmartimages.com/asr/1d9381a6-53c2-4d79-8e63-1b922fd36ab9_2.a427496a9555df22607a951a33dd3587.jpeg?odnWidth=450&odnHeight=450&odnBg=ffffff'
            expected_title = 'Proctor Silex 12 Cup Programmable Coffeemaker | Model# 43672'
            expected_size = 'Default size'
            expected_rating = '4.1'
            expected_colors = 'Default color'
            self.assertEqual(expected_size, wm.get_size(dom))
            self.assertEqual(expected_rating, wm.get_rating(dom))
            self.assertEqual(expected_colors, wm.get_colors(dom))
            self.assertEqual(expected_title, wm.get_title(dom))
            self.assertEqual(expected_image, wm.get_picture(dom))


    def test_alternatives_cache_is_old_and_not_processing(self):
        self.item.cached_date = timezone.now() - datetime.timedelta(hours=2)
        self.item.save()
        self.assertTrue(len(self.item.alternatives.all()) > 0)
        self.api_client.get('/api/items/{}/alternatives/'.format(self.item.id))
        self.assertTrue(len(self.item.alternatives.all()) == 0)
        self.item.refresh_from_db()
        self.assertEqual(self.item.is_processing, 4)


    def test_alternatives_update_date_is_none_and_not_processing(self):
        self.item_no_update_date.cached_date = timezone.now() - datetime.timedelta(hours=2)
        self.item_no_update_date.save()
        response = self.api_client.get('/api/items/{}/alternatives/'.format(self.item_no_update_date.id))
        self.assertFalse(response.json()['result'])

    def test_alternatives_processing(self):
        self.item.is_processing = 1
        response = self.api_client.get('/api/items/{}/alternatives/'.format(self.item.id))
        self.assertTrue(response.json()['result'])

    def test_alternatives_cache_is_ok(self):
        response = self.api_client.get('/api/items/{}/alternatives/'.format(self.item.id))
        self.assertTrue(response.json()['result'])





