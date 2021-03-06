# -*- coding: utf-8 -*-
# Generated by Django 1.11.14 on 2018-12-05 00:30
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

#jira TANTA-209
#first part is same as TANTA-153

#tables referencing tantalus_sample(sample_id):
#   tantalus_submission(sample_id), tantalus_sequencedataset(sample_id), -- 1:N relation
#   tantalus_sample_projects(sample_id), tantalus_resultsdataset_samples(sample_id) -- M:N relation
#
#original data does not restored after rollback of the migration
#to fix it for the debugging run at the beginning
#   create table sa as (select * from tantalus_sample);
#   create table ds as (select id, sample_id val from tantalus_sequencedataset);
#   create table ps as (select * from tantalus_sample_projects);
#
#after migration rollback run
#insert into tantalus_sample ( -- insert deleted records
#    select * from sa
#        where id not in (select id from tantalus_sample));
#
#update tantalus_sequencedataset s -- restore updated data
#    set sample_id=t.val
#  from ds t
#  where s.id=t.id
#    and s.sample_id!=t.val;
#
#insert into tantalus_sample_projects ( -- insert deleted records
#    select * from ps
#        where id not in (select id from tantalus_sample_projects));
#

sample_id_fixup = {
      'VBA0082'     : 'SA095'
    , 'BM01-20'     : 'SA238'
    , 'GT470'       : 'SA299'
    , 'GVM0383'     : 'SA299'
    , 'GVM0630'     : 'SA300'
    , 'GVM0278_BC'  : 'SA296N'
}

#renames sample_from |-> sample_to,
#deletes record sample_from
def sample_fixup(apps, class_name):
    Sample = apps.get_model('tantalus', 'Sample')
    SequenceDataset = apps.get_model('tantalus', 'SequenceDataset')
    Submission = apps.get_model('tantalus', 'Submission')

    for k,v in sample_id_fixup.items():
        try:
            sample_from = Sample.objects.get(sample_id=k)
            sample_to   = Sample.objects.get(sample_id=v)

            # updating 1:N
            for child in [SequenceDataset,Submission]:
                for s in child.objects.filter(sample_id=sample_from.id):
                    print("{} sample {}".format(s.name, s.sample.sample_id))
                    assert sample_from.sample_id in s.name
                    s.sample_id = sample_to.id
                    s.name = s.name.replace(sample_from.sample_id, sample_to.sample_id)
                    s.save()
                    s = child.objects.get(id=s.id)
                    print("{} sample {}".format(s.name, s.sample.sample_id))

            # updating M:N
            #projects is property (set) of Sample
            sample_to.projects.add(*list(sample_from.projects.all()))
            sample_from.projects = []

            #resultsdataset is virtual property (set) of Sample
            sample_to.resultsdataset_set.add(*list(sample_from.resultsdataset_set.all()))
            sample_from.resultsdataset_set = []

            sample_to.save()
            sample_from.save() #probably needed to save M:N field

            #there should be no reference to old sample_id left
            sample_from.delete()
            print("sample_fixup(); '%s' -> '%s' done;" % (k,v))

        except Sample.DoesNotExist:
            print("sample_fixup(); sample_id not found: '%s';" % (k))
            pass

seq_ds_fixup = {
      ('SA221N','A06669') : 'SA221'
    , ('SA239N','A06672') : 'SA239'
    , ('SA423N','A08453') : 'SA423'
    , ('SA425N','A08454') : 'SA425'
}

#renames sample_from |-> sample_to,
#deletes record sample_from
def sequence_dataset_fixup(apps, class_name):
    Sample = apps.get_model('tantalus', 'Sample')
    SequenceDataset = apps.get_model('tantalus', 'SequenceDataset')

    for k,v in seq_ds_fixup.items():
        try:
            print('\n')
            for ds in SequenceDataset.objects.filter(sample__sample_id=k[0]).filter(library__library_id=k[1]):
                sa = Sample.objects.get(sample_id=v)
                ds.sample_id = sa
                ds.save()
                print("sequence_dataset_fixup(); {},{}; done;" . format(k,v))
            print("sequence_dataset_fixup(); finished: {}; {};" . format(k,v))
        except SampleDataset.DoesNotExist:
            print("sequence_dataset_fixup(); sample_id not found: ('%s',%s);" % (k[0],k[1]))
            pass

#empty function, required to rollback migration
def do0(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('tantalus', '0108_auto_20190213_2218'),
    ]

    operations = [
        migrations.RunPython(sample_fixup, do0),
        migrations.RunPython(sequence_dataset_fixup, do0),
    ]

