import random
import os
import logging
import json
import datetime

from constance import config
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client as HttpClient, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.zone_coverage.models import ZoneCoverage, ZoneType, SecurityZoneCoverage
from apps.alerts.models import AlertType, Alert, Path, AlertAttachment, Chat, UserSpam
from apps.api_auth.models import User, AppUser, Client, Operator, HomeUser, EmergencyContact, Relation

from apps.api_auth.serializers import UserProfileSerializer, EmergencyContactSerializer, OperatorSerializer
from apps.alerts.serializers import AlertSerializer, AlertAttachmentSerializer, PathSerializer, ChatSerializer

from apps.subscription.models import Order, Payment, PromoCode

logging.disable(logging.ERROR)


@override_settings(
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache', }}
)
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class RESTTest(TestCase):
    fixtures = ['alerttypes', 'relations', ]
    maxDiff = None

    def setUp(self):
        config.HELPER_LIMIT_RADIUS_MAP = 5000
        config.DISABLE_HELPERS_COORDINATES_WRITE = False
        settings.RAVEN_CONFIG = {}
        settings.TWILIO_NUMBER = None
        settings.TWILIO_SMS_NUMBER = None
        self.http_client = HttpClient()
        self.api_client = APIClient()
        self.client = Client.objects.create(name='Client 1')
        self.zone_type = ZoneType.objects.create(name='safe')
        self.zone = ZoneCoverage.objects.create(name='test_zone',  area='{"type": "MultiPolygon", "coordinates": [[[[-99.20321546554612, 19.427397026483202], [-99.1772945976331, 19.424159241882077], [-99.18398939133623, 19.43856688795457], [-99.18999753952514, 19.43937626835062], [-99.1941174125746, 19.442613749582883], [-99.2193516349824, 19.455239309313253], [-99.21917997360609, 19.445527427482162], [-99.21626173019979, 19.444394336736572], [-99.21162687302137, 19.435976843571023], [-99.20321546554612, 19.427397026483202]]]]}')
        self.sec_zone = SecurityZoneCoverage.objects.create(type=self.zone_type, name='test_zone',  area='{"type": "MultiPolygon", "coordinates": [[[[-99.20321546554612, 19.427397026483202], [-99.1772945976331, 19.424159241882077], [-99.18398939133623, 19.43856688795457], [-99.18999753952514, 19.43937626835062], [-99.1941174125746, 19.442613749582883], [-99.2193516349824, 19.455239309313253], [-99.21917997360609, 19.445527427482162], [-99.21626173019979, 19.444394336736572], [-99.21162687302137, 19.435976843571023], [-99.20321546554612, 19.427397026483202]]]]}')
        self.user = User.objects.create(username="+79081234568", email="79081234568@localhost")
        self.operator = Operator.objects.create(user=self.user, assigned_zone_id=self.zone.id)
        self.appuser = AppUser.objects.create(user=self.user, phone_number="+79081234568")
        self.token = "Token " + Token.objects.create(user=self.user).key
        self.homeuser = HomeUser.objects.create(client=self.client, user=self.user, home_phone="+79081234569", home_address="address", family_name="Joe")
        self.emergency_contact = EmergencyContact.objects.create(user=self.user, phone_number="+79081234567", relation=Relation.objects.first())
        self.helper_user = User.objects.create(username="+79081234570", email="79081234570@localhost")
        self.appuser_helper = AppUser.objects.create(user=self.helper_user, phone_number="+79081234570", is_helper=True)
        self.helper_token = "Token " + Token.objects.create(user=self.helper_user).key

    def tearDown(self):
        pass

    def test_00_test_str(self):
        alert = Alert.objects.create(user=self.user, alert_type_id=1)
        chat = Chat.objects.create(user=self.user, alert=alert, text="msg")
        spam = UserSpam.objects.create(appuser=self.appuser, alert=alert, operator=self.operator)
        s = str(spam)
        s = str(chat)
        s = str(alert)
        s = str(self.client)
        s = str(self.user)
        s = str(self.appuser)
        s = str(self.homeuser)
        s = str(self.operator)
        s = str(self.emergency_contact)
        s = str(self.zone)
        s = str(self.zone_type)
        s = str(AlertType.objects.last())
        s = str(Relation.objects.last())

    def test_01_signup_app(self):
        response = self.http_client.post(reverse('signup_app'), data={})
        self.assertEqual(response.status_code, 400)
        self.assertTrue('phone' in response.data)

        response = self.http_client.post(reverse('signup_app'), data={
            'phone': 'abc',
        })
        self.assertEqual(response.status_code, 400)
        self.assertTrue('phone' in response.data)

        response = self.http_client.post(reverse('signup_app'), data={
            'phone': self.appuser.phone_number,
        })
        self.user.refresh_from_db()
        self.appuser.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, UserProfileSerializer(self.user).data)

        response = self.http_client.post(reverse('signup_app'), data={
            'phone': "+79081234562",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['payment_type'], User.PAYMENT_FREE)

        response = self.http_client.post(reverse('signup_app'), data={
            'payment_type': 'fake',
        })
        self.assertEqual(response.status_code, 400)
        self.assertTrue('payment_type' in response.data)

        response = self.http_client.post(reverse('signup_app'), data={
            'payment_type': User.PAYMENT_FREE,
        })
        self.assertEqual(response.status_code, 400)
        self.assertFalse('payment_type' in response.data)

        response = self.http_client.post(reverse('signup_app'), data={
            'phone': self.appuser.phone_number,
            'payment_type': User.PAYMENT_CORPORATE,
        })
        self.assertEqual(response.status_code, 400)

        self.assertTrue('client' in response.data)
        self.assertFalse(self.user.is_premium)
        response = self.http_client.post(reverse('signup_app'), data={
            'phone': self.appuser.phone_number,
            'client': self.client.id,
            'payment_type': User.PAYMENT_CORPORATE,
        })
        self.user.refresh_from_db()
        self.appuser.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, UserProfileSerializer(self.user).data)
        self.assertTrue(self.user.is_premium)

        response = self.http_client.post(reverse('signup_app'), data={
            'phone': self.appuser.phone_number,
            'client': self.client.id,
            'payment_type': User.PAYMENT_FREE,
        })
        self.user.refresh_from_db()
        self.appuser.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, UserProfileSerializer(self.user).data)

        response = self.http_client.post(reverse('signup_app'), data={
            'phone': self.appuser.phone_number,
            'payment_type': User.PAYMENT_CONEKTA,
        })
        self.user.refresh_from_db()
        self.appuser.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, UserProfileSerializer(self.user).data)

        response = self.http_client.post(reverse('signup_app'), data={
            'is_helper': True,
            'phone': self.appuser.phone_number,
            'payment_type': User.PAYMENT_CONEKTA,
        })
        self.user.refresh_from_db()
        self.appuser.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.appuser.is_helper, True)
        self.assertDictEqual(response.data, UserProfileSerializer(self.user).data)

    def test_01_signup_home(self):
        pass


    def test_02_login(self):
        response = self.http_client.get(reverse('login'))
        self.assertEqual(response.status_code, 405)

        self.user.set_unusable_password()
        self.user.save()
        response = self.http_client.post(reverse('login'), data={
            'email': self.user.email,
            'password':'123'
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual({'non_field_errors': ['Unable to login with provided credentials.']}, response.data)

        self.user.set_password('123')
        self.user.save()
        response = self.http_client.post(reverse('login'), data={
            'email': self.user.email,
            'password':'123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue('auth_token' in response.data)
        self.jwt_token = "JWT " + response.data['auth_token']

    def test_03_me(self):
        response = self.http_client.get(reverse('user'))
        self.assertEqual(response.status_code, 403)
        self.assertEqual({'detail': 'Authentication credentials were not provided.'}, response.data)

        response = self.http_client.get(reverse('user'), HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, UserProfileSerializer(self.user).data)

        age = 12
        now = datetime.date.today()
        birthday = now.replace(now.year-age)
        birthday_str = birthday.isoformat()

        last_online = timezone.now()
        last_online_str = last_online.isoformat()
        changes = {
            "email": "a@b.com",
            "first_name": "first_name",
            "last_name": "last_name",
            "appuser": {
                # "emergency_contacts": [],
                "sex": "male",
                "birthday": birthday_str,
                "age": age,
                "blood_type": "AB",
                "alergies": "butter",
                "chronic_diseases": "asdflmaonia",
                "pin_code": "1234",
                # "avatar": None,
                "keyword": "key1"
            },
            "operator": {
                "assigned_zone": None,
                "last_online": last_online_str
            }
        }

        response = self.http_client.patch(reverse('user'), \
                                         json.dumps(changes),
                                         content_type='application/json',
                                         HTTP_AUTHORIZATION=self.token)
        self.appuser.refresh_from_db()
        self.user.refresh_from_db()
        self.appuser.user.refresh_from_db()
        self.appuser.user.operator.refresh_from_db()
        for k, v in changes.items():
            if type(v) == str:
                self.assertEqual(getattr(self.appuser.user, k), v)
            elif type(v) == dict:
                for k1, v1 in v.items():
                    if k1 == 'birthday':
                        self.assertEqual(getattr(getattr(self.appuser.user, k), k1), birthday)
                    elif k1 == 'last_online':
                        self.assertEqual(getattr(getattr(self.appuser.user, k), k1), last_online)
                    else:
                        self.assertEqual(getattr(getattr(self.appuser.user, k), k1), v1)

        self.assertEqual(response.status_code, 200)
        for k, v in changes.items():
            if type(v) == str:
                self.assertEqual(response.data[k], v)
            elif type(v) == dict:
                for k1, v1 in v.items():
                    if k1 == 'last_online':
                        self.assertEqual(parse_datetime(response.data[k][k1]), parse_datetime(last_online_str))
                    else:
                        self.assertEqual(response.data[k][k1], v1)


        self.assertEqual(3, User.objects.all().count())
        response = self.api_client.delete(reverse('user'), HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(2, User.objects.all().count())

    def test_03_avatar(self):
        self.assertEqual(None, self.appuser.avatar)

        response = self.api_client.patch(reverse('set_avatar'), data={}, HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['avatar_url'], None)

        avatar = SimpleUploadedFile("file.jpg", b"file_content", content_type="image/jpeg")

        response = self.api_client.patch(reverse('set_avatar'), \
                                        data={'avatar': avatar}, \
                                        HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.data['avatar_url'], None)
        self.appuser.refresh_from_db()
        self.assertNotEqual(None, self.appuser.avatar)

    def test_04_check_email(self):
        response = self.http_client.post(reverse('check_email'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['result'])

        response = self.http_client.post(reverse('check_email'), json.dumps({'email': self.user.email}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['result'])

        response = self.http_client.post(reverse('check_email'), json.dumps({'email': self.user.email, 'type': 'appuser'}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['result'])

        response = self.http_client.post(reverse('check_email'), json.dumps({'email': self.user.email, 'type': 'type'}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['result'])

        response = self.http_client.post(reverse('check_email'), json.dumps({'email': 'a@b.com'}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['result'])


    def test_05_check_homephone(self):
        response = self.http_client.post(reverse('check_homephone'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['result'])

        response = self.http_client.post(reverse('check_homephone'), json.dumps({'phone': str(self.homeuser.home_phone)}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['result'])

        response = self.http_client.post(reverse('check_homephone'), json.dumps({'phone': '12345'}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['result'])


    def test_06_new_password(self):
        self.user.set_password('123')
        self.user.save()

        user = authenticate(username=self.user.email, password='123')
        self.assertEqual(user.id, self.user.id)

        response = self.http_client.post(reverse('new_password'))
        self.assertEqual(response.status_code, 403)

        response = self.http_client.post(reverse('new_password'), HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['result'])

        response = self.http_client.post(reverse('new_password'), json.dumps({
            'id': self.user.id,
            'password': '456'
        }), content_type='application/json', HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['result'])

        user = authenticate(username=self.user.email, password='456')
        self.assertEqual(user.id, self.user.id)


    def test_07_emergency_contact_appuser(self):
        self.assertEqual(self.emergency_contact.appuser, None)

        response = self.http_client.post(reverse('signup_app'), data={
            'phone': self.emergency_contact.phone_number,
            'payment_type': User.PAYMENT_FREE,
        })
        self.assertEqual(response.status_code, 200)

        self.emergency_contact.refresh_from_db()
        self.assertNotEqual(self.emergency_contact.appuser, None)

        response = self.http_client.get(reverse('alert-emergency-alerts'), {
        }, HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_08_list_alerts(self):
        response = self.http_client.get(reverse('alert-list'))
        self.assertEqual(response.status_code, 403)

        response = self.http_client.get(reverse('alert-list'), HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

        Alert.objects.create(user=self.user, alert_type_id=1)

        response = self.http_client.get(reverse('alert-list'), HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_09_alert_create(self):
        Alert.objects.all().update(alert_state=Alert.ALERT_STATE_ARCHIVED)
        alert_type = random.choice(AlertType.objects.all().values_list('id', flat=True))
        self.appuser.last_lat = 19.4315655
        self.appuser.last_lon = -99.1934047
        self.appuser.save()

        self.user.trial_alerts = 1
        self.user.save()

        response = self.http_client.post(reverse('alert-list'), data={
            "alert_type": alert_type
        })
        self.assertEqual(response.status_code, 403)

        # response = self.http_client.post(reverse('alert-list'), data={
            # "alert_type": alert_type
        # }, HTTP_AUTHORIZATION=self.token)
        # self.assertEqual(response.status_code, 400)
        # self.assertEqual(response.data, ['No operators available'])

        self.operator.is_online = True
        self.operator.save()

        response = self.http_client.post(reverse('alert-list'), data={
            "alert_type": alert_type
        }, HTTP_AUTHORIZATION=self.token)

        last_alert = Alert.objects.last()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(last_alert.alert_state, Alert.ALERT_STATE_NEW)
        self.assertEqual(last_alert.operator, self.operator)
        #lil hack to overcome operator being set async, we checked that it is correct already
        a_ser = AlertSerializer(last_alert).data
        a_ser['operator'] = response.data['operator']
        a_ser['address'] = response.data['address']
        self.assertDictEqual(response.data, a_ser)


        Alert.objects.all().update(alert_state=Alert.ALERT_STATE_ARCHIVED)
        self.user.refresh_from_db()
        self.user.payment_type = User.PAYMENT_FREE
        self.user.save()
        response = self.http_client.post(reverse('alert-list'), data={
            "alert_type": alert_type
        }, HTTP_AUTHORIZATION=self.token)
        last_alert = Alert.objects.last()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(last_alert.alert_state, Alert.ALERT_STATE_FREE)
        self.assertEqual(last_alert.operator, None)
        a_ser = AlertSerializer(last_alert).data
        a_ser['operator'] = response.data['operator']
        a_ser['address'] = response.data['address']
        self.assertDictEqual(response.data, a_ser)

    def test_11_emergency_list(self):
        response = self.http_client.get(reverse('emergencycontact-list'))
        self.assertEqual(response.status_code, 403)

        response = self.http_client.get(reverse('emergencycontact-list'), HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_12_emergency_get(self):
        response = self.http_client.get(reverse('emergencycontact-detail', kwargs={'pk':self.emergency_contact.id}))
        self.assertEqual(response.status_code, 403)

        response = self.http_client.get(reverse('emergencycontact-detail', kwargs={'pk':self.emergency_contact.id}), HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, EmergencyContactSerializer(self.emergency_contact).data)

        response = self.http_client.get(reverse('emergencycontact-detail', kwargs={'pk':self.emergency_contact.id+1}), HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 404)

    def test_12_emergency_post(self):
        response = self.http_client.post(reverse('emergencycontact-list'))
        self.assertEqual(response.status_code, 403)

        response = self.http_client.get(reverse('emergencycontact-list'), HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

        response = self.http_client.post(reverse('emergencycontact-list'), data={},HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 400)
        self.assertTrue('relation_pk' in response.data)
        self.assertTrue('phone_number' in response.data)

        response = self.http_client.post(reverse('emergencycontact-list'), data={
            'relation_pk': Relation.objects.last().id,
            'phone_number': "+7495123123123"
        },HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 400)
        self.assertTrue('phone_number' in response.data)

        response = self.http_client.post(reverse('emergencycontact-list'), data={
            'relation_pk': Relation.objects.last().id,
            'phone_number': "+7495123123123"
        },HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 400)
        self.assertTrue('phone_number' in response.data)

        response = self.http_client.post(reverse('emergencycontact-list'), data={
            'relation_pk': Relation.objects.last().id,
            'phone_number': "+525512341234"
        },HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 201)

        response = self.http_client.get(reverse('emergencycontact-list'), HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_13_get_alerts(self):
        alert = Alert.objects.create(user=self.user, alert_type_id=1)
        response = self.http_client.get(reverse('alert-detail', kwargs={'pk':alert.id}))
        self.assertEqual(response.status_code, 403)

        response = self.http_client.get(reverse('alert-detail', kwargs={'pk':alert.id}), HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, AlertSerializer(alert).data)

        response = self.http_client.get(reverse('alert-detail', kwargs={'pk':alert.id+1}), HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 404)

    def test_14_attachment(self):
        alert = Alert.objects.create(user=self.user, alert_type_id=1)
        response = self.http_client.get(reverse('alert-detail', kwargs={'pk':alert.id}))
        self.assertEqual(response.status_code, 403)

        response = self.http_client.get(reverse('alert-detail', kwargs={'pk':alert.id}), HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['attachments']), 0)

        attach = AlertAttachment.objects.create(type=AlertAttachment.FILE_TYPE_AUDIO, alert=alert)

        response = self.http_client.get(reverse('alert-detail', kwargs={'pk':alert.id}), HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['attachments']), 1)
        self.assertDictEqual(response.data['attachments'][0], AlertAttachmentSerializer(attach).data)

        alert = Alert.objects.create(user=self.user, alert_type_id=1)
        response = self.http_client.post(reverse('alert-attachment', kwargs={'pk':alert.id}))
        self.assertEqual(response.status_code, 403)

        alert = Alert.objects.create(user=self.user, alert_type_id=1)
        response = self.http_client.post(reverse('alert-attachment', kwargs={'pk':alert.id}), HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 400)
        self.assertTrue('file' in response.data)

        video = SimpleUploadedFile("file.mp4", b"file_content", content_type="video/mp4")
        response = self.http_client.post(reverse('alert-attachment', kwargs={'pk': alert.id}),\
                                         data={
                                             'file': video,
                                             'alert_type': AlertAttachment.FILE_TYPE_VIDEO
                                         }, HTTP_AUTHORIZATION=self.token)
        attach = AlertAttachment.objects.last()
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), AlertAttachmentSerializer(attach).data)

    def test_15_locations_list(self):
        response = self.http_client.get(reverse('path-list'))
        self.assertEqual(response.status_code, 403)

        response = self.http_client.get(reverse('path-list'), HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

        response = self.http_client.post(reverse('path-list'), data={}, HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 400)
        self.assertTrue('lon' in response.data)
        self.assertTrue('lat' in response.data)
        self.assertTrue('alert' in response.data)

        self.appuser.last_lat = None
        self.appuser.last_lon = None
        self.appuser.save()

        alert = Alert.objects.create(user=self.user, alert_type_id=1)
        response = self.http_client.post(reverse('path-list'), \
                                         data={
                                            'alert': alert.id,
                                             'lon': 1,
                                             'lat': 2,
                                         },HTTP_AUTHORIZATION=self.token)

        self.appuser.refresh_from_db()
        self.assertEqual(self.appuser.last_lat, 2)
        self.assertEqual(self.appuser.last_lon, 1)
        self.assertEqual(response.status_code, 201)
        self.assertDictEqual(response.data, PathSerializer(alert.paths.last()).data)


        alert = Alert.objects.create(user=self.user, alert_type_id=1)
        response = self.http_client.post(reverse('path-list'), \
                                         data={
                                             'lon': 4,
                                             'lat': 5,
                                         },HTTP_AUTHORIZATION=self.token)

        self.appuser.refresh_from_db()
        self.assertEqual(self.appuser.last_lat, 5)
        self.assertEqual(self.appuser.last_lon, 4)
        self.assertEqual(response.status_code, 201)
        self.assertDictEqual(response.data, PathSerializer(alert.paths.last()).data)

        response = self.http_client.get(reverse('path-detail', kwargs={'pk': alert.paths.last().id}), HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.data, PathSerializer(alert.paths.last()).data)

        response = self.http_client.post(reverse('path-list'), \
                                         data={
                                             'lon': 4,
                                             'lat': 5,
                                         }, HTTP_AUTHORIZATION=self.helper_token)
        self.assertEqual(response.status_code, 200)

    def test_16_messages(self):
        alert = Alert.objects.create(user=self.user, alert_type_id=1)
        response = self.http_client.get(reverse('alert-messages-list', kwargs={'alert_pk': alert.id}))
        self.assertEqual(response.status_code, 403)

        response = self.http_client.get(reverse('alert-messages-list', kwargs={'alert_pk': alert.id}), HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

        response = self.http_client.post(reverse('alert-messages-list', kwargs={'alert_pk': alert.id}), data={},HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 400)
        self.assertTrue('text' in response.data)

        response = self.http_client.post(reverse('alert-messages-list', kwargs={'alert_pk': alert.id}), \
                                         data={
                                             'text': 'hello'
                                         },HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 201)
        self.assertDictEqual(response.data, ChatSerializer(alert.messages.last()).data)

        response = self.http_client.get(reverse('alert-messages-list', kwargs={'alert_pk': alert.id}), HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    '''
    def test_17_check_subscription(self):
        response = self.http_client.get(reverse('user'), HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['subscription_start'], None)
        self.assertEqual(response.data['subscription_end'], None)

        order = Order.objects.create(user=self.user, payment_type=User.PAYMENT_CONEKTA)
        payment = Payment.objects.create(order=order)

        response = self.http_client.get(reverse('user'), HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['subscription_start'], None)
        self.assertEqual(response.data['subscription_end'], None)

        payment.is_paid = True
        payment.save()

        response = self.http_client.get(reverse('user'), HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.data['subscription_start'], None)
        self.assertNotEqual(response.data['subscription_end'], None)
    '''

    def test_18_check_reset_payment_id(self):
        user = User.objects.create(username="+79081234561", payment_type=User.PAYMENT_FREE, email="79081234561@localhost.test.com")
        self.assertEqual(user.payment_type, User.PAYMENT_FREE)
        self.assertEqual(user.payment_ext_id, None)
        self.assertEqual(user.payment_card_last4, None)
        self.assertEqual(user.subscription_start, None)
        self.assertEqual(user.subscription_end, None)

        user.payment_type = User.PAYMENT_CONEKTA
        user.payment_ext_id = 'tok_test_visa_4242'
        user.save()

        self.assertEqual(user.payment_card_last4, '4242')

        user.payment_type = User.PAYMENT_FREE
        user.save()
        self.assertEqual(user.payment_ext_id, None)
        self.assertEqual(user.payment_card_last4, None)

    def test_19_reset_password(self):
        response = self.http_client.post(reverse('password_reset'), data={}, HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 400)
        self.assertTrue('email' in response.data)

        response = self.http_client.post(reverse('password_reset'), data={
            'email': 'not_exists@email.com'
        }, HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 204)

        response = self.http_client.post(reverse('password_reset'), data={
            'email': self.user.email
        }, HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 204)

        self.user.set_password('123')
        self.user.save()
        response = self.http_client.post(reverse('password_reset'), data={
            'email': self.user.email
        }, HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 204)

    def test_20_subscribe(self):
        self.assertEqual(0, Order.objects.count())
        response = self.http_client.post(reverse('subscribe'), data={}, HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 400)
        self.assertTrue('payment_type' in response.data)

        response = self.http_client.post(reverse('subscribe'), data={
            'payment_ext_id': '',
            'payment_type': User.PAYMENT_STRIPE
        }, HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 400)
        self.assertTrue('payment_ext_id' in response.data)

        response = self.http_client.post(reverse('subscribe'), data={
            'payment_ext_id': '',
            'payment_type': User.PAYMENT_FREE
        }, HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(1, Order.objects.count())

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)
        self.assertTrue(self.user.trial_period_end is None)
        self.assertFalse(self.user.has_valid_subscription())
        promo_code = PromoCode.objects.create(
            code="promo1",
            expire=timezone.now() + datetime.timedelta(days=1),
            free_months=1
        )

        promo_code.max_redemptions_per_coupon = 1
        self.assertTrue(promo_code.is_valid_for_user(self.user))
        promo_code.times_redeemed = 1
        self.assertFalse(promo_code.is_valid_for_user(self.user))

        response = self.http_client.post(reverse('subscribe'), data={
            'payment_ext_id': '',
            'payment_type': User.PAYMENT_FREE,
            'promo_code': promo_code.code
        }, HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(1, Order.objects.count())

        self.user.refresh_from_db()
        self.assertTrue(self.user.has_valid_subscription())
        self.assertTrue(self.user.trial_period_end is not None)
        self.assertTrue(self.user.is_premium)

        response = self.http_client.post(reverse('subscribe'), data={
            'payment_ext_id': 'tok_test_visa_4242',
            'payment_type': User.PAYMENT_CONEKTA
        }, HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(2, Order.objects.count())

    def test_21_alert_create_demo(self):
        Alert.objects.all().update(alert_state=Alert.ALERT_STATE_ARCHIVED)
        alert_type = random.choice(AlertType.objects.all().values_list('id', flat=True))
        self.appuser.last_lat = 19.4315655
        self.appuser.last_lon = -99.1934047
        self.appuser.save()

        self.user.payment_type = User.PAYMENT_FREE
        self.user.trial_alerts = 1
        self.user.save()

        self.operator.is_online = True
        self.operator.save()

        response = self.http_client.post(reverse('alert-list'), data={
            "alert_type": alert_type
        }, HTTP_AUTHORIZATION=self.token)

        last_alert = Alert.objects.last()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(last_alert.operator, self.operator)
        a_ser = AlertSerializer(last_alert).data
        a_ser['operator'] = response.data['operator']
        a_ser['address'] = response.data['address']
        self.assertDictEqual(response.data, a_ser)

    def test_22_alert_helper(self):
        self.appuser_helper.last_lat = 19.4315655
        self.appuser_helper.last_lon = 99.1934047
        self.appuser_helper.save()
        self.assertEqual(self.appuser_helper.nearby_alerts.count(), 0)

        self.appuser.last_lat = 19.4315655
        self.appuser.last_lon = -49.1934047
        self.appuser.save()

        response = self.http_client.get(reverse('alert-nearby'), {
        }, HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

        alert_type = random.choice(AlertType.objects.all().values_list('id', flat=True))
        response = self.http_client.post(reverse('alert-list'), data={
            "alert_type": alert_type
        }, HTTP_AUTHORIZATION=self.token)
        self.assertEqual(self.appuser_helper.nearby_alerts.count(), 0)
        self.assertEqual(response.status_code, 201)
        Alert.objects.all().delete()

        self.appuser_helper.last_lat = 19.4315655
        self.appuser_helper.last_lon = -49.1934047
        self.appuser_helper.save()

        response = self.http_client.post(reverse('alert-list'), data={
            "alert_type": alert_type
        }, HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.appuser_helper.nearby_alerts.count(), 1)
        last_alert = Alert.objects.last()
        self.assertEqual(response.data['id'], last_alert.id)
        self.assertEqual(response.data['helpers_nearby'], 1)
        self.assertEqual(response.data['helpers_accepted'], 0)

        response = self.http_client.get(reverse('alert-nearby'), {
        }, HTTP_AUTHORIZATION=self.helper_token)
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.json(), [])

        response = self.http_client.post(reverse('alert-accept', kwargs={'pk':last_alert.id}))
        self.assertEqual(response.status_code, 403)

        response = self.http_client.post(reverse('alert-accept', kwargs={'pk':last_alert.id}), HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 400)

        response = self.http_client.post(reverse('alert-accept', kwargs={'pk':last_alert.id}), HTTP_AUTHORIZATION=self.helper_token)
        self.assertEqual(response.status_code, 200)

        response = self.http_client.get(reverse('user'), HTTP_AUTHORIZATION=self.helper_token)

    def test_23_helpers_list(self):
        self.appuser.is_helper = False
        self.appuser.last_lat = 19.4315655
        self.appuser.last_lon = -99.1934047
        self.appuser.save()

        # response = self.http_client.get(reverse('helper-list'), HTTP_AUTHORIZATION=self.token)
        # self.assertEqual(response.status_code, 400)
        # self.assertEqual(response.json()['error'], "Some of the required param is missing (lat, lon, radius)")

        response = self.http_client.get(reverse('helper-list'), {
            'lat': 19.4315655,
            'lon': -99.1934047,
            'radius': 1000
        }, HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(0, len(response.json()))

        response = self.http_client.get(reverse('helper-list'), {
            'lat': 19.4315655,
            'lon': 99.1934047,
            'radius': 1000
        }, HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(0, len(response.json()))

        self.appuser.is_helper = True
        self.appuser.save()
        response = self.http_client.get(reverse('helper-list'), {
            'lat': 19.4315655,
            'lon': -99.1834047,
            'radius': 1000
        }, HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(0, len(response.json()))

        self.appuser.is_helper = True
        self.appuser.save()
        response = self.http_client.get(reverse('helper-list'), {
            'lat': 19.4315655,
            'lon': -99.1834047,
            'radius': 5000
        }, HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(0, len(response.json()))
