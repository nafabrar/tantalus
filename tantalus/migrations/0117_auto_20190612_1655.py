# Generated by Django 2.2 on 2019-06-12 16:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tantalus', '0116_auto_20190411_0110'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalsequencedataset',
            name='note',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='sequencedataset',
            name='note',
            field=models.TextField(blank=True, null=True),
        ),
    ]
