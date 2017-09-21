import os
import sys
import string
import pandas as pd
import django


sys.path.append('./')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tantalus.settings')
django.setup()

import tantalus.models

tantalus.models.ServerStorage.objects.all().delete()
tantalus.models.AzureBlobStorage.objects.all().delete()
tantalus.models.FileResource.objects.all().delete()
tantalus.models.FileInstance.objects.all().delete()
tantalus.models.PairedEndFastqFiles.objects.all().delete()

def reverse_complement(sequence):
    return sequence[::-1].translate(string.maketrans('ACTGactg','TGACtgac'))

data = pd.HDFStore('loaders/single_cell_hiseq_fastq_metadata.h5', 'r')['/metadata']
data = data[data['id'] == 'PX0593']

storage = tantalus.models.ServerStorage()
storage.name = 'rocks'
storage.server_ip = 'rocks3.cluster.bccrc.ca'
storage.storage_directory = '/share/lustre/archive'
storage.username = 'jngo'
storage.full_clean()
storage.save()

blob_storage = tantalus.models.AzureBlobStorage()
blob_storage.name = 'azure_sc_fastqs'
blob_storage.storage_account = 'singlecellstorage'
blob_storage.storage_container = 'fastqs'
blob_storage.storage_key = 'okQAsp72BagVWpGLEaUNO30jH9XGLuVj3EDmbtg7oV6nmH7+9E+4csF+AXn4G3YMEKebnCnsRwVu9fRhh2RiMQ=='
blob_storage.full_clean()
blob_storage.save()

for idx in data.index:
    fastq_dna_sequences = tantalus.models.DNASequences.objects.filter(index_sequence=reverse_complement(data.loc[idx, 'code1']) + '-' + data.loc[idx, 'code2'])
    assert len(fastq_dna_sequences) == 1

    fastq_files = tantalus.models.PairedEndFastqFiles()
    fastq_files.dna_sequences = fastq_dna_sequences[0]
    fastq_files.save()
    fastq_files.lanes = tantalus.models.SequenceLane.objects.filter(flowcell_id=data.loc[idx, 'flowcell'], lane_number=data.loc[idx, 'lane'])
    fastq_files.full_clean()
    fastq_files.save()

    for read_end in ('1', '2'):
        fastq_filename = data.loc[idx, 'read' + read_end]

        seqfile = tantalus.models.FileResource()
        seqfile.file_set = fastq_files
        seqfile.md5 = data.loc[idx, 'md5' + read_end]
        seqfile.size = data.loc[idx, 'size' + read_end]
        seqfile.created = pd.Timestamp(data.loc[idx, 'create' + read_end], tz='Canada/Pacific')
        seqfile.file_type = tantalus.models.FileResource.FQ
        seqfile.read_end = int(read_end)
        seqfile.compression = tantalus.models.FileResource.GZIP
        seqfile.filename =fastq_filename
        seqfile.save()

        serverfile = tantalus.models.FileInstance()
        serverfile.storage = storage
        serverfile.file_resource = seqfile
        serverfile.full_clean()
        serverfile.save()


