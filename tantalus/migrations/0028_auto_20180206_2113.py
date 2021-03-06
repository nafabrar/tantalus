# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-02-06 21:13
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tantalus', '0027_auto_20180119_1852'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistoricalReadGroup',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('index_sequence', models.CharField(blank=True, max_length=50, null=True)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('dna_library', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='tantalus.DNALibrary')),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('sample', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='tantalus.Sample')),
                ('sequence_lane', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='tantalus.SequenceLane')),
            ],
            options={
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
                'verbose_name': 'historical read group',
            },
        ),
        migrations.CreateModel(
            name='ReadGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('index_sequence', models.CharField(blank=True, max_length=50, null=True)),
                ('dna_library', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tantalus.DNALibrary')),
                ('sample', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tantalus.Sample')),
                ('sequence_lane', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tantalus.SequenceLane')),
            ],
        ),
        migrations.AddField(
            model_name='abstractdataset',
            name='read_groups',
            field=models.ManyToManyField(to='tantalus.ReadGroup'),
        ),
        migrations.AlterUniqueTogether(
            name='readgroup',
            unique_together=set([('sample', 'dna_library', 'index_sequence', 'sequence_lane')]),
        ),
    ]
