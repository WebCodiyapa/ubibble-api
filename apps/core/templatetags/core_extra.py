# -*- coding: utf-8 -*-

import pytils
import datetime

from django import template
from django.utils.timezone import utc
from django.conf import settings


register = template.Library()


@register.simple_tag
def setting(name):
    return str(settings.__getattr__(name))


@register.simple_tag
def absolute_url_host(request):
    return request.build_absolute_uri('/')[:-1]


@register.simple_tag
def choose_plural(num, form1, form2, form5):
    return pytils.numeral.choose_plural(int(num), (unicode(form1), unicode(form2), unicode(form5)))


@register.filter
def to_class_name(value):
    return value.__class__.__name__


MONTHS = ('января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля',
          'августа', 'сентября', 'октября', 'ноября', 'декабря')
WEEKDAYS = ('в понедельник', 'во вторник', 'в среду', 'в четверг',
            'в пятницу', 'в субботу', 'в воскресенье')


@register.simple_tag
def local_format_date(date):
    if type(date) in (int, long, float):
        date = datetime.datetime.utcfromtimestamp(date)

    now = datetime.datetime.utcnow().replace(tzinfo=utc)

    if date > now:
        date = now

    local_date = date
    local_now = now
    local_yesterday = local_now - datetime.timedelta(hours=24)
    difference = now - date
    seconds = difference.seconds
    days = difference.days

    format = None

    if days == 0:
        if seconds < 50:
            if seconds == 0:
                return 'только что'
            else:
                return '{0:g} {1}'.format(seconds, choose_plural(seconds,
                                                                 'секунда назад', 'секунды назад', 'секунд назад'
                ))

        if seconds < 50 * 60:
            minutes = round(seconds / 60.0)
            return '{0:g} {1}'.format(minutes, choose_plural(minutes,
                                                             'минута назад', 'минуты назад', 'минут назад'
            ))

        hours = round(seconds / (60.0 * 60))
        return '{0:g} {1}'.format(hours, choose_plural(hours,
                                                       'час назад', 'часа назад', 'часов назад'
        ))
    elif days == 1 and local_date.day == local_yesterday.day:
        format = 'вчера в %(time)s'
    elif days < 5:
        format = '%(weekday)s в %(time)s'
    elif days < 334:
        format = '%(day)s %(month_name)s в %(time)s'

    if format is None:
        format = '%(day)s %(month_name)s %(year)s в %(time)s'

    return format % {
        'month_name': MONTHS[local_date.month - 1],
        'weekday': WEEKDAYS[local_date.weekday()],
        'day': str(local_date.day),
        'year': str(local_date.year),
        'time': '%d:%02d' % (local_date.hour, local_date.minute)
    }

@register.simple_tag
def format_number_sep(n):
    r = []
    for i, c in enumerate(reversed(str(n))):
        if i and (not (i % 3)):
            r.insert(0, ' ')
        r.insert(0, c)
    return ''.join(r)


@register.simple_tag()
def multiply(qty, unit_price, *args, **kwargs):
    # you would need to do any localization of the result here
    return qty * unit_price