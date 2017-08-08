"""
Loading new data into Tantalus from Colossus REST API

See Colossus REST API documentation here:
https://www.bcgsc.ca/wiki/display/MO/Colossus+Documentation
"""


import requests
from tantalus.models import *
import re
import json

HOSTNAME='http://127.0.0.1:8000/apps/api/'
JSON_FORMAT='?format=json'
DEFAULT_LIBRARY_TYPE='SC WGS'
INDEX_FORMAT='D' #Data coming from colossus should all be dual indexed


def parse_sample_id(s, colossus_sample_id):
    """
    Parses the sample ID from Colossus database into a sample ID namespace and sample ID number.
    Eg. SA928 in the colossus database gets turned into "SA", and "928".
    """

    for namespace in s.sample_id_space_choices:
        match = re.search('(?P<namespace>[a-zA-Z]+)(?P<id>.+$)', colossus_sample_id)
        test_namespace = match.group(1)
        test_id = match.group(2)

        # giving back the acronym, and not the verbose form of the sample id space
        # eg. namespace is ('SA', 'Aparicio), namespace[0] will have the value of 'SA'
        if test_namespace == namespace[0]:
            return namespace[0], test_id

    return None, None


def get_json(resource_name):
    r = requests.get('{hostname}{resource}{format}'.format(
        hostname=HOSTNAME, resource=resource_name, format=JSON_FORMAT)
    )
    # r.raise_for_status() #check if request is successful?
    if r.status_code != 200:
        raise Exception('Returned {}: {}'.format(r.status_code, r.reason))

    try:
        r = r.json()
        if len(r) == 0:
            raise Exception('No entries for {}'.format(resource_name))
    except ValueError: #invalid json returned
        raise Exception('Unable to parse response into JSON')
    finally:
        return r


def get_json_with_filter(resource_name, filter_string):
    r = requests.get('{hostname}{resource}{format}&{filter_string}'.format(
        hostname=HOSTNAME, resource=resource_name, format=JSON_FORMAT, filter_string=filter_string)
    )

    if r.status_code != 200:
        raise Exception('Returned {}: {}'.format(r.status_code, r.reason))

    try:
        r = r.json()
        if len(r) == 0:
            raise Exception('No entries for {}'.format(resource_name))

    except ValueError: #invalid json returned
        raise Exception('Unable to parse response into JSON')

    finally:
        return r


def get_difference(tantalus, colossus):
    """
    get difference between lists of items in both databases

    NOTE: This must be a list of UNIQUE IDs that is found in BOTH databases
    eg. for Samples, sample_id is a unique identifier
    """

    tantalus = set(tantalus)
    colossus = set(colossus)
    to_add = colossus - tantalus
    to_delete = tantalus - colossus
    return to_add, to_delete


def add_new_samples(samples):
    """ takes in a list of sample id strings and creates new sample objects in tantalus"""

    for sample in samples:
        print "ADDING this sample: {}".format(sample)
        s = Sample()
        sample_namespace, sample_id_number = parse_sample_id(s, sample)
        if (sample_namespace != None):
            s.sample_id_space = sample_namespace
            s.sample_id = sample_id_number
            s.save()


def delete_samples(samples):
    # TODO: when implemented, delete all related too ?
    for sample in samples:
        print "DELETING this sample: {}".format(sample)


def add_new_libraries(libs):
    for lib in libs:
        l = DNALibrary(
            library_id = lib,
            library_type=DEFAULT_LIBRARY_TYPE
        )
        l.save()
        print "ADDING this library: {}".format(lib)
        update_tantalus_dnasequences(lib)


def delete_libraries(libs):
    # TODO: when implemented, delete all related to ?
    for lib in libs:
        print "DELETING this library: {}".format(lib)


def add_new_sequencelanes(seqs, seq_lib_map):
    for seq in seqs:

        ## no flow cell or lane for this seq - don't add this
        if seq == "":
            print "no flowcell or lane"

        else:
            sequencelane = SequenceLane()
            flowcell_id_and_lane = seq.split('_')
            sequencelane.flowcell_id = flowcell_id_and_lane[0]

            # has flow cell id and no lane
            if (len(flowcell_id_and_lane) == 1):
                # TODO: add default and save model - set lane to null and blank in models
                print "hi no lane here"

            # has both flow cell id and lane
            elif len(flowcell_id_and_lane) == 2:
                sequencelane.lane_number = flowcell_id_and_lane[1]
                sequencelane.dna_library = DNALibrary.objects.get(library_id=seq_lib_map[seq])
                sequencelane.save()



