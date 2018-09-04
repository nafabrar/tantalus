# -*- coding: utf-8 -*-
# Generated by Django 1.11.14 on 2018-08-10 18:37
from __future__ import unicode_literals

from django.db import migrations


def populate_sequence_file_info(apps, schema_editor):
    FileResource = apps.get_model('tantalus', 'FileResource')
    SequenceFileInfo = apps.get_model('tantalus', 'SequenceFileInfo')

    for file_resource in FileResource.objects.all():
        sequence_file_info = SequenceFileInfo(
            file_resource=file_resource,
            owner=file_resource.owner,
            read_end=file_resource.read_end,
            genome_region=file_resource.genome_region,
            index_sequence=file_resource.index_sequence,
        )
        sequence_file_info.save()


class Migration(migrations.Migration):

    dependencies = [
        ('tantalus', '0058_historicalsequencefileinfo_sequencefileinfo'),
    ]

    operations = [
        migrations.RunPython(populate_sequence_file_info)
    ]