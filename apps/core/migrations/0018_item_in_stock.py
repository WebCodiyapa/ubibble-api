# Generated by Django 2.2.2 on 2019-11-01 14:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_auto_20191101_1147'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='in_stock',
            field=models.BooleanField(default=True),
        ),
    ]
