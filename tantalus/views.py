import operator

from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic.list import ListView
from django.views.generic import DetailView, FormView
from django.views.generic.base import TemplateView
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, render
from django_datatables_view.base_datatable_view import BaseDatatableView
from django.db.models import Q, F, Count
from django.db.models.functions import Lower
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.template.defaulttags import register
from django.forms import ModelForm
from django.forms.models import model_to_dict
from django.shortcuts import redirect
from django.contrib.sites.shortcuts import get_current_site
from django.views.generic.edit import UpdateView
from functools import reduce
import account.models

import csv
import json
import os
from datetime import date
import pandas as pd
from io import StringIO
import xlsxwriter
import requests

from jira import JIRA, JIRAError

from search_util.search_helper import return_text_search
from tantalus.utils import read_excel_sheets
from tantalus.settings import STATIC_ROOT, JIRA_URL, LOGIN_URL
from misc.helpers import Render
import tantalus.models
import tantalus.forms
from tantalus.services import *
#============================
# Search view
#----------------------------
class SearchView(TemplateView):
    login_url = LOGIN_URL
    template_name = "tantalus/search/search_main.html"


    def get_context_data(self):

        query_str = self.request.GET.get('query_str')

        if len(query_str) < 1:
            return {"total" : 0}

        return return_text_search(query_str)


class ExternalIDSearch(LoginRequiredMixin, TemplateView):
    login_url = LOGIN_URL

    search_template_name = "tantalus/external_id_search.html"
    result_template_name = "tantalus/external_id_results.html"

    def get_context_and_render(self, request, form):
        context = {
            'form': form,
        }
        return render(request, self.search_template_name, context)

    def render_results(self, request, sample_list, wrong_sample_list, multiple_sample_list):
        context = {
            'samples': sample_list,
            'multiple_samples': multiple_sample_list,
            'wrong_ids': wrong_sample_list,
        }
        return render(request, self.result_template_name, context)

    def get(self, request):
        form = tantalus.forms.ExternalIDSearcherForm()
        return self.get_context_and_render(request, form)

    def post(self, request):
        form = tantalus.forms.ExternalIDSearcherForm(request.POST)
        if form.is_valid():
            sample_list = []
            multiple_sample_list = []
            wrong_sample_list = []
            passable_sample_list = []
            external_id_list = set(form.cleaned_data['external_id_column'].encode('ascii','ignore').splitlines())

            for external_id in external_id_list:
                if(tantalus.models.Sample.objects.filter(external_sample_id=external_id).count() == 1):
                    sample_list.append(list(tantalus.models.Sample.objects.filter(external_sample_id=external_id))[0])
                elif(tantalus.models.Sample.objects.filter(external_sample_id=external_id).count() > 1):
                    for sample in tantalus.models.Sample.objects.filter(external_sample_id=external_id):
                        multiple_sample_list.append(sample)
                else:
                    wrong_sample_list.append(external_id)

            for sample in sample_list:
                passable_sample_list.append({'id': sample.id, 'sample_id': sample.sample_id, 'external_sample_id': sample.external_sample_id})

            request.session['sample_list'] = passable_sample_list
            return self.render_results(request, sample_list, wrong_sample_list, multiple_sample_list)
        else:
            msg = "Failed to create search query. Please fix the errors below."
            messages.error(request, msg)
            return self.get_context_and_render(request, form)


@login_required
def export_external_id_results(request):
    header_dict = {
        'ID': [],
        'Sample ID': [],
        'External Sample ID': [],
    }

    for sample in request.session['sample_list']:
        header_dict['ID'].append(sample['id'])
        header_dict['Sample ID'].append(sample['sample_id'])
        header_dict['External Sample ID'].append(sample['external_sample_id'])

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="external-sample-id-matches.csv"'
    df = pd.DataFrame(header_dict)
    df.to_csv(response, index=False)
    return response


@login_required
@Render("tantalus/patient_list.html")
def patient_list(request):
    patients = tantalus.models.Patient.objects.all().order_by('patient_id')
    context = {
        'patients': patients
    }
    return context


class PatientDetail(LoginRequiredMixin, DetailView):
    login_url = LOGIN_URL

    model = tantalus.models.Patient
    template_name = "tantalus/patient_detail.html"

    def get_context_data(self, **kwargs):
        # TODO: add other fields to the view?
        context = super(PatientDetail, self).get_context_data(**kwargs)
        sample_set = self.object.sample_set.all()
        sample_list = []
        sample_url = []

        for sample in sample_set:
            projects_list = []
            submission_list = []
            projects = sample.projects.all()
            for project in projects:
                projects_list.append(project.__str__())
            for submission in sample.submission_set.all():
                submission_list.append(submission.id)
            sample.projects_list = projects_list
            sample.submission_list = submission_list
            sample_list.append([sample.sample_id, sample.get_absolute_url() + str(sample.id)])

        #self.object.patient_id = self.object.patient_id

        context['sample_list'] = sample_list
        context['samples'] = sample_set

        return context


@login_required
@Render("tantalus/submission_list.html")
def submission_list(request):
    submissions = tantalus.models.Submission.objects.all().order_by('id')
    context = {
        'submissions': submissions
    }
    return context


class SubmissionDetail(LoginRequiredMixin, DetailView):
    login_url = LOGIN_URL

    model = tantalus.models.Submission
    template_name = "tantalus/submission_detail.html"

    def get_context_data(self, **kwargs):
        # TODO: add other fields to the view?
        context = super(SubmissionDetail, self).get_context_data(**kwargs)
        sample_object = tantalus.models.Sample.objects.get(pk=self.object.sample_id)
        context['sample_url'] = sample_object.get_absolute_url()
        return context


@login_required
@Render("tantalus/sample_list.html")
def sample_list(request):
    """
    List of samples.
    """

    samples = tantalus.models.Sample.objects.all().order_by('sample_id')

    context = {
        'samples': samples,
    }
    return context


class SampleDetail(LoginRequiredMixin, DetailView):
    login_url = LOGIN_URL

    model = tantalus.models.Sample
    template_name = "tantalus/sample_detail.html"

    def get_context_data(self, **kwargs):
        # TODO: add other fields to the view?
        context = super(SampleDetail, self).get_context_data(**kwargs)

        sequence_datasets_set = self.object.sequencedataset_set.all()
        results_datasets_set = self.object.resultsdataset_set.all()

        submission_set = self.object.submission_set.all()
        project_set = self.object.projects.all()
        library_set = tantalus.models.DNALibrary.objects.filter(sequencedataset__sample=self.object).distinct()

        context['sequence_datasets_set'] = sequence_datasets_set
        context['results_datasets_set'] = results_datasets_set
        try:
            context['patient_url'] = self.object.patient.get_absolute_url()
        except:
            context['patient_url'] = None

        context['project_list'] = project_set
        context['sequence_datasets_set'] = sequence_datasets_set
        context['submission_set'] = submission_set
        context['library_set'] = library_set
        return context


@login_required
@Render("tantalus/result_list.html")
def result_list(request):

    context = {
    }
    return context


