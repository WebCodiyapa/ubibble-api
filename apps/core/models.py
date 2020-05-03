# -*- coding: utf-8 -*-
import datetime
import os
import sys
from autoslug.fields import AutoSlugField
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.aggregates import StringAgg
from django.contrib.postgres.search import (
    SearchQuery, SearchRank, SearchVector, TrigramSimilarity,
)
from django.db import models
from django.db.models import signals as signals
from django.utils import timezone
from mptt.models import MPTTModel, TreeForeignKey

from .utils import str_trunc, ModelDiffMixin

__all__ = ['User']


def create_admin_user(app_config, **kwargs):
    if app_config.name != 'module':
        return None

    try:
        User.objects.get(username='admin')
    except User.DoesNotExist:
        print('Creating admin user: login: admin, password: 123')
        assert User.objects.create_superuser('admin', 'admin@localhost', '123')
    else:
        print('Admin user already exists')


signals.post_migrate.connect(create_admin_user)


# Abstract

class TimeStampedModel(models.Model):
    date_added = models.DateTimeField(auto_now_add=True, db_index=True)
    date_updated = models.DateTimeField(auto_now=True, db_index=True)

    class Meta(object):
        abstract = True


class OrderedModel(models.Model):
    order = models.PositiveIntegerField(default=0)

    class Meta(object):
        abstract = True
        ordering = ['order']


# User

class User(AbstractUser):
    pass


class Brand(TimeStampedModel):
    name = models.CharField(max_length=512)
    slug = AutoSlugField(editable=True, blank=True, null=True, populate_from=['name', ], unique=True, max_length=512)

    def __str__(self):
        return self.name


class Color(TimeStampedModel):
    name = models.CharField(max_length=512)

    def __str__(self):
        return self.name


class Size(TimeStampedModel):
    name = models.CharField(max_length=512)

    def __str__(self):
        return self.name


class Condition(TimeStampedModel):
    name = models.CharField(max_length=512)

    def __str__(self):
        return self.name


search_vectors = (
        SearchVector('sku', weight='A', config='english') +
        SearchVector('title', weight='B', config='english') +
        SearchVector('brand__name', weight='C', config='english') +
        SearchVector('size__name', weight='D', config='english') +
        SearchVector('condition__name', weight='D', config='english') +
        SearchVector(StringAgg('colors__name', delimiter=' '), weight='D', config='english')
)


class Category(MPTTModel):
    name = models.TextField(blank=True, null=True)
    parent = TreeForeignKey('Category', blank=True, null=True,
                            related_name="children", db_index=True, on_delete=models.PROTECT)

    class MPTTMeta:
        order_insertion_by = ['name']

    def __str__(self):
        return f'{self.name}'


class ItemManager(models.Manager):
    def search(self, text):
        if text == "":
            # search_rank = SearchRank(search_vectors, search_query)
            return self.get_queryset().annotate(
                search=search_vectors
            )
        else:
            search_query = SearchQuery(text, config='english')
            search_rank = SearchRank(search_vectors, search_query)
            return self.get_queryset().annotate(
                search=search_vectors
            ).filter(
                search=search_query
            ).annotate(
                rank=search_rank
            ).order_by('-rank')


class SearchPage(TimeStampedModel):
    category_url = models.TextField(blank=True, null=True)
    last_tracked_date = models.DateTimeField(default=None, blank=True, null=True)
    cur_page = models.IntegerField(default=1)


class Item(TimeStampedModel, ModelDiffMixin):
    PLATFORM_VALUE_AMAZON = 'amazon'
    PLATFORM_VALUE_EBAY = 'ebay'
    PLATFORM_VALUE_BESTBUY = 'bestbuy'
    PLATFORM_VALUE_WALLMART = 'wallmart'
    PLATFORM_VALUE_NEWEGG = 'newegg'
    PLATFORM_VALUES = (
        (PLATFORM_VALUE_AMAZON, 'Amazon'),
        (PLATFORM_VALUE_EBAY, 'Ebay'),
        (PLATFORM_VALUE_BESTBUY, 'BestBuy'),
        (PLATFORM_VALUE_WALLMART, 'WallMart'),
        (PLATFORM_VALUE_NEWEGG, 'NewEgg'),
    )

    title = models.TextField(blank=True, null=True)
    sku = models.CharField(max_length=512, blank=True, null=True, db_index=True)
    brand = models.ForeignKey(Brand, blank=True, null=True, on_delete=models.PROTECT, related_name='items')
    colors = models.ManyToManyField(Color, blank=True, related_name='items')
    rating = models.FloatField(blank=True, default=0)
    platform = models.CharField(max_length=32, default=PLATFORM_VALUES[0][0], choices=PLATFORM_VALUES, blank=True,
                                null=True)
    size = models.ForeignKey(Size, blank=True, null=True, on_delete=models.PROTECT, related_name='items')
    condition = models.ForeignKey(Condition, blank=True, null=True, on_delete=models.PROTECT, related_name='items')
    price = models.FloatField()
    url = models.CharField(max_length=2048)
    picture_url = models.CharField(max_length=2048)
    parent = models.ForeignKey('Item', blank=True, null=True, related_name="alternatives", default=None,
                               on_delete=models.PROTECT)
    cached_date = models.DateTimeField(default=None, blank=True, null=True)
    category = models.ForeignKey('Category', related_name='categories', on_delete=models.PROTECT, null=True, blank=True)
    is_processing = models.IntegerField(default=0)
    update_date = models.DateTimeField(default=None, blank=True, null=True)
    in_stock = models.BooleanField(default=True)
    objects = ItemManager()
    asin = models.CharField(max_length=50, blank=True, null=True, db_index=True, unique=True)

    def save(self, **kwargs):
        if self.id and 'is_processing' in self.changed_fields and self.is_processing == 0:
            self.cached_date = timezone.now()
        return super(Item, self).save(**kwargs)

    def cache_is_older_than(self, hours):
        return self.cached_date is None or self.cached_date < (timezone.now() - datetime.timedelta(hours=hours))

    def alternatives_in_progress(self):
        return self.is_processing != 0

    @staticmethod
    def create(row, parent=None):
        rating = 0
        try:
            rating = float(row['rating'])
        except:
            pass

        price = str(row['price'])

        try:
            i = Item.objects.create(
                sku=row['sku'].lower(),
                title=row['title'],
                rating=rating,
                platform=row['platform'],
                picture_url=row['picture'],
                price=price.replace('$', '').split('-')[0].replace(',', ''),
                url=row['url'],
                parent_id=parent
            )
            size = None
            if row['size']:
                name = row['size'].lower()
                size, _ = Size.objects.get_or_create(name=name)
            i.size = size

            condition = None
            if row['condition']:
                name = row['condition'].lower()
                condition, _ = Condition.objects.get_or_create(name=name)
            i.condition = condition

            brand = None
            if row['brand']:
                name = row['brand'].lower()
                brand, _ = Brand.objects.get_or_create(name=name, slug=name)
            i.brand = brand

            if row['colors']:
                for c in row['colors'].lower().split(', '):
                    color, _ = Color.objects.get_or_create(name=c)
                    i.colors.add(color)
            i.save()
            return i
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)

            print("!!! GOT EXCEPTION during adding product %s" % (e))
            return

    def __str__(self):
        return "%s" % self.id
