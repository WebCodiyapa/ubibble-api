# Generated by Django 2.2.2 on 2019-06-03 17:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_auto_20190603_2022'),
    ]

    operations = [
        migrations.AlterField(
            model_name='item',
            name='title',
            field=models.TextField(blank=True, null=True),
        ),
    ]