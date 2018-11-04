# -*- coding: utf-8 -*-
# Generated by Django 1.11.14 on 2018-11-04 19:27
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tantalus', '0073_auto_20181101_1925'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fileresource',
            name='compression',
            field=models.CharField(choices=[('GZIP', 'gzip'), ('BZIP2', 'bzip2'), ('SPEC', 'SpEC'), ('UNCOMPRESSED', 'uncompressed')], default='UNCOMPRESSED', max_length=50),
        ),
        migrations.AlterField(
            model_name='historicalfileresource',
            name='compression',
            field=models.CharField(choices=[('GZIP', 'gzip'), ('BZIP2', 'bzip2'), ('SPEC', 'SpEC'), ('UNCOMPRESSED', 'uncompressed')], default='UNCOMPRESSED', max_length=50),
        ),
    ]
