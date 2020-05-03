# -*- coding: utf-8 -*-
import datetime
from django.utils import timezone
from django.contrib.auth import authenticate, user_logged_in
from django.utils.translation import ugettext as _
from rest_framework import serializers
from rest_framework_jwt.compat import PasswordField, Serializer
from rest_framework_jwt.settings import api_settings

from apps.core.models import User, Brand, Color, Size, Category, Item, Condition

jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'is_active', )


class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = ('id', 'name', )


class SizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Size
        fields = ('id', 'name', )


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ('id', 'name', )


class ConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Condition
        fields = ('id', 'name', )


class ItemAltSerializer(serializers.ModelSerializer):
    condition = ConditionSerializer()

    class Meta:
        model = Item
        fields = ('platform', 'price', 'url', 'condition',)

class RecursiveField(serializers.Serializer):
    def to_native(self, value):
        return CategorySerializer(value, context={"parent": self.parent.object, "parent_serializer": self.parent})

class CategorySerializer(serializers.ModelSerializer):
    children = RecursiveField(many=True, required=False)

    class Meta:
        model = Category
        fields = ('id', 'name', 'children', 'level')

class ItemSerializer(serializers.ModelSerializer):
    condition = ConditionSerializer()
    size = SizeSerializer()
    brand = BrandSerializer()
    colors = ColorSerializer(many=True)
    alternatives = ItemAltSerializer(many=True)
    is_cached = serializers.SerializerMethodField(read_only=True)

    def get_is_cached(self, obj):
        return obj.cached_date is not None and obj.cached_date > (timezone.now() - datetime.timedelta(hours=1))

    class Meta:
        model = Item
        fields = ('colors', 'id', 'alternatives', 'is_cached', 'title', 'sku', 'brand', 'is_processing',
                  'rating', 'platform', 'size', 'price', 'condition', 'url', 'picture_url',)


class JSONWebTokenSerializer(Serializer):
    """
    Serializer class used to validate a company name, email and password.

    Returns a JSON Web Token that can be used to authenticate later calls.
    """
    email = serializers.EmailField()
    password = PasswordField(write_only=True)

    def validate(self, attrs):
        credentials = {
            'email': attrs.get('email'),
            'password': attrs.get('password')
        }

        if all(credentials.values()):
            # it's required to get User object from email
            try:
                user = CustomUser.objects.get(email=credentials['email'])
            except CustomUser.DoesNotExist:
                msg = _('Unable to login with provided credentials.')
                raise serializers.ValidationError(msg)

            user = authenticate(username=user.email,
                                password=credentials['password'])

            if user:
                user_logged_in.send(sender=user.__class__, request=self.context['request'], user=user)
                if not user.is_active:
                    msg = _('User account is disabled.')
                    raise serializers.ValidationError(msg)

                payload = jwt_payload_handler(user)

                return {
                    'token': jwt_encode_handler(payload),
                    'user': {'email': credentials['email']}
                }
            else:
                msg = _('Unable to login with provided credentials.')
                raise serializers.ValidationError(msg)
        else:
            msg = _('Must include "email" and "password".')
            raise serializers.ValidationError(msg)


