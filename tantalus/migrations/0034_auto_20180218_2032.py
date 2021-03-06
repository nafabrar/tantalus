# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-02-18 20:32
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tantalus', '0033_auto_20180209_2133'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dnalibrary',
            name='library_type',
            field=models.CharField(choices=[('EXOME', 'Bulk Whole Exome Sequence'), ('WGS', 'Bulk Whole Genome Sequence'), ('RNASEQ', 'Bulk RNA-Seq'), ('SC_WGS', 'Single Cell Whole Genome Sequence'), ('SC_RNASEQ', 'Single Cell RNA-Seq'), ('DNA_AMPLICON', 'Targetted DNA Amplicon Sequence')], max_length=50),
        ),
        migrations.AlterField(
            model_name='historicaldnalibrary',
            name='library_type',
            field=models.CharField(choices=[('EXOME', 'Bulk Whole Exome Sequence'), ('WGS', 'Bulk Whole Genome Sequence'), ('RNASEQ', 'Bulk RNA-Seq'), ('SC_WGS', 'Single Cell Whole Genome Sequence'), ('SC_RNASEQ', 'Single Cell RNA-Seq'), ('DNA_AMPLICON', 'Targetted DNA Amplicon Sequence')], max_length=50),
        ),
    ]
