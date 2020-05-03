# -*- coding: utf-8 -*-
from django.contrib.admin.options import ModelAdmin, StackedInline
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib import admin
from django import forms
from jet.admin import CompactInline
from django_mptt_admin.admin import DjangoMpttAdmin
from django.contrib.admin.options import ModelAdmin, StackedInline, TabularInline

from .models import User, Brand, Color, Size, Item, Condition, Category


# @admin.register(User)
# class UserAdmin(UserAdmin):
    # pass


class OrderedAdmin(ModelAdmin):
    # mandatory display & editable 'order' field
    list_display = ('order',)
    list_editable = ('order',)
    ordering = ('order',)

    class Media:
        js = ['/static/js/admin_list_reorder.js', ]


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'date_added', 'date_updated')
    list_filter = ('date_added', 'date_updated')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ['name']}


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'date_added', 'date_updated')
    list_filter = ('date_added', 'date_updated')
    search_fields = ('name',)


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'date_added', 'date_updated')
    list_filter = ('date_added', 'date_updated')
    search_fields = ('name',)


@admin.register(Condition)
class ConditionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'date_added', 'date_updated')
    list_filter = ('date_added', 'date_updated')
    search_fields = ('name',)


class ItemAltAdmin(TabularInline):
    model = Item
    extra = 0
    fields = ('id', 'platform', 'price', 'condition', 'picture_url', 'url')
    readonly_fields = ('id', )


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'sku',
        'brand',
        'rating',
        'platform',
        'size',
        'price',
        'condition',
        'url',
        'picture_url',
        'date_added', 
        'date_updated'
    )
    inlines = (ItemAltAdmin, )
    list_filter = ('brand', 'size', 'condition', 'date_added', 'date_updated')
    raw_id_fields = ('colors',)


@admin.register(Category)
class CategoryAdmin(DjangoMpttAdmin, ModelAdmin):
    mptt_level_indent = 20
    save_on_top = True
    search_fields = ('name', )
    list_display = ('id', 'name', 'parent', )