class ResultDetail(LoginRequiredMixin, DetailView):
    login_url = LOGIN_URL

    model = tantalus.models.ResultsDataset
    template_name = "tantalus/result_detail.html"

    def get_context_data(self, **kwargs):
        # TODO: add other fields to the view?
        context = super(ResultDetail, self).get_context_data(**kwargs)

        sample_set = self.object.samples.all()
        library_set = self.object.libraries.all()
        project_set = tantalus.models.Project.objects.filter(sample__in=sample_set).distinct()
        submission_set = tantalus.models.Submission.objects.filter(sample__in=sample_set).distinct()

        context['file_resources'] = self.object.file_resources.all()
        context['library_set'] = library_set
        context['samples'] = sample_set
        context['pk'] = self.object.id
        context['form'] = tantalus.forms.AddDatasetToTagForm()
        return context

    def post(self, request, *args, **kwargs):
        result_pk = kwargs['pk']
        result = tantalus.models.ResultsDataset.objects.get(id=result_pk)
        form = tantalus.forms.AddDatasetToTagForm(request.POST)
        if form.is_valid():
            tag = form.cleaned_data['tag']
            result.tags.add(tag)
            result.save()
            msg = "Successfully added Tag {} to this Result.".format(tag.name)
            messages.success(request, msg)
            return HttpResponseRedirect(result.get_absolute_url())
        else:
            msg = "Invalid Tag Name"
            messages.error(request, msg)
            return HttpResponseRedirect(result.get_absolute_url())


class TagResultsDelete(LoginRequiredMixin, View):
    login_url = LOGIN_URL

    def get(self, request, pk, pk_2):
        result = get_object_or_404(tantalus.models.ResultsDataset, pk=pk)
        tag = get_object_or_404(tantalus.models.Tag, pk=pk_2)
        tag.resultsdataset_set.remove(result)
        msg = "Successfully removed datasest "
        messages.success(request, msg)
        return HttpResponseRedirect(reverse('tag-detail',kwargs={'pk':pk_2}))


