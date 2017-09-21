from rest_framework import viewsets
import django_filters
import tantalus.models
import tantalus.api.serializers


class SampleViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.Sample.objects.all()
    serializer_class = tantalus.api.serializers.SampleSerializer
    filter_fields = ('sample_id',)


class FileResourceFilterSet(django_filters.FilterSet):
    library_id = django_filters.CharFilter(name='file_set__dna_sequences__dna_library__library_id')
    class Meta:
        model = tantalus.models.FileResource
        fields = ['md5', 'library_id']


class FileResourceViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.FileResource.objects.all()
    serializer_class = tantalus.api.serializers.FileResourceSerializer
    filter_fields = ('md5',)
    filter_class = FileResourceFilterSet


class DNALibraryViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.DNALibrary.objects.all()
    serializer_class = tantalus.api.serializers.DNALibrarySerializer
    filter_fields = ('library_id',)


class DNASequencesViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.DNASequences.objects.all()
    serializer_class = tantalus.api.serializers.DNASequencesSerializer
    filter_fields = ('dna_library__library_id', 'dna_library', 'index_sequence')


class SequenceLaneViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.SequenceLane.objects.all()
    serializer_class = tantalus.api.serializers.SequenceLaneSerializer
    filter_fields = ('flowcell_id', 'lane_number',)


class AbstractFileSetViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.AbstractFileSet.objects.all()
    serializer_class = tantalus.api.serializers.AbstractFileSetSerializer
    filter_fields = (
                     # filters for SequenceLanes
                     'lanes',
                     'lanes__flowcell_id', 'lanes__lane_number',
                     # filters for DNASequences
                     'dna_sequences',
                     'dna_sequences__dna_library__library_id', 'dna_sequences__dna_library', 'dna_sequences__index_sequence'
                     )


class SingleEndFastqFileViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.SingleEndFastqFile.objects.all()
    serializer_class = tantalus.api.serializers.SingleEndFastqFileSerializer


class PairedEndFastqFilesFilterSet(django_filters.FilterSet):
    library_id = django_filters.CharFilter(name='dna_sequences__dna_library__library_id')
    class Meta:
        model = tantalus.models.PairedEndFastqFiles
        fields = ['library_id']


class PairedEndFastqFilesViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.PairedEndFastqFiles.objects.all()
    serializer_class = tantalus.api.serializers.PairedEndFastqFilesSerializer
    filter_class = PairedEndFastqFilesFilterSet


class BamFileViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.BamFile.objects.all()
    serializer_class = tantalus.api.serializers.BamFileSerializer


class StorageViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.Storage.objects.all()
    serializer_class = tantalus.api.serializers.StorageSerializer


class ServerStorageViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.ServerStorage.objects.all()
    serializer_class = tantalus.api.serializers.ServerStorageSerializer


class AzureBlobStorageViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.AzureBlobStorage.objects.all()
    serializer_class = tantalus.api.serializers.AzureBlobStorageSerializer


class FileInstanceViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.FileInstance.objects.all()
    serializer_class = tantalus.api.serializers.FileInstanceSerializer
    filter_fields = ('file_resource__md5', 'file_resource',
                     'storage__name',)


class DeploymentViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.Deployment.objects.all()
    serializer_class = tantalus.api.serializers.DeploymentSerializer


class FileTransferViewSet(viewsets.ModelViewSet):
    queryset = tantalus.models.FileTransfer.objects.all()
    serializer_class = tantalus.api.serializers.FileTransferSerializer