def delete_sequencelanes(seqs, seq_lib_map):
    pass


def add_new_sublibs(sublibs, library):
    for sublib in sublibs:
        # the foreign key name is sample_id, and the name of the field inside sample is also sample_id, which is why this key is accessed twice
        sample_id_space, sample_id = parse_sample_id(Sample(), sublib['sample_id']['sample_id'])
        sample = Sample.objects.get(sample_id_space = sample_id_space, sample_id = sample_id)

        s = DNASequences(
            sample = sample,
            index_format = INDEX_FORMAT,
            dna_library = DNALibrary.objects.get(library_id=library)
        )

        if (s.index_format == 'D'):
            s.index_sequence = "{i5}-{i7}".format(
                i5 = sublib['primer_i5'],
                i7 = sublib['primer_i7'],
            )
            s.save()

        else:
            raise Exception('One or more sublibraries for library {} are not dual indexed, '
                            'colossus data should be dual indexed. Contact database admin.'.format(library))


def update_tantalus_samples():

    tantalus_samples = Sample.objects.values_list('sample_id_space', 'sample_id')
    ## parsing sample namespace and ID together into one
    tantalus_samples = [(s[0]+s[1]) for s in tantalus_samples]
    json_colossus_samples = get_json('sample')
    colossus_samples = [j['sample_id'] for j in json_colossus_samples]

    samples_to_add, samples_to_delete = get_difference(tantalus_samples, colossus_samples)
    add_new_samples(samples_to_add)
    delete_samples(samples_to_delete)

def update_tantalus_DNAlibrary():
    tantalus_libs = DNALibrary.objects.values_list('library_id', flat=True)
    json_colossus_libs = get_json('library')
    colossus_libs = [j['pool_id'] for j in json_colossus_libs]

    libraries_to_add, libraries_to_delete = get_difference(tantalus_libs, colossus_libs)
    add_new_libraries(libraries_to_add)
    delete_libraries(libraries_to_delete)


def update_tantalus_sequencelane():

    ## parsing sequence flowcell and lane number together so that it is queryable in the colossus database
    tantalus_sequencelanes = SequenceLane.objects.values_list('flowcell_id', 'lane_number')
    tantalus_sequencelanes = [(seq[0] + seq[1]) for seq in tantalus_sequencelanes]

    json_colossus_sequencelanes = get_json('sequencing')
    colossus_sequencelanes = [j['sequencingdetail']['flow_cell_id'] for j in json_colossus_sequencelanes]

    # creating a map of flowcell ids to library id
    sequence_library_map = {j['sequencingdetail']['flow_cell_id']: j['library']
                            for j in json_colossus_sequencelanes}

    sequences_to_add, sequences_to_delete = get_difference(tantalus_sequencelanes, colossus_sequencelanes)
    add_new_sequencelanes(sequences_to_add, sequence_library_map)
    delete_sequencelanes(sequences_to_delete, sequence_library_map)

def update_tantalus_dnasequences(library):
    # called in add_new_libraries, is passed a library pool id

    ## TODO: how to check if sublibrary information has changed if library hasnt - Exceptional case?
    ## TODO: ASSUME THAT ALL SUBLIBRARY INFORMATION IS NEW BECAUSE THE LIBRARY IS NEW
    filter_string = "pool_id={}".format(library)
    json_library = get_json_with_filter('library', filter_string)

    # there should only be one library for this filter
    if len(json_library)==1:
        sublibrary_set = json_library[0]['sublibraryinformation_set']
        add_new_sublibs(sublibrary_set, library)
    else:
        raise Exception('This library identifier is not unique.. Returned more than one library. Please ensure uniqueness of library ID')


def update_tantalus():
    update_tantalus_samples()
    update_tantalus_DNAlibrary()  #calls update_tantalus_dnasequences inside as well
    update_tantalus_sequencelane()















