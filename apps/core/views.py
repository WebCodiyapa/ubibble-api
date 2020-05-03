import json

from django.http import JsonResponse
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework_jwt.settings import api_settings
from rest_framework_jwt.views import JSONWebTokenAPIView

from .serializers import JSONWebTokenSerializer
from cleverad.models import (
    User
)

jwt_decode_handler = api_settings.JWT_DECODE_HANDLER
jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER


class ObtainJSONWebToken(JSONWebTokenAPIView):
    """
    API View that receives a POST with a user's email and password along with company_name.

    Returns a JSON Web Token that can be used for authenticated requests.
    """
    serializer_class = JSONWebTokenSerializer


@api_view(['POST'])
@permission_classes([AllowAny, ])
def check_email(request):
    res = False
    requestBody = json.loads(request.body.decode('utf-8'))
    email = requestBody.get('email', None)
    if email and not CustomUser.objects.filter(email__iexact=email).exists():
        res = True

    return JsonResponse({'status': 'Success', 'result': res})
