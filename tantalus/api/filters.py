"""Contains filters for API viewsets."""

from django.db import models
from django_filters import rest_framework as filters
from tantalus.models import (
    Analysis,
    DNALibrary,
    FileInstance,
    FileResource,
    Patient,
    ResultsDataset,
    Sample,
    SequenceDataset,
    SequenceFileInfo,
    SequencingLane,
    ServerStorage,
    Storage,
    Tag,
    Curation,
    CurationDataset
)


class BaseFilterSet(filters.FilterSet):
    """Base filterset class.

    Specify some common attributes for all filters.
    """

    class Meta:
        """Override browsable filter boxes

        Remember to inherit the Meta class in children as in the
        following:

            >>> class Meta(BaseFilterSet.Meta):
            ...     # stuff here
        """

        # Make relational fields have a text input box in the browser,
        # else loading all related rows will take *ages*
        filter_overrides = {
            models.ForeignKey: {"filter_class": filters.CharFilter},
            models.ManyToManyField: {"filter_class": filters.CharFilter},
            models.OneToOneField: {"filter_class": filters.CharFilter},
        }


class AnalysisFilter(BaseFilterSet):
    """Filters for analyses."""

    class Meta(BaseFilterSet.Meta):
        model = Analysis
        fields = {
            "id": ["exact"],
            "name": ["exact"],
            "version": ["exact"],
            "jira_ticket": ["exact"],
            "analysis_type__name": ["exact"],
            "version": ["exact"],
            "input_datasets__id": ["exact"],
            "input_results__id": ["exact"],
            "input_datasets__library__library_id": ["exact"],
            "input_results__libraries__library_id": ["exact"],
            "input_datasets__sample__sample_id": ["exact"],
            "input_results__samples__sample_id": ["exact"],
            "status": ["exact"],
            "last_updated": ["lte", "gte"],
        }


class DNALibraryFilter(BaseFilterSet):
    """Filters for DNA libraries."""

    class Meta(BaseFilterSet.Meta):
        model = DNALibrary
        fields = {"id": ["exact"], "library_id": ["exact", "startswith"]}


class FileInstanceFilter(BaseFilterSet):
    """Filters for file instances."""

    def __init__(self, *args, **kwargs):
        super(FileInstanceFilter, self).__init__(*args, **kwargs)
        """Take care of filter names that render poorly."""
        self.filters["file_resource__sequencedataset__id"].label = "Sequence Dataset ID"
        self.filters["file_resource__sequencedataset__name"].label = "Sequence Dataset name"
        self.filters["file_resource__resultsdataset__id"].label = "Results Dataset ID "
        self.filters["file_resource__resultsdataset__name"].label = "Results Dataset name"

    class Meta(BaseFilterSet.Meta):
        model = FileInstance
        fields = {
            "id": ["exact"],
            "storage__name": ["exact"],
            "file_resource": ["exact", "in"],
            "file_resource__filename": ["exact"],
            "file_resource__sequencedataset__id": ["exact"],
            "file_resource__sequencedataset__name": ["exact"],
            "file_resource__resultsdataset__id": ["exact"],
            "file_resource__resultsdataset__name": ["exact"],
            "owner": ["exact"],
            "storage": ["exact"],
            "is_deleted": ["exact"],
        }


class FileResourceFilter(BaseFilterSet):
    """Filters for file resources."""

    def __init__(self, *args, **kwargs):
        """Take care of filter names that render poorly."""
        super(FileResourceFilter, self).__init__(*args, **kwargs)
        self.filters["sequencedataset__id"].label = "Sequence Dataset ID"
        self.filters["sequencedataset__name"].label = "Sequence Dataset name"
        self.filters["resultsdataset__id"].label = "Results Dataset ID"
        self.filters["resultsdataset__name"].label = "Results Dataset name"
        self.filters["sequencefileinfo__index_sequence"].label = "Index Sequence"
        self.filters["fileinstance__storage__name"].label = "Storage Name"

    class Meta(BaseFilterSet.Meta):
        model = FileResource
        fields = {
            "id": ["exact"],
            "filename": ["exact", "endswith", "startswith"],
            "sequencedataset__name": ["exact"],
            "sequencedataset__id": ["exact"],
            "resultsdataset__name": ["exact"],
            "resultsdataset__id": ["exact"],
            "sequencefileinfo__index_sequence": ["exact"],
            "fileinstance__storage__name": ["exact"],
        }