class AnalysisCreate(LoginRequiredMixin, TemplateView):
    login_url = LOGIN_URL

    template_name = "tantalus/analysis_create.html"

    def create_jira_ticket(self, username, password, name, description, reporter, assignee, project_name):

        jira_server = JIRA(JIRA_URL, auth=(username, password))

        projects = jira_server.projects()

        for project in projects:
            if(project.name.lower() == project_name.lower()):
                project_id = project.id


        title = "Analysis Ticket For of {}".format(name)

        issue_dict = {
            "project": {"id": project_id},
            "summary": title,
            "description": description,
            "issuetype": {"name": "Task"},
            "reporter": {"name": reporter},
            "assignee": {"name": assignee},
        }

        new_issue = jira_server.create_issue(fields=issue_dict)

        return new_issue

    def get_context_and_render(self, request, form):
        context = {
            'form': form,
        }
        if not 'dataset' in request.path:
            if 'analysis_dataset_ajax' in request.session:
                del request.session["analysis_dataset_ajax"]
        return render(request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        form = tantalus.forms.AnalysisForm()
        return self.get_context_and_render(request, form)

    def post(self, request, *args, **kwargs):
        form = tantalus.forms.AnalysisForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.owner = request.user
            jira_ticket = self.create_jira_ticket(form['jira_username'].value(), form['jira_password'].value(),
                                    instance.name, form['description'].value(), str(request.user), str(request.user), form['project_name'].value())
            instance.jira_ticket = jira_ticket
            instance.save()

            if 'analysis_dataset_ajax' in request.session:
                instance.input_datasets = request.session["analysis_dataset_ajax"]
            msg = "Successfully created Analysis {}.".format(instance.name)
            messages.success(request, msg)
            return HttpResponseRedirect(instance.get_absolute_url())
        else:
            msg = "Failed to create Analysis. Please fix the errors below."
            messages.error(request, msg)
            return self.get_context_and_render(request, form)


class AnalysisEdit(LoginRequiredMixin, TemplateView):
    login_url = LOGIN_URL

    template_name = "tantalus/analysis_edit.html"

    def get_context_and_render(self, request, form, pk=None):
        context = {
            'pk':pk,
            'form': form,
        }
        return render(request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        analysis_pk = kwargs['pk']
        analysis = tantalus.models.Analysis.objects.get(id=analysis_pk)
        form = tantalus.forms.AnalysisEditForm(instance=analysis)
        return self.get_context_and_render(request, form, analysis_pk)

    def post(self, request, *args, **kwargs):
        analysis_pk = kwargs['pk']
        analysis = tantalus.models.Analysis.objects.get(id=analysis_pk)
        form = tantalus.forms.AnalysisEditForm(request.POST, instance=analysis)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            msg = "Successfully edited Patient {}".format(instance.name)
            messages.success(request, msg)
            return HttpResponseRedirect(instance.get_absolute_url())
        else:
            msg = "Failed to edit the Analysis. Please fix the errors below."
            messages.error(request, msg)
            return self.get_context_and_render(request, form, analysis_pk)


@login_required
@Render("tantalus/analysis_list.html")
def analysis_list(request):
    context = {
    }
    return context


class AnalysisDetail(LoginRequiredMixin, DetailView):
    login_url = LOGIN_URL

    model = tantalus.models.Analysis
    template_name = "tantalus/analysis_detail.html"

    def get_context_data(self, **kwargs):
        # TODO: add other fields to the view?
        context = super(AnalysisDetail, self).get_context_data(**kwargs)
        context['input_datasets'] = self.object.input_datasets.all()
        context['input_results'] = self.object.input_results.all()
        context['output_datasets'] = self.object.sequencedataset_set.all()
        context['output_results'] = self.object.resultsdataset_set.all()
        return context


@login_required
def export_patient_create_template(request):
    header_dict = {
        'Case ID': [],
        'Reference ID': [],
        'External Patient ID': [],
        'SA ID': [],
    }
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="patient-header-template.csv"'
    df = pd.DataFrame(header_dict)
    df.to_csv(response, index=False)
    return response


class PatientCreate(LoginRequiredMixin, TemplateView):
    """
    tantalus.models.Patient create page.
    """
    login_url = LOGIN_URL

    template_name = "tantalus/patient_create.html"

    def get_context_and_render(self, request, form, multi_form, pk=None):
        context = {
            'pk':pk,
            'form': form,
            'multi_form': multi_form
        }
        return render(request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        SA_prefix_patients = tantalus.models.Patient.objects.filter(patient_id__startswith='SA').order_by('-patient_id')
        SA_ids = []
        for patient in SA_prefix_patients:
            SA_ids.append(int(patient.patient_id[2:]))
        SA_ids.sort()
        data = {'patient_id': 'SA' + str(SA_ids[-1] + 1)}
        form = tantalus.forms.PatientForm(initial=data)
        multi_form = tantalus.forms.UploadPatientForm()
        return self.get_context_and_render(request, form, multi_form)

    def post(self, request, *args, **kwargs):
        form = tantalus.forms.PatientForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            msg = "Successfully created Patient {}.".format(instance.patient_id)
            messages.success(request, msg)
            return HttpResponseRedirect(instance.get_absolute_url())

        multi_form = tantalus.forms.UploadPatientForm(request.POST, request.FILES)
        if multi_form.is_valid():
            patients_df, auto_generated_SA_ids = multi_form.get_patient_data()

            form_headers = patients_df.columns.tolist()

            external_patient_id_index = form_headers.index('External Patient ID')
            reference_id_index = form_headers.index('Reference ID')
            SA_id_index = form_headers.index('SA ID')
            case_id_index = form_headers.index('Case ID')

            to_edit = []
            auto_generated_patients = []
            for idx, patient_row in patients_df.iterrows():
                if(patient_row[SA_id_index] in auto_generated_SA_ids):
                    patient = tantalus.models.Patient(
                        patient_id=patient_row[SA_id_index],
                        external_patient_id=patient_row[external_patient_id_index],
                        case_id=patient_row[case_id_index],
                        reference_id=patient_row[reference_id_index]
                    )
                    auto_generated_patients.append(model_to_dict(patient))
                    continue
                patient, created = tantalus.models.Patient.objects.get_or_create(patient_id=patient_row[SA_id_index])
                if(created):
                    patient.external_patient_id = patient_row[external_patient_id_index]
                    patient.case_id = patient_row[case_id_index]
                    patient.reference_id = patient_row[reference_id_index]
                    patient.save()
                else:
                    patient.external_patient_id = patient_row[external_patient_id_index]
                    patient.case_id = patient_row[case_id_index]
                    patient.reference_id = patient_row[reference_id_index]
                    to_edit.append(model_to_dict(patient))
            if(len(to_edit) == 0 and len(auto_generated_patients) == 0):
                msg = "Successfully created all Patients."
                messages.success(request, msg)
                return HttpResponseRedirect(reverse('patient-list'))
            else:
                msg = "You are editing existing Patient Data or have asked us to auto-generate SA IDs. Please Confirm Modifications and ID Generation."
                messages.warning(request, msg)
                request.session['to_edit'] = to_edit
                request.session['auto_generated_patients'] = auto_generated_patients
                return HttpResponseRedirect(reverse('confirm-patient-edit-from-create'))
        else:
            msg = "Failed to create the Patient. Please fix the errors below."
            messages.error(request, msg)
            return self.get_context_and_render(request, form, multi_form)


class ConfirmPatientEditFromCreate(LoginRequiredMixin, TemplateView):
    login_url = LOGIN_URL

    template_name = "tantalus/confirm_patient_edit.html"

    def get_context_and_render(self, request, to_edit, auto_generated_patients):
        context = {
            'patients_to_edit': to_edit,
            'auto_generated_patients': auto_generated_patients,
        }
        return render(request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        existing_patient_list = []
        for patient in request.session['to_edit']:
            existing_patient = tantalus.models.Patient.objects.get(patient_id=patient['patient_id'])
            existing_patient.new_external_patient_id = patient['external_patient_id']
            existing_patient.new_case_id = patient['case_id']

            if(existing_patient.external_patient_id == existing_patient.new_external_patient_id and existing_patient.case_id == existing_patient.new_case_id):
                continue
            elif(existing_patient.external_patient_id == existing_patient.new_external_patient_id):
                existing_patient.fields_changed = "Case ID Changed"
            elif(existing_patient.case_id == existing_patient.new_case_id):
                existing_patient.fields_changed = "External Patient ID Changed"
            else:
                existing_patient.fields_changed = "External Patient ID and Case ID Changed"

            existing_patient_list.append(existing_patient)

        return self.get_context_and_render(request, existing_patient_list, request.session['auto_generated_patients'])

    def post(self, request, *args, **kwargs):

        for patient in request.session['to_edit']:
            existing_patient = tantalus.models.Patient.objects.get(patient_id=patient['patient_id'])
            existing_patient.reference_id = patient['reference_id']
            existing_patient.external_patient_id = patient['external_patient_id']
            existing_patient.case_id = patient['case_id']
            existing_patient.save()

        for patient in request.session['auto_generated_patients']:
            new_patient = tantalus.models.Patient(**patient)
            new_patient.save()

        msg = "Successfully modified and created all Patients."
        messages.success(request, msg)
        return HttpResponseRedirect(reverse('patient-list'))


class PatientEdit(LoginRequiredMixin, TemplateView):
    login_url = LOGIN_URL

    template_name = "tantalus/patient_edit.html"

    def get_context_and_render(self, request, form, pk=None):
        context = {
            'pk':pk,
            'form': form,
        }
        return render(request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        patient_pk = kwargs['pk']
        patient = tantalus.models.Patient.objects.get(id=patient_pk)
        form = tantalus.forms.PatientForm(instance=patient)
        return self.get_context_and_render(request, form, patient_pk)

    def post(self, request, *args, **kwargs):
        patient_pk = kwargs['pk']
        patient = tantalus.models.Patient.objects.get(id=patient_pk)
        form = tantalus.forms.PatientForm(request.POST, instance=patient)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            msg = "Successfully edited Patient {}.".format(patient.patient_id)
            messages.success(request, msg)
            return HttpResponseRedirect(instance.get_absolute_url())
        else:
            msg = "Failed to edit the Patient. Please fix the errors below."
            messages.error(request, msg)
            return self.get_context_and_render(request, form, patient_pk)


class SubmissionCreate(LoginRequiredMixin, TemplateView):
    """
    tantalus.models.Sample create page.
    """
    login_url = LOGIN_URL

    template_name = "tantalus/submission_create.html"

    def get_context_and_render(self, request, form, pk=None):
        context = {
            'pk':pk,
            'form': form,
        }
        return render(request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        today = date.today().strftime('%B %d, %Y')
        form = tantalus.forms.SubmissionForm(initial={'submission_date': today, 'submitted_by': request.user})
        return self.get_context_and_render(request, form)

    def post(self, request, *args, **kwargs):
        form = tantalus.forms.SubmissionForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            msg = "Successfully created the tantalus.models.Submission."
            messages.success(request, msg)
            return HttpResponseRedirect(instance.get_absolute_url())
        else:
            msg = "Failed to create the sample. Please fix the errors below."
            messages.error(request, msg)
            return self.get_context_and_render(request, form)


class SpecificSubmissionCreate(LoginRequiredMixin, TemplateView):
    """
    tantalus.models.Sample create page.
    """
    login_url = LOGIN_URL
    template_name = "tantalus/submission_create.html"

    def get_context_and_render(self, request, sample_pk, form, pk=None):
        context = {
            'pk':pk,
            'form': form,
            'sample_pk': sample_pk,
        }
        return render(request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        today = date.today().strftime('%B %d, %Y')
        sample = get_object_or_404(tantalus.models.Sample,pk=kwargs['sample_pk'])
        form = tantalus.forms.SubmissionForm(initial={'submission_date': today, 'submitted_by': request.user, 'sample': sample})
        return self.get_context_and_render(request, kwargs['sample_pk'], form)

    def post(self, request, *args, **kwargs):
        form = tantalus.forms.SubmissionForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            msg = "Successfully created the tantalus.models.Submission."
            messages.success(request, msg)
            return HttpResponseRedirect(instance.get_absolute_url())
        else:
            msg = "Failed to create the sample. Please fix the errors below."
            messages.error(request, msg)
            return self.get_context_and_render(request, form)


class SampleCreate(LoginRequiredMixin, TemplateView):
    """
    tantalus.models.Sample create page.
    """
    login_url = LOGIN_URL

    template_name = "tantalus/sample_create.html"

    def get_context_and_render(self, request, form, multi_form, pk=None):
        context = {
            'pk':pk,
            'form': form,
            'multi_form': multi_form,
        }
        return render(request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        form = tantalus.forms.SampleForm()
        multi_form = tantalus.forms.UploadSampleForm()
        return self.get_context_and_render(request, form, multi_form)

    def post(self, request, *args, **kwargs):
        form = tantalus.forms.SampleForm(request.POST)
        multi_form = tantalus.forms.UploadSampleForm(request.POST, request.FILES)

        if form.is_valid():
            instance = form.save()
            msg = "Successfully created the tantalus.models.Sample."
            messages.success(request, msg)
            return HttpResponseRedirect(instance.get_absolute_url())
        elif multi_form.is_valid():
            samples_df, projects_list, one_ref_found, no_ref_found, multiple_refs_found = multi_form.get_sample_data()

            form_headers = samples_df.columns.tolist()

            reference_id_index = form_headers.index('Reference ID')
            suffix_index = form_headers.index('Suffix')
            submitter_index = form_headers.index('Submitter')
            researcher_index = form_headers.index('Researcher')
            tissue_index = form_headers.index('Tissue')
            note_index = form_headers.index('Note')
            external_sample_id = form_headers.index('External Sample ID')

            #Get next available SA ID if new Patients need to be created
            SA_prefix_patients = tantalus.models.Patient.objects.filter(patient_id__startswith='SA').order_by('-patient_id')
            SA_ids = []
            for patient in SA_prefix_patients:
                SA_ids.append(int(patient.patient_id[2:]))
            SA_ids.sort()
            next_available_SA_number = SA_ids[-1] + 1

            samples_with_one_match = []
            samples_with_no_match = []
            samples_with_multiple_matches = []

            for idx, sample_row in samples_df.iterrows():
                multiple_matches = []
                if(pd.isnull(sample_row[submitter_index])):
                    submitter = str(request.user)
                else:
                    submitter = sample_row[submitter_index]

                projects_name_list = []

                for project in projects_list[idx]:
                    projects_name_list.append(project.name)

                incomplete_sample = {
                    "external_sample_id": sample_row[external_sample_id],
                    "submitter": submitter,
                    "researcher": sample_row[researcher_index],
                    "tissue": sample_row[tissue_index],
                    "note": sample_row[note_index],
                    "projects": projects_name_list,
                }


                if(sample_row[reference_id_index] in one_ref_found):
                    incomplete_sample['patient'] = model_to_dict(tantalus.models.Patient.objects.get(reference_id=sample_row[reference_id_index]))
                    incomplete_sample['sample_id'] = incomplete_sample['patient']['patient_id'] + sample_row[suffix_index]
                    samples_with_one_match.append(incomplete_sample)
                elif(sample_row[reference_id_index] in no_ref_found): #Create the Patient
                    patient = tantalus.models.Patient(
                        patient_id='SA'+str(next_available_SA_number),
                        reference_id=sample_row[reference_id_index],
                    )
                    incomplete_sample['new_patient'] = model_to_dict(patient)
                    incomplete_sample['sample_id'] = patient.patient_id + sample_row[suffix_index]
                    samples_with_no_match.append(incomplete_sample)
                else:
                    patients = tantalus.models.Patient.objects.filter(reference_id=sample_row[reference_id_index])
                    for patient in patients:
                        multiple_matches.append(model_to_dict(patient))
                    incomplete_sample['patients'] = multiple_matches
                    incomplete_sample['reference_id'] = patient.reference_id
                    incomplete_sample['suffix'] = sample_row[suffix_index]
                    samples_with_multiple_matches.append(incomplete_sample)

            request.session['samples_with_one_match'] = samples_with_one_match
            request.session['samples_with_multiple_matches'] = samples_with_multiple_matches
            request.session['samples_with_no_match'] = samples_with_no_match
            return HttpResponseRedirect(reverse('confirm-samples-create'))
        else:
            msg = "Failed to create the sample. Please fix the errors below."
            messages.error(request, msg)
            return self.get_context_and_render(request, form, multi_form)


@method_decorator(login_required, name='dispatch')
class ConfirmSamplesCreate(TemplateView):

    template_name = 'tantalus/confirm_samples_create.html'

    def get_context_and_render(self, request, samples_with_one_match, samples_with_multiple_matches, samples_with_no_match):
        context = {
            'samples_with_one_match': samples_with_one_match,
            'samples_with_multiple_matches': samples_with_multiple_matches,
            'samples_with_no_match': samples_with_no_match,
        }

        return render(request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        samples_with_one_match = request.session['samples_with_one_match']
        samples_with_multiple_matches = request.session['samples_with_multiple_matches']
        samples_with_no_match = request.session['samples_with_no_match']
        return self.get_context_and_render(request, samples_with_one_match, samples_with_multiple_matches, samples_with_no_match)

    def post(self, request, *args, **kwargs):
        samples_with_one_match = request.session['samples_with_one_match']
        samples_with_multiple_matches = request.session['samples_with_multiple_matches']
        samples_with_no_match = request.session['samples_with_no_match']

        confirmed_samples_with_one_match_indices = request.POST.getlist('confirm[]')
        confirmed_samples_with_no_match_indices = request.POST.getlist('confirm_create[]')

        confirmed_samples_with_multiple_matches_indices = []
        for sample in samples_with_multiple_matches:
            if(request.POST.get(sample['reference_id']) is None):
                pass
            else:
                try:
                    patient = tantalus.models.Patient.objects.get(patient_id=request.POST.get(sample['reference_id']))
                    sample['patient'] = patient
                    sample['sample_id'] = patient.SA_id + sample['suffix']
                    sample.pop('reference_id')
                    sample.pop('patients')
                    sample.pop('suffix')
                    projects = sample.pop('projects')
                    created_sample = tantalus.models.Sample.objects.create(**sample)

                    for project in projects:
                        created_sample.projects.add(tantalus.models.Project.objects.get(name=project))
                    created_sample.save()
                except Exception as e:
                    messages.error(request, str(e))
                    return HttpResponseRedirect((request.path))


        #For loop finds out which samples were selected for SA_IDs that were found
        for idx, sample in enumerate(samples_with_one_match):
            if str(idx) in confirmed_samples_with_one_match_indices:
                patient = tantalus.models.Patient.objects.get(patient_id=sample['patient']['patient_id'])
                sample['patient'] = patient
                sample.pop('patient')
                projects = sample.pop('projects')
                created_sample = tantalus.models.Sample.objects.create(**sample)
                for project in projects:
                    created_sample.projects.add(tantalus.models.Project.objects.get(name=project))
                created_sample.save()

        for idx, sample in enumerate(samples_with_no_match):
            if(str(idx) in confirmed_samples_with_no_match_indices):
                patient = tantalus.models.Patient.objects.create(**sample['new_patient'])
                sample['patient'] = patient
                sample.pop('new_patient')
                projects = sample.pop('projects')
                created_sample = tantalus.models.Sample.objects.create(**sample)
                for project in projects:
                    created_sample.projects.add(tantalus.models.Project.objects.get(name=project))
                created_sample.save()

        messages.success(request, 'Successfully Created Samples')
        return HttpResponseRedirect(reverse('sample-list'))


class SpecificSampleCreate(LoginRequiredMixin, TemplateView):
    """
    tantalus.models.Sample create page.
    """
    login_url = LOGIN_URL

    template_name = "tantalus/specific_sample_create.html"

    def get_context_and_render(self, request, form, patient_id, pk=None):
        context = {
            'pk':pk,
            'form': form,
            'patient_id': patient_id,
        }
        return render(request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        patient_id = kwargs.get('patient_id').encode('utf-8')
        form = tantalus.forms.SampleForm(initial={'sample_id': patient_id, 'patient_id': patient_id})
        return self.get_context_and_render(request, form, patient_id)

    def post(self, request, *args, **kwargs):
        form = tantalus.forms.SampleForm(request.POST)

        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            msg = "Successfully created the tantalus.models.Sample."
            messages.success(request, msg)
            return HttpResponseRedirect(instance.get_absolute_url())
        else:
            msg = "Failed to create the sample. Please fix the errors below."
            messages.error(request, msg)
            patient_id = kwargs.get('patient_id').encode('utf-8')
            return self.get_context_and_render(request, form, patient_id)


class SampleEdit(LoginRequiredMixin, TemplateView):
    login_url = LOGIN_URL

    template_name = "tantalus/sample_edit.html"

    def get_context_and_render(self, request, form, pk=None):
        context = {
            'pk':pk,
            'form': form,
        }
        return render(request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        sample_pk = kwargs['pk']
        sample = tantalus.models.Sample.objects.get(id=sample_pk)
        form = tantalus.forms.SampleForm(instance=sample)
        return self.get_context_and_render(request, form, sample_pk)

    def post(self, request, *args, **kwargs):
        sample_pk = kwargs['pk']
        sample = tantalus.models.Sample.objects.get(id=sample_pk)
        form = tantalus.forms.SampleForm(request.POST, instance=sample)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            msg = "Successfully edited Sample {}.".format(sample.sample_id)
            messages.success(request, msg)
            return HttpResponseRedirect(instance.get_absolute_url())
        else:
            msg = "Failed to edit the Sample. Please fix the errors below."
            messages.error(request, msg)
            return self.get_context_and_render(request, form, sample_pk)


@login_required
def export_sample_create_template(request):
    header_dict = {
        'Reference ID': [],
        'Suffix': [],
        'Submitter': [],
        'Researcher': [],
        'Tissue': [],
        'Note': [],
        'Projects': [],
        'External Sample ID': [],
    }
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="header-template.csv"'
    df = pd.DataFrame(header_dict)
    df.to_csv(response, index=False)
    return response


@login_required
@Render("tantalus/tag_list.html")
def tag_list(request):
    """
    List of Tags.
    """
    tags = tantalus.models.Tag.objects.all().order_by('name')
    context = {
        'tags': tags,
    }
    return context


@method_decorator(login_required, name='dispatch')
class TagDelete(View):
    """
    tantalus.models.Tag delete page.
    """
    def get(self, request, pk):
        get_object_or_404(tantalus.models.Tag,pk=pk).delete()
        msg = "Successfully deleted tag"
        messages.success(request, msg)
        return HttpResponseRedirect(reverse('tag-list'))


class TagDetail(LoginRequiredMixin, DetailView):
    login_url = LOGIN_URL

    model = tantalus.models.Tag
    template_name = "tantalus/tag_detail.html"

    def get_context_data(self, object):
        tag = get_object_or_404(tantalus.models.Tag, pk=object.id)
        sequence_datasets = tag.sequencedataset_set.all()
        results = tag.resultsdataset_set.all()
        context = {
            'tag': tag,
            'sequence_datasets': sequence_datasets,
            'results': results,
        }
        return context



@method_decorator(login_required, name='dispatch')
class TagDatasetDelete(View):
    """
    tantalus.models.Tag dataset delete page.
    """
    def get(self, request, pk,pk_2):
        dataset = get_object_or_404(tantalus.models.SequenceDataset,pk=pk)
        tag = get_object_or_404(tantalus.models.Tag,pk=pk_2)
        tag.sequencedataset_set.remove(dataset)
        msg = "Successfully removed datasest "
        messages.success(request, msg)
        return HttpResponseRedirect(reverse('tag-detail',kwargs={'pk':pk_2}))

@login_required
@Render("tantalus/curation_list.html")
def curation_list(request):
    """
    List of Curations.
    """
    #get a list of curation and order by their names
    curations = tantalus.models.Curation.objects.all().order_by('name')
    context = {
        'curations': curations,
    }
    return context


class CurationDetail(LoginRequiredMixin, DetailView):
    login_url = LOGIN_URL

    model = tantalus.models.Curation
    template_name = "tantalus/curation_detail.html"

    def get_context_data(self, object):
        #get the curation if it exists
        curation = get_object_or_404(tantalus.models.Curation, pk=object.id)
        #get a list of sequence datasets associated with this curation
        sequence_datasets = curation.sequencedatasets.all()
        #get the modification history of the curation
        curation_history_lst = get_curation_change(curation)
        context = {
            'curation': curation,
            'sequence_datasets': sequence_datasets,
            'curation_history':curation_history_lst,
            'pk': object.id
        }
        return context

class CurationEdit(LoginRequiredMixin, TemplateView):

    template_name = "tantalus/curation_edit.html"

    def get_context_data(self, pk):
        #get the curation by pk
        curation = tantalus.models.Curation.objects.get(id=pk)
        #pass the curation object to the curationEditForm
        selectable = set(tantalus.models.SequenceDataset.objects.all()).difference(curation.sequencedatasets.all())
        form=tantalus.forms.CurationEditForm(instance=curation)
        context = {
            "form" : form,
            "pk" : pk,
            "sequence_datasets": selectable,
            "sequence_datasets_selected": curation.sequencedatasets.all()
        }
        return  context

    def post(self, request, pk):
        #get the curation by pk
        curation = tantalus.models.Curation.objects.get(id=pk)
        #get a dict of information that the curation contains
        original_datasets = set(curation.sequencedatasets.all())
        version = curation.version
        form = tantalus.forms.CurationEditForm(request.POST, instance=curation)
        if form.is_valid():
            # Get the data from the html form
            instance = form.save(commit=False)
            # Get the current user who is modifying the form
            instance.user = request.user
            # Increase the version number
            new_datasets = set(form.cleaned_data["sequencedatasets"])
            added = new_datasets - original_datasets
            deleted = original_datasets - new_datasets
            unchanged = original_datasets.intersection(new_datasets)
            #if the curation object is changed, increase the version number and create the modification history
            if form.changed_data:
                instance.version = "v" + str(int(version[1:].split(".")[0]) + 1) + ".0.0"
                #make changes to the list of sequence datasets of the curation
                for dataset in deleted:
                    curationdataset = get_object_or_404(tantalus.models.CurationDataset,
                        curation_instance=instance,
                        sequencedataset_instance=dataset).delete()
                for dataset in added:
                    tantalus.models.CurationDataset.objects.create(
                        curation_instance=instance,
                        sequencedataset_instance=dataset,
                        version = instance.version)
                for dataset in unchanged:
                    curationdataset = get_object_or_404(tantalus.models.CurationDataset,
                        curation_instance=instance,
                        sequencedataset_instance=dataset)
                    curationdataset.version = instance.version
                    curationdataset.save()
                # Save the object
                instance.save()
                msg = "Successfully updated the Curation."
                messages.success(request, msg)
            else:
                msg = "No change was detected."
                messages.warning(request, msg)
            return HttpResponseRedirect(curation.get_absolute_url())
        else:
            #if the form is not valid, then catch and print all the errors
            error_dict = json.loads(form.errors.as_json())
            for field in error_dict:
                error_message = error_dict[field][0]["message"]
                #show the error messages onto the screen
                messages.error(request, error_message)
            form = tantalus.forms.CurationEditForm(instance=curation)
            return self.get_context_and_render(request, form, pk=pk)


class CurationCreate(LoginRequiredMixin, TemplateView):
    template_name = "tantalus/curation_create.html"
    def get_context_and_render(self, request, form):
        context = {
            'form': form,
            'sequence_datasets': tantalus.models.SequenceDataset.objects.all()
            }
        return render(request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        #create an empty curation creation form
        form = tantalus.forms.CurationCreateForm()
        return self.get_context_and_render(request, form)

    def post(self, request, *args, **kwargs):
        form = tantalus.forms.CurationCreateForm(request.POST)
        #check if the form is valid
        if form.is_valid():
            #Get the corresponding data from the form
            instance = form.save(commit=False)
            #Get the user who is creating the object
            instance.user = request.user
            instance.save()
            #next, save the m2m field
            for dataset in form.cleaned_data["sequencedatasets"]:
                tantalus.models.CurationDataset.objects.create(
                    curation_instance=instance,
                    sequencedataset_instance=dataset,
                    version = instance.version)
            #form.save_m2m()
            msg = "Successfully create the Curation."
            messages.success(request, msg)
            return HttpResponseRedirect(instance.get_absolute_url())
        else:
            #if not valid, then catch and print all the errors
            error_dict = json.loads(form.errors.as_json())
            for field in error_dict:
                error_message = error_dict[field][0]["message"]
                messages.error(request, error_message)
            form = tantalus.forms.CurationCreateForm()
            return self.get_context_and_render(request, form)

class ResultJSON(BaseDatatableView):
    model = tantalus.models.ResultsDataset
    columns = ['id', 'owner', 'name', 'results_type', 'results_version', 'samples', 'libraries', 'analysis']
    order_columns = ['id', 'owner', 'name', 'results_type', 'results_version', 'samples', 'libraries', 'analysis']


    def render_column(self, row, column):
        if column == 'owner':
            return str(row.owner)
        if column == 'name':
            return row.name
        if column == 'results_type':
            return row.results_type
        if column == 'results_version':
            return row.results_version
        if column == 'samples':
            return [s.sample_id for s in row.samples.all()] if row.samples.all() else "None"
        if column == 'libraries':
            return [l.library_id for l in row.libraries.all()]
        if column == 'analysis':
            return str(row.analysis)
        else:
            return super(ResultJSON, self).render_column(row, column)

    def filter_queryset(self, qs):
        search = self.request.GET.get('search[value]', None)
        if search:
            search_list = search.split(" ")
            qs =  qs.filter(reduce(operator.and_,[
                                         Q(analysis__name__istartswith=key)|Q(id__istartswith=key)|Q(name__istartswith=key)
                             |Q(results_type__istartswith=key)|Q(libraries__library_id__istartswith=key)
                             |Q(results_version__istartswith=key)|Q(owner__username__istartswith=key)|Q(samples__sample_id__istartswith=key)
                             |Q(analysis__name__icontains=key)|Q(id__icontains=key)|Q(name__icontains=key)|Q(results_type__icontains=key)
                             |Q(libraries__library_id__icontains=key)|Q(results_version__icontains=key)|Q(owner__username__icontains=key)
                             |Q(samples__sample_id__icontains=key)|Q(samples__sample_id__in=search_list) for key in search_list if key is not ""]
                                   )
                            )

            return qs.distinct()

        return qs

class AnalysesJSON(BaseDatatableView):
    model = tantalus.models.Analysis
    columns = ['id', 'owner', 'name', 'version', 'analysis_type', 'jira_ticket', 'last_updated', 'status']
    order_columns = ['id', 'owner', 'name', 'version', 'analysis_type', 'jira_ticket', 'last_updated', 'status']

    def render_column(self, row, column):
        if column == 'owner':
            return str(row.owner)
        if column == 'name':
            return row.name
        if column == 'version':
            return row.version
        if column == 'analysis_type':
            return row.analysis_type.name if row.analysis_type else "None"
        if column == 'jira_ticket':
            return row.jira_ticket if row.jira_ticket else "None"
        if column == 'last_updated':
            return row.last_updated
        if column == 'status':
            return row.status
        else:
            return super(AnalysesJSON, self).render_column(row, column)

    def filter_queryset(self, qs):
        search = self.request.GET.get('search[value]', None)
        if search:
            return qs.filter(Q(id__istartswith=search)|Q(name__istartswith=search)|Q(version__istartswith=search)|Q(analysis_type__name__istartswith=search)
                             |Q(jira_ticket__istartswith=search)|Q(status__istartswith=search)|Q(id__icontains=search)|Q(name__icontains=search)
                             |Q(version__icontains=search)|Q(analysis_type__name__icontains=search)|Q(jira_ticket__icontains=search)|Q(status__icontains=search)
                             | Q(owner__username__icontains=search)|Q(owner__username__istartswith=search)).distinct()
        return qs


class FileResourceJSON(BaseDatatableView):
    model = tantalus.models.FileResource
    columns = ['id','filename', 'owner', 'created', 'size', 'last_updated', 'storages']
    order_columns = ['id','filename', 'owner', 'created', 'size', 'last_updated', 'storages']

    def get_id(request, id):
        return render(request, {'id' : id}, 'templates/tantalus/datatable/file_resources.html')

    def get_initial_queryset(self):
        id = self.request.GET.get("id", None)
        if self.request.GET.get("source_table", None) == "sequencedataset":
            return tantalus.models.SequenceDataset.objects.filter(id=id)[0].file_resources.all()
        else:
            return tantalus.models.ResultsDataset.objects.filter(id=id)[0].file_resources.all()

    def render_column(self, row, column):
        if column == 'id':
            return row.id
        if column == 'filename':
            return row.filename
        if column == 'owner':
            return str(row.owner)
        if column == 'created':
            return row.created
        if column == 'size':
            return row.get_file_size()
        if column == 'last_updated':
            return row.last_updated
        if column == 'storages':
            return row.get_storage_names()
        else:
            return super(FileResourceJSON, self).render_column(row, column)


    def filter_queryset(self, qs):
        search = self.request.GET.get('search[value]', None)
        if search:
            return qs.filter(Q(id__startswith=search)|Q(filename__istartswith=search)|Q(filename__icontains=search)).distinct()
        return qs



class DatasetListJSON(LoginRequiredMixin, BaseDatatableView):
    login_url = LOGIN_URL
    """
    Class used as AJAX data source through the ajax option in the abstractdataset_list template.
    This enables server-side processing of the data used in the javascript DataTables.
    """

    model = tantalus.models.SequenceDataset

    columns = [
        'id',
        'dataset_type',
        'sample_id',
        'library_id',
        'library_type',
        'is_production',
        'num_read_groups',
        'num_total_read_groups',
        'is_complete',
        'tags',
        'storages',
    ]

    # MUST be in the order of the columns
    order_columns = [
        'id',
        'dataset_type',
        'sample_id',
        'library_id',
        'library_type',
        'is_production',
        'num_read_groups',
        'num_total_read_groups',
        'is_complete',
        'tags',
        'storages',
    ]

    max_display_length = 50

    def get_context_data(self, *args, **kwargs):
        dataset_pks = self.request.session.get('dataset_search_results', None)
        if dataset_pks:
            kwargs['datasets'] = dataset_pks

        self.kwargs = kwargs
        return super(DatasetListJSON, self).get_context_data(*args, **kwargs)

    def get_initial_queryset(self):
        if 'datasets' in self.kwargs.keys():
            qs = tantalus.models.SequenceDataset.objects.filter(pk__in=self.kwargs['datasets'])
        else:
            qs = tantalus.models.SequenceDataset.objects.all()
        qs = qs.annotate(
            library_type=F('library__library_type__name'),
            num_read_groups=Count('sequence_lanes', distinct=True),
            annotate_library_id=F('library__library_id'),
            annotate_sample_id=F('sample__sample_id')
        )
        return qs

    def render_column(self, row, column):

        if column == 'dataset_type':
            return row.dataset_type

        if column == 'sample_id':
            return row.annotate_sample_id

        if column == 'library_id':
            return row.annotate_library_id

        if column == 'num_read_groups':
            return row.num_read_groups

        if column == 'tags':
            return list(map(str, row.tags.all().values_list('name', flat=True)))

        if column == 'storages':
            return list(row.get_storage_names())

        if column == 'library_type':
            return row.library_type

        if column == 'is_production':
            return row.is_production

        if column == 'num_total_read_groups':
            return row.get_num_total_sequencing_lanes()

        if column == 'is_complete':
            return row.get_is_complete()

        else:
            return super(DatasetListJSON, self).render_column(row, column)

    def filter_queryset(self, qs):
        search = self.request.GET.get('search[value]', None)
        if search:
            return qs.filter(
                Q(id__startswith=search) |
                Q(dataset_type__startswith=search) |
                Q(annotate_sample_id__startswith=search) |
                Q(annotate_library_id__startswith=search) |
                Q(library_type__startswith=search) |
                Q(dataset_type__startswith=search) |
                Q(tags__name__startswith=search)
            ).distinct()
        return qs


class DatasetList(LoginRequiredMixin, ListView):
    login_url = LOGIN_URL

    model = tantalus.models.SequenceDataset
    template_name = "tantalus/abstractdataset_list.html"
    paginate_by = 100

    class Meta:
        ordering = ["id"]

    def get_context_data(self, **kwargs):

        # TODO: add other fields to the view?
        """
        Get context data, and pop session variables from search/tagging if they exist.
        """

        self.request.session.pop('dataset_search_results', None)
        self.request.session.pop('select_none_default', None)

        context = super(DatasetList, self).get_context_data(**kwargs)
        return context


class DatasetDetail(LoginRequiredMixin, DetailView):
    login_url = LOGIN_URL

    model = tantalus.models.SequenceDataset
    template_name = "tantalus/abstractdataset_detail.html"

    def get_context_data(self, **kwargs):
        # TODO: add other fields to the view?
        context = super(DatasetDetail, self).get_context_data(**kwargs)
        storage_ids = self.object.get_storage_names()
        context['storages'] = storage_ids
        context['pk'] = kwargs['object'].id
        context['form'] = tantalus.forms.AddDatasetToTagForm()
        return context

    def post(self, request, *args, **kwargs):
        dataset_pk = kwargs['pk']
        dataset = tantalus.models.SequenceDataset.objects.get(id=dataset_pk)
        form = tantalus.forms.AddDatasetToTagForm(request.POST)
        if form.is_valid():
            tag = form.cleaned_data['tag']
            dataset.tags.add(tag)
            dataset.save()
            msg = "Successfully added Tag {} to this Dataset.".format(tag.name)
            messages.success(request, msg)
            return HttpResponseRedirect(dataset.get_absolute_url())
        else:
            msg = "Invalid Tag Name"
            messages.error(request, msg)
            return HttpResponseRedirect(dataset.get_absolute_url())


class DatasetEdit(TemplateView):

    template_name = "tantalus/abstractdataset_edit.html"

    def get_context_data(self, pk):
        print("HELLO")
        dataset = tantalus.models.SequenceDataset.objects.get(id=pk)
        form=tantalus.forms.DatasetForm(instance=dataset)
        print("PRINTING FPRM")
        print(form._html_output)
        context = {
            "form" : form,
            "pk" : pk
        }
        return  context

    def post(self, request, pk):
        dataset = tantalus.models.SequenceDataset.objects.get(id=pk)
        form = tantalus.forms.DatasetForm(request.POST, instance=dataset)

        if form.is_valid():
            print(dir(form))
            form.save()
            msg = "Successfully updated the Dataset."
            messages.success(request, msg)
            return HttpResponseRedirect(dataset.get_absolute_url())

        msg = "Failed to update the Dataset. Please fix the errors below."
        messages.error(request, msg)
        return self.get_context_and_render(request, form, pk=pk)


@method_decorator(login_required, name='dispatch')
class DatasetDelete(View):
    """
    tantalus.models.SequenceDataset delete page.
    """
    def get(self, request, pk):
        dataset = get_object_or_404(tantalus.models.SequenceDataset, pk=pk)
        for file_resource in dataset.file_resources.all():
            for file_instance in file_resource.fileinstance_set.all():
                file_instance.is_deleted = True
                file_instance.save()
        dataset.delete()
        msg = "Successfully removed datasest"
        messages.success(request, msg)
        return HttpResponseRedirect(reverse('dataset-list'))


class DatasetSearch(LoginRequiredMixin, FormView):

    login_url = LOGIN_URL

    form_class = tantalus.forms.DatasetSearchForm
    success_url = reverse_lazy('dataset-tag')
    template_name = 'tantalus/abstractdataset_search_form.html'

    def post(self, request, *args, **kwargs):

        """
        Handles POST requests, instantiating a form instance with the passed POST variables and then checked for validity.
        """

        form = self.get_form()
        if form.is_valid():
            search_data = form.get_dataset_search_results()
            kwargs['kw_search_results'] =search_data
            request.session['dataset_search_results'] = search_data
            request.session.modified = True
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


@method_decorator(login_required, name='post')
class DatasetTag(FormView):
    form_class = tantalus.forms.DatasetTagForm
    template_name = 'tantalus/abstractdataset_tag_form.html'

    def get_context_data(self, **kwargs):

        """
        Insert the form into the context dict.
        Initialize queryset for tagging, and whether the default should have the whole queryset default to selected or not.
        """

        dataset_pks = self.request.session.get('dataset_search_results', None)
        if dataset_pks:
            datasets = tantalus.models.SequenceDataset.objects.filter(pk__in=dataset_pks)
            kwargs['datasets'] = datasets
            kwargs['dataset_pks'] = dataset_pks
        else:
            kwargs['datasets'] = tantalus.models.SequenceDataset.objects.all()
            kwargs['select_none_default'] = True

        if 'form' not in kwargs:
            kwargs['form'] = tantalus.forms.DatasetTagForm(datasets=dataset_pks)

        return super(DatasetTag, self).get_context_data(**kwargs)

    def get_form(self, form_class=None):

        """
        Returns an instance of the form to be used in this view.
        """

        if form_class is None:
            form_class = self.get_form_class()

        datasets = self.request.session.get('dataset_search_results', None)
        return form_class(datasets=datasets, **self.get_form_kwargs())

    def form_valid(self, form):
        form.add_dataset_tags()
        tag =  form.cleaned_data['tag_name']
        tag_id = tantalus.models.Tag.objects.get(name=tag)
        self.request.session.pop('dataset_search_results', None)
        self.request.session.pop('select_none_default', None)

        # Depending on which of the "tantalus.models.Tag" or "tantalus.models.Tag then transfer" buttons
        # was clicked to submit the form, take the appropriate action
        if self.request.POST.get('tag_and_transfer_button'):
            # Redirect to transfer
            return HttpResponseRedirect("%s?tag=%s" % (reverse('filetransfer-create'), tag))
        # Go to tantalus.models.Tag detail page
        return HttpResponseRedirect(reverse('tag-detail', kwargs={'pk': tag_id.id}))

def dataset_analysis_ajax(request):
    if request.method == 'POST':
        data = request.POST.getlist('data[]')
        if 'analysis_dataset_ajax' in request.session:
            del request.session['analysis_dataset_ajax']
        request.session['analysis_dataset_ajax'] =  map(int, data)

    return HttpResponse('')

@require_POST
def dataset_set_to_CSV(request):
    """A view to generate a CSV of datasets.

    Expects dataset_pks to be provided in the POST as a list of ints
    serialized as a string, each int of which corresponds to a dataset
    primary key.

    See https://docs.djangoproject.com/en/2.0/howto/outputting-csv/ for
    more info on outputting to CSV with Django.
    """
    # The http response, to which we'll write CSV rows to
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="datasets.csv"'

    # Set up an object to write CSVs to
    writer = csv.writer(response)

    # Functions to get dataset attributes. These need to return strings.
    def get_dataset_samples(instance):
        return instance.get_samples()

    def get_dataset_libraries(instance):
        return instance.get_libraries()

    def get_dataset_library_type(instance):
        return instance.get_library_type()

    def get_dataset_tags(instance):
        tags = instance.tags.all().values_list('name', flat=True)
        return ','.join([str(tag) for tag in tags])

    def get_dataset_storages(instance):
        storages = instance.get_storage_names()
        return ','.join(storages)

    def get_dataset_type(instance):
        return instance.get_dataset_type_name()

    def get_num_read(instance):
        return str(instance.get_num_total_sequencing_lanes())

    # Title and lambda function dictionary for dataset attributes used
    # for CSV header row. Each attribute has a title, used for the CSV
    # header row, and each attribute has a function, used getting the
    # value of the attribute, given a dataset instance.
    attribute_dict = {
            'pk': {'title': 'Dataset PK',
                   'function': lambda x: x.pk},
            'type': {'title': 'Type',
                     'function': get_dataset_type},
            'samples': {'title': 'Samples',
                        'function': get_dataset_samples},
            'libraries': {'title': 'Libraries',
                          'function': get_dataset_libraries},
            'library type': {'title': 'Library Type',
                             'function': get_dataset_library_type},
            'num read groups': {'title': 'Number of Read Groups',
                                'function': get_num_read},
            'tags': {'title': 'Tags',
                     'function': get_dataset_tags},
            'storages': {'title': 'Storages',
                         'function': get_dataset_storages},
            }

    # Dataset attributes to use. Choose from keys used in attribute_dict
    # above
    csv_attrs = ['pk',
                 'type',
                 'samples',
                 'libraries',
                 'library type',
                 'num read groups',
                 'tags',
                 'storages',]

    # Write the headers to the CSV file
    header_row = [attribute_dict[attr]['title'] for attr in csv_attrs]
    writer.writerow(header_row)

    # Get the datasets from the POST
    pks = sorted(json.loads(request.POST['dataset_pks']))
    datasets = tantalus.models.SequenceDataset.objects.filter(pk__in=pks)

    # Write the data from each dataset
    for dataset in datasets:
        # Get its attributes
        dataset_row = [attribute_dict[attr]['function'](dataset)
                                                        for attr in csv_attrs]

        # Write to CSV
        writer.writerow(dataset_row)

    return response


def get_storage_stats(storages=['all']):
    """A helper function to get data stats for all storages.

    Expects a list of storages as input, and outputs a dictionary of
    integers specifying the following:

    - num_bams: number of bam files in the storages
    - num_specs: number of spec files in the storages
    - num_bais: ...
    - num_fastqs: ...
    - num_active_file_transfers: ...
    - storage_size: size in bytes of files tracked on server
    """
    # Build the file instance set
    if 'all' in storages:
        file_resources = tantalus.models.FileResource.objects.all()
    else:
        file_resources = tantalus.models.FileResource.objects.filter(
            fileinstance__storage__name__in=storages)

    # Get the size of all storages
    storage_size = file_resources.aggregate(Sum('size'))
    storage_size = storage_size['size__sum']

    return {
            'storage_size': storage_size,
           }


def get_library_stats(filetype, storages_dict):
    """Get info on number of files in libraries.

    An assumption that this function makes is that all FASTQs come in
    the form of paired end FASTQs (cf. single end FASTQs). This
    assumption is currently true, and making it helps simplify the code
    a little.

    Args:
        filetype: A string which is either 'BAM' or 'FASTQ'.
        storages_dict: A dictionary where keys are storage names and
            values are a list of string of storage names. This framework
            lets us cluster several storages under a single name.
    Returns:
        A dictionary where the keys are the library types and the values
        are lists containing the name, file, and size count (under
        'name, 'file', and 'size') for each storage.
    """
    # Make sure the filetype is 'BAM' or 'FASTQ'
    assert filetype in ['BAM', 'FASTQ']

    # Results dictionary
    results = dict()

    # Get the list of library types that we'll get data for
    # Go through each library
    for lib_type in tantalus.models.LibraryType.objects.all():
        # Make a list to store results in
        results[lib_type] = list()

        # Go through each storage
        for storage_name, storages in storages_dict.items():
            # Get data for this storage and library. The distinct() at
            # the end of the queryset operations is necessary here, and
            # I'm not exactly sure why this is so, without it, filter
            # picks up a ton of duplicates. Very strange.
            matching_files = tantalus.models.FileResource.objects.filter(
                sequencedataset__library__library_type=lib_type.id).filter(
                fileinstance__storage__name__in=storages).distinct()

            # Compute results - first the number of files- Add field skip_file_import to gscwgsbamquery
            number = matching_files.count()
            size = matching_files.aggregate(Sum('size'))
            size = size['size__sum']
            size = 0 if size is None else int(size)


            results[lib_type].append({
                'name': storage_name,
                'number': number,
                'size': size,
                })

    # Return the per-library results
    return results


class DataStatsView(LoginRequiredMixin, TemplateView):
    login_url = LOGIN_URL
    """A view to show info on data statistics."""
    template_name = 'tantalus/data_stats.html'

    def get_context_data(self, **kwargs):
        """Get data info."""
        # Contains per-storage specific stats
        storage_stats = dict()

        # Go through local storages (i.e., non-cloud)
        for local_storage_name in ['gsc', 'shahlab', 'rocks']:
            # General stats
            storage_stats[local_storage_name] = (
                get_storage_stats([local_storage_name]))

        # Go through cloud storages.
        azure_storages = [x.name for x in tantalus.models.AzureBlobStorage.objects.all()]
        storage_stats['azure'] = get_storage_stats(azure_storages)

        # Get overall data stats over all storage locations
        storage_stats['all'] = get_storage_stats(['all'])
        # Contains per-library-type stats
        storages_dict = {'all': ['gsc', 'shahlab', 'rocks'] + azure_storages,
                         'gsc': ['gsc'],
                         'shahlab': ['shahlab'],
                         'rocks': ['rocks'],
                         'azure': azure_storages,
                        }
        bam_dict = get_library_stats('BAM', storages_dict)
        fastq_dict = get_library_stats('FASTQ', storages_dict)

        context = {
            'storage_stats': sorted(
                storage_stats.items(),
                key=lambda y: y[1]['storage_size'],
                reverse=True),
            'locations_list': sorted(['all', 'azure', 'gsc', 'rocks', 'shahlab']),
            'bam_library_stats': sorted(bam_dict.items()),
            'fastq_library_stats': sorted(fastq_dict.items()),
            }

        return context


class HomeView(TemplateView):

    login_url = LOGIN_URL

    template_name = 'tantalus/index.html'

    def get_context_data(self, **kwargs):
        context = {
            'dataset_bam_count': tantalus.models.SequenceDataset.objects.filter(dataset_type='BAM').count(),
            'dataset_fastq_count': tantalus.models.SequenceDataset.objects.filter(dataset_type='FQ').count(),
            'patient_count': tantalus.models.Patient.objects.all().count(),
            'sample_count': tantalus.models.Sample.objects.all().count(),
            'submission_count': tantalus.models.Submission.objects.all().count(),
            'result_count': tantalus.models.ResultsDataset.objects.all().count(),
            'analysis_count': tantalus.models.Analysis.objects.all().count(),
            'tag_count': tantalus.models.Tag.objects.all().count(),
            'curation_count': tantalus.models.Curation.objects.all().count(),
        }
        return context
