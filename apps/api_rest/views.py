# -*- coding: utf-8 -*-
import os
import sys
import datetime
import json
from constance import config
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from raven.contrib.django.raven_compat.models import client as raven_client
from rest_framework import serializers
from rest_framework.decorators import api_view, detail_route
from rest_framework.decorators import permission_classes
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ViewSet

from apps.parsers.common import increment_queue
from apps.core.models import User, Brand, Color, Size, Item, Condition, Category
from apps.core.serializers import (BrandSerializer, CategorySerializer, ColorSerializer, ConditionSerializer,
                                   SizeSerializer, ItemSerializer, ItemAltSerializer)

from apps.parsers.tasks import parse_alternative_newegg, parse_alternative_ebay, \
    parse_alternative_bestbuy, parse_alternative_wallmart, amazon_model_update


@api_view(['GET'])
@permission_classes([AllowAny, ])
def get_constants(request):
    res = []

    cache_key = 'constants'
    res_cache = cache.get(cache_key, None)
    if res_cache is not None:
        res = json.loads(res_cache)
    else:
        res.append({
            'name': 'BRANDS',
            'values': BrandSerializer(Brand.objects.all(), many=True).data
        })
        res.append({
            'name': 'CATEGORIES',
            'values': CategorySerializer(Category.objects.all(), many=True).data
        })
        res.append({
            'name': 'COLORS',
            'values': ColorSerializer(Color.objects.all(), many=True).data
        })
        res.append({
            'name': 'SIZES',
            'values': SizeSerializer(Size.objects.all(), many=True).data
        })
        res.append({
            'name': 'CONDITIONS',
            'values': ConditionSerializer(Condition.objects.all(), many=True).data
        })
        res.append({
            'name': 'EXCHANGE_RATE',
            'values': config.EXCHANGE_RATE
        })
        res.append({
            'name': 'SEARCH_PAGE',
            'values': settings.REST_FRAMEWORK['PAGE_SIZE']
        })

        res_cache = json.dumps(res)
        try:
            cache.set(cache_key, res_cache, 60 * 5)
        except Exception as e:
            raven_client.captureException()

    return JsonResponse({'result': res})


class ItemsListView(ListCreateAPIView, RetrieveUpdateAPIView, ViewSet):
    serializer_class = ItemSerializer
    queryset = Item.objects.all()
    permission_classes = (AllowAny,)
    paginator = PageNumberPagination()

    def get_queryset(self):
        q = self.request.GET.get('q', None)
        category_id = self.request.GET.get('category_id', None)
        res = Item.objects.filter()

        if q:
            res = Item.objects.search(q)

        if category_id:
            parent_category = Category.objects.get(id=category_id)
            res = res.filter(category__lft__gte=parent_category.lft,
                             category__lft__lte=parent_category.rght,
                             category__tree_id=parent_category.tree_id)

        pmin = self.request.GET.get('pmin', None)
        pmax = self.request.GET.get('pmax', None)
        brand_id = self.request.GET.get('brand_id', None)
        colors_id = self.request.GET.get('colors_id', None)
        condition_id = self.request.GET.get('condition_id', None)
        size_id = self.request.GET.get('size_id', None)

        if pmin:
            pmin = pmin.split('$')[0]
            res = res.filter(price__gte=pmin)

        if pmax:
            pmax = pmax.split('$')[0]
            res = res.filter(price__lte=pmax)

        if brand_id:
            res = res.filter(brand_id=brand_id)

        if colors_id:
            res = res.filter(colors__in=[colors_id])

        if condition_id:
            res = res.filter(condition_id=condition_id)

        if size_id:
            res = res.filter(size_id=size_id)

        return res

    @detail_route(methods=['GET'])
    def alternatives(self, request, *args, **kwargs):
        obj = self.get_object()
        res = []

        # if not obj.alternatives_in_progress() and obj.cache_is_older_than(hours=1):
        if True:
            try:
                if obj.update_date is None:
                    amazon_model_update([(obj.url, obj.id)])
                else:
                    obj.alternatives.all().delete()
                    # increment_queue(obj.id, 4)
                    # parse_alternative_newegg(obj.brand.name if obj.brand else '', obj.sku, obj.price, obj.id)
                    # parse_alternative_wallmart(obj.brand.name if obj.brand else '', obj.sku, obj.price, obj.id)
                    parse_alternative_bestbuy(obj.brand.name if obj.brand else '', obj.sku, obj.price, obj.id)
                    # parse_alternative_ebay.delay(obj.brand.name if obj.brand else '', obj.sku, obj.price, obj.id)

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print(exc_type, fname, exc_tb.tb_lineno)
                print("!!! GOT EXCEPTION during adding product %s" % e)
        else:
            ser = ItemAltSerializer(obj.alternatives.all(), many=True)
            res = ser.data

        return JsonResponse({'result': res})

    # def paginate_queryset(self, *args, **kwargs):
    # if self.request.GET.get('archived') or self.request.GET.get('page'):
    # return super(AlertsListView, self).paginate_queryset(*args, **kwargs)
    # else:
    # return None