class ResultsDatasetFilter(filters.FilterSet):
    """Filters for results datasets."""

    def __init__(self, *args, **kwargs):
        """Take care of filter names that render poorly."""
        super(ResultsDatasetFilter, self).__init__(*args, **kwargs)
        self.filters["file_resources__fileinstance__storage__name"].label = "File resources instance storage"

    class Meta(BaseFilterSet.Meta):
        model = ResultsDataset
        fields = {
            "id": ["exact"],
            "owner": ["exact"],
            "name": ["exact"],
            "analysis": ["exact"],
            "analysis__jira_ticket": ["exact"],
            "analysis__version": ["exact"],
            "file_resources__filename": ["exact"],
            "file_resources__id": ["exact"],
            "results_type": ["exact"],
            "results_version": ["exact"],
            "tags__name": ["exact"],
            "libraries__library_id": ["exact"],
            "samples__sample_id": ["exact"],
            "file_resources__fileinstance__storage__name": ["exact"],
        }

class PatientFilter(filters.FilterSet):

    class Meta(BaseFilterSet.Meta):
        model = Patient
        fields = {
            "id": ["exact"],
            "patient_id": ["exact"],
            "external_patient_id": ["exact"],
            "case_id": ["exact"],
        }

class SampleFilter(BaseFilterSet):
    """Filters for samples."""

    def __init__(self, *args, **kwargs):
        """Take care of filter names that render poorly."""
        super(SampleFilter, self).__init__(*args, **kwargs)
        self.filters["sequencedataset__id"].label = "Has SequenceDataset"
        self.filters["sequencedataset__id__in"].label = "Has SequenceDataset in"
        self.filters["sequencedataset__id__isnull"].label = "Has no SequenceDatasets"

    class Meta(BaseFilterSet.Meta):
        model = Sample
        fields = {
            "id": ["exact", "in"],
            "sample_id": ["exact", "in"],
            "sequencedataset__id": ["exact", "in", "isnull"],
            "is_reference": ["exact"],
        }


class SequenceDatasetFilter(filters.FilterSet):
    """Filters for sequence datasets."""

    def __init__(self, *args, **kwargs):
        """Take care of filter names that render poorly."""
        super(SequenceDatasetFilter, self).__init__(*args, **kwargs)
        self.filters["file_resources__fileinstance__storage__name"].label = "File resources instance storage"

    class Meta(BaseFilterSet.Meta):
        model = SequenceDataset
        fields = {
            "id": ["exact"],
            "name": ["exact"],
            "version_number": ["exact"],
            "is_production": ["exact"],
            "library__library_id": ["exact"],
            "library__library_type__name": ["exact"],
            "sample__sample_id": ["exact", "contains"],
            "tags__name": ["exact"],
            "sequence_lanes__flowcell_id": ["exact"],
            "sequence_lanes__lane_number": ["exact"],
            "dataset_type": ["exact"],
            "aligner__name": ["exact", "startswith"],
            "reference_genome__name": ["exact"],
            "analysis": ["exact"],
            "analysis__name": ["exact"],
            "analysis__jira_ticket": ["exact"],
            "file_resources__filename": ["exact"],
            "file_resources__id": ["exact"],
            "file_resources__fileinstance__storage__name": ["exact"],
        }

class CurationFilter(filters.FilterSet):
    """Filters for curations."""

    class Meta(BaseFilterSet.Meta):
        model = Curation
        fields = {
            "id": ["exact"],
            "name": ["exact"],
            "owner": ["exact"]
        }

class CurationDatasetFilter(filters.FilterSet):
    """Filters for curations."""

    class Meta(BaseFilterSet.Meta):
        model = CurationDataset
        fields = {
            "id": ["exact"],
            "curation_instance": ["exact"],
            "sequencedataset_instance": ["exact"],
            "version": ["exact"],
        }

class SequenceFileInfoFilter(BaseFilterSet):
    """Filters for sequence file infos."""

    class Meta(BaseFilterSet.Meta):
        model = SequenceFileInfo
        fields = {
            "id": ["exact"],
            "file_resource": ["exact"],
            "index_sequence": ["exact"],
        }


class SequencingLaneFilter(BaseFilterSet):
    """Filters for sequencing lanes."""

    class Meta(BaseFilterSet.Meta):
        model = SequencingLane
        fields = {
            "id": ["exact"],
            "dna_library__library_id": ["exact"],
            "flowcell_id": ["exact"],
            "lane_number": ["exact"],
            "sequencing_library_id": ["exact"],
            "read_type": ["exact"],
            "dna_library": ["exact"],
            "sequencing_centre": ["exact"],
        }


class ServerStorageFilter(BaseFilterSet):
    """Filters for server storages."""

    class Meta(BaseFilterSet.Meta):
        model = ServerStorage
        fields = {"id": ["exact"], "name": ["exact"]}


class StorageFilter(BaseFilterSet):
    """Filters for storages."""

    class Meta(BaseFilterSet.Meta):
        model = Storage
        fields = {"id": ["exact"], "name": ["exact"]}


class TagFilter(BaseFilterSet):
    """Filters for tags."""

    class Meta(BaseFilterSet.Meta):
        model = Tag
        fields = {"name": ["exact"]}
