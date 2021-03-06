# -*- coding: utf-8 -*-
# Generated by Django 1.11.14 on 2018-08-10 18:36
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tantalus', '0057_gscwgsbamquery_tag_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistoricalSequenceFileInfo',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('read_end', models.PositiveSmallIntegerField(null=True)),
                ('genome_region', models.CharField(max_length=50, null=True)),
                ('index_sequence', models.CharField(blank=True, max_length=50, null=True)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('file_resource', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='tantalus.FileResource')),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('owner', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
                'verbose_name': 'historical sequence file info',
            },
        ),
        migrations.CreateModel(
            name='SequenceFileInfo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('read_end', models.PositiveSmallIntegerField(null=True)),
                ('genome_region', models.CharField(max_length=50, null=True)),
                ('index_sequence', models.CharField(blank=True, max_length=50, null=True)),
                ('file_resource', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='tantalus.FileResource')),
                ('owner', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
