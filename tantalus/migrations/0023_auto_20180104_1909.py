# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-01-04 19:09
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tantalus', '0022_gscdlppairedfastqquery_gsc_library_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bamfile',
            name='bam_file',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='bam_file', to='tantalus.FileResource'),
        ),
        migrations.AlterUniqueTogether(
            name='bamfile',
            unique_together=set([]),
        ),
    ]
