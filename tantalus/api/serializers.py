from django.db import transaction
from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned, ValidationError
from rest_framework import serializers

import tantalus.models


class SampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = tantalus.models.Sample
        fields = '__all__'

class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = tantalus.models.Patient
        fields = '__all__'

class StorageSerializer(serializers.ModelSerializer):
    class Meta:
        model = tantalus.models.Storage
        exclude = ['polymorphic_ctype']

    def to_representation(self, obj):
        if isinstance(obj, tantalus.models.ServerStorage):
            return ServerStorageSerializer(obj, context=self.context).to_representation(obj)
        elif isinstance(obj, tantalus.models.AzureBlobStorage):
            return AzureBlobStorageSerializer(obj, context=self.context).to_representation(obj)
        elif isinstance(obj, tantalus.models.AwsS3Storage):
            return AwsS3StorageSerializer(obj, context=self.context).to_representation(obj)
        return super(StorageSerializer, self).to_representation(obj)


class ServerStorageSerializer(serializers.ModelSerializer):
    prefix = serializers.SerializerMethodField()
    storage_type = serializers.CharField(read_only=True)

    def get_prefix(self, obj):
        return obj.get_prefix()

    class Meta:
        model = tantalus.models.ServerStorage
        fields = (
            'id',
            'storage_type',
            'name',
            'storage_directory',
            'prefix',
            'server_ip',
        )


class AzureBlobStorageSerializer(serializers.ModelSerializer):
    prefix = serializers.SerializerMethodField()
    storage_type = serializers.CharField(read_only=True)

    def get_prefix(self, obj):
        return obj.get_prefix()

    class Meta:
        model = tantalus.models.AzureBlobStorage
        fields = (
            'id',
            'storage_type',
            'name',
            'storage_account',
            'storage_container',
            'prefix',
        )


class AwsS3StorageSerializer(serializers.ModelSerializer):
    prefix = serializers.SerializerMethodField()
    storage_type = serializers.CharField(read_only=True)

    def get_prefix(self, obj):
        return obj.get_prefix()

    class Meta:
        model = tantalus.models.AwsS3Storage
        fields = (
            'id',
            'storage_type',
            'name',
            'bucket',
            'prefix',
        )


class FileInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = tantalus.models.FileInstance
        fields = '__all__'


class SequenceFileInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = tantalus.models.SequenceFileInfo
        fields = '__all__'


class FileResourceSerializer(serializers.ModelSerializer):
    sequencefileinfo = SequenceFileInfoSerializer(read_only=True)
    class Meta:
        model = tantalus.models.FileResource
        fields = '__all__'


class FileResourceSerializerRead(serializers.ModelSerializer):
    sequencefileinfo = SequenceFileInfoSerializer(read_only=True)
    class Meta:
        model = tantalus.models.FileResource
        fields = '__all__'

class FileInstanceSerializerRead(serializers.ModelSerializer):
    filepath = serializers.SerializerMethodField()
    storage = StorageSerializer(read_only=True)
    file_resource = FileResourceSerializer(read_only=True)

    def get_filepath(self, obj):
        return obj.get_filepath()

    class Meta:
        model = tantalus.models.FileInstance
        fields = '__all__'

class FileResourceInstancesSerilizer(serializers.ModelSerializer):
    fileinstance_set = FileInstanceSerializerRead(read_only=True, many=True)
    class Meta:
        model = tantalus.models.SequenceFileInfo
        fields = (
            'id',
            'fileinstance_set'
        )

class LibraryTypeField(serializers.Field):
    def to_representation(self, obj):
        return obj.name
    def to_internal_value(self, data):
        try:
            return tantalus.models.LibraryType.objects.get(name=data)
        except ObjectDoesNotExist:
            raise ValidationError('{} does not exist'.format(data))


class DNALibrarySerializer(serializers.ModelSerializer):
    library_type = LibraryTypeField()
    class Meta:
        model = tantalus.models.DNALibrary
        fields = '__all__'


class SequencingLaneSerializer(serializers.ModelSerializer):
    class Meta:
        model = tantalus.models.SequencingLane
        fields = '__all__'


