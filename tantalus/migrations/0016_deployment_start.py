# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-11-30 20:06
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tantalus', '0015_auto_20171128_1917'),
    ]

    operations = [
        migrations.AddField(
            model_name='deployment',
            name='start',
            field=models.BooleanField(default=False, verbose_name=''),
        ),
    ]