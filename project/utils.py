import os
import string
import random
from django.conf import settings
from django.contrib.auth import logout
from django.forms import widgets
from django.forms.models import model_to_dict
from django.core.files.uploadedfile import UploadedFile
from django.forms.fields import Field, EMPTY_VALUES
from django.core.exceptions import ValidationError
from django.forms.utils import flatatt
from django.forms.widgets import FileInput, ClearableFileInput, FILE_INPUT_CONTRADICTION
from django.utils.datastructures import MultiValueDict
from django.utils.deconstruct import deconstructible
from django.utils.translation import ugettext, ugettext_lazy as _
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe


# Template context processor
def get_settings(request):
    return dict(settings=settings)


def generate_uid():
    chars = string.digits + string.ascii_letters

    return ''.join(random.choice(chars) for _ in range(10))


class ModelDiffMixin(object):
    """
    A model mixin that tracks model fields' values and provide some useful api
    to know what fields have been changed.
    """

    def __init__(self, *args, **kwargs):
        super(ModelDiffMixin, self).__init__(*args, **kwargs)
        self.__initial = self._dict

    @property
    def diff(self):
        d1 = self.__initial
        d2 = self._dict
        diffs = [(k, (v, d2[k])) for k, v in d1.items() if v != d2[k]]
        return dict(diffs)

    @property
    def has_changed(self):
        return bool(self.diff)

    @property
    def changed_fields(self):
        return self.diff.keys()

    def get_field_diff(self, field_name):
        """
        Returns a diff for field if it's changed and None otherwise.
        """
        return self.diff.get(field_name, None)

    def save(self, *args, **kwargs):
        """
        Saves model and set initial state.
        """
        super(ModelDiffMixin, self).save(*args, **kwargs)
        self.__initial = self._dict

    @property
    def _dict(self):
        return model_to_dict(self, fields=[field.name for field in
                             self._meta.fields])


@deconstructible
class PathAndRename(object):

    def __init__(self, sub_path):
        self.path = sub_path

    def __call__(self, instance, filename):
        ext = filename.split('.')[-1]
        # set filename as random string
        uid = generate_uid()
        filename = '{}.{}'.format(uid, ext)
        # return the whole path to the file
        return os.path.join(self.path, filename)


def jwt_response_payload_handler(token, user=None, request=None):
    return {
        'token': token,
        'email': user['email'],
    }