class AlignmentToolField(serializers.Field):
    def to_representation(self, obj):
        return obj.name
    def to_internal_value(self, data):
        try:
            return tantalus.models.AlignmentTool.objects.get(name=data)
        except ObjectDoesNotExist:
            raise ValidationError('{} does not exist'.format(data))


class ReferenceGenomeField(serializers.Field):
    def to_representation(self, obj):
        return obj.name
    def to_internal_value(self, data):
        try:
            return tantalus.models.ReferenceGenome.objects.get(name=data)
        except ObjectDoesNotExist:
            raise ValidationError('{} does not exist'.format(data))


class SequenceDatasetSerializer(serializers.ModelSerializer):
    aligner = AlignmentToolField(required=False, allow_null=True)
    reference_genome = ReferenceGenomeField(required=False, allow_null=True)
    class Meta:
        model = tantalus.models.SequenceDataset
        fields = '__all__'


class SequenceDatasetSerializerRead(serializers.ModelSerializer):
    sample = SampleSerializer()
    library = DNALibrarySerializer()
    sequence_lanes = SequencingLaneSerializer(many=True)
    aligner = AlignmentToolField()
    reference_genome = ReferenceGenomeField()
    is_complete = serializers.SerializerMethodField()

    def get_is_complete(self, obj):
        return obj.get_is_complete()

    class Meta:
        model = tantalus.models.SequenceDataset
        fields = '__all__'


class TagSerializer(serializers.ModelSerializer):
    """ Serializer for tags.
    Note that this serializer will always update by
    adding the tag to the given datasets.
    """
    sequencedataset_set = serializers.PrimaryKeyRelatedField(
        many=True,
        allow_null=True,
        required=False,
        queryset=tantalus.models.SequenceDataset.objects.all(),)

    resultsdataset_set = serializers.PrimaryKeyRelatedField(
        many=True,
        allow_null=True,
        required=False,
        queryset=tantalus.models.ResultsDataset.objects.all(),)

    class Meta:
        model = tantalus.models.Tag
        fields = ('id', 'name', 'owner', 'sequencedataset_set', 'resultsdataset_set')

    def is_valid(self, raise_exception=False):
        if hasattr(self, 'initial_data'):
            try:
                obj = tantalus.models.Tag.objects.get(name=self.initial_data['name'])
            except (ObjectDoesNotExist, MultipleObjectsReturned):
                return super(TagSerializer, self).is_valid(raise_exception)
            else:
                self.instance = obj
                return super(TagSerializer, self).is_valid(raise_exception)
        else:
            return super(TagSerializer, self).is_valid(raise_exception)

    def update(self, instance, validated_data):
        if 'owner' in validated_data:
            instance.owner = validated_data['owner']
            instance.save()
        for sequencedataset in validated_data.get('sequencedataset_set', ()):
            sequencedataset.tags.add(instance)
        for resultsdataset in validated_data.get('resultsdataset_set', ()):
            resultsdataset.tags.add(instance)
        return instance


class ResultsDatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = tantalus.models.ResultsDataset
        fields = '__all__'


class ResultsDatasetSerializerRead(serializers.ModelSerializer):
    samples = SampleSerializer(many=True)
    libraries = DNALibrarySerializer(many=True)

    class Meta:
        model = tantalus.models.ResultsDataset
        fields = '__all__'


class AnalysisTypeField(serializers.Field):
    def to_representation(self, obj):
        return obj.name
    def to_internal_value(self, data):
        try:
            return tantalus.models.AnalysisType.objects.get(name=data)
        except ObjectDoesNotExist:
            raise ValidationError('{} does not exist'.format(data))


class AnalysisSerializer(serializers.ModelSerializer):
    analysis_type = AnalysisTypeField()
    class Meta:
        model = tantalus.models.Analysis
        fields = '__all__'


class CurationSerializer(serializers.ModelSerializer):
    #sequencedatasets = SequenceDatasetSerializer()
    class Meta:
        model = tantalus.models.Curation
        fields = '__all__'

class CurationDatasetSerializer(serializers.ModelSerializer):
    #sequencedatasets = SequenceDatasetSerializer()
    class Meta:
        model = tantalus.models.CurationDataset
        fields = '__all__'
