# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-02-06 21:14
from __future__ import unicode_literals

from django.db import migrations


def add_read_groups(apps, schema_editor):
    AbstractDataSet = apps.get_model('tantalus', 'AbstractDataSet')
    ReadGroup = apps.get_model('tantalus', 'ReadGroup')

    for d in AbstractDataSet.objects.all():
        for l in d.lanes.all():
            r = ReadGroup.objects.create(
                sample=d.dna_sequences.sample,
                dna_library=d.dna_sequences.dna_library,
                index_sequence=d.dna_sequences.index_sequence,
                sequence_lane=l)
            d.read_groups.add(r)


class Migration(migrations.Migration):

    dependencies = [
        ('tantalus', '0028_auto_20180206_2113'),
    ]

    operations = [
        migrations.RunPython(add_read_groups)
    ]

