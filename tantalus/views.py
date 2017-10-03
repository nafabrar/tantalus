from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView
from django.views.generic.edit import ModelFormMixin, View
from django.views.generic.base import TemplateView
from django.db import transaction
from django.shortcuts import get_object_or_404, render
from tantalus.models import FileTransfer, Deployment, FileResource
from tasks import transfer_file
from tantalus.utils import create_deployment_file_transfers
from misc.helpers import Render
from .models import Sample
from .forms import SampleForm

def search_view(request):
    query_str = request.GET.get('query_str')
    instance = None

    # search for samples
    if Sample.objects.filter(sample_id=query_str):
        instance = Sample.objects.filter(sample_id=query_str)[0]

    if instance:
        return HttpResponseRedirect(instance.get_absolute_url())
    else:
        msg = "Sorry, no match found."
        messages.warning(request, msg)
        return HttpResponseRedirect(reverse('home'))

@Render("tantalus/sample_list.html")
def sample_list(request):
    """list of samples."""
    samples = Sample.objects.all().order_by('sample_id')
    context = {'samples': samples}
    return context

#============================
# Classes
#----------------------------
class FileTransferView(TemplateView):
    template_name = 'tantalus/filetransfer_list.html'
    
    def get_context_data(self, **kwargs):
        transfers = FileTransfer.objects.all()
        context = {'transfers': transfers}
        return context


class DeploymentView(TemplateView):
    template_name = 'tantalus/deployment_list.html'
    
    def get_context_data(self, **kwargs):
        deployments = Deployment.objects.all()
        context = {'deployments': deployments}
        return context

@method_decorator(login_required, name='get')
class DeploymentCreateView(CreateView):
    model = Deployment
    fields = ['from_storage', 'to_storage', 'datasets']

    def post(self, request, *args, **kwargs):
        try:
            self.object = None
            with transaction.atomic():
                form = self.get_form()
                if form.is_valid():
                    self.object = form.save()
                    self.object.state = 'Started'
                    self.object.save()

                    file_transfer_ids = []

                    deployment = self.object
                    # TODO: start celery tasks
                    create_deployment_file_transfers(deployment)
                    return super(ModelFormMixin, self).form_valid(form)
        except ValueError as e:
            error_message = ' '.join(e.args)
            messages.error(request, error_message)
            #TODO: override methods + update template so that error message is passed through and is useful
        return self.form_invalid(form)

@method_decorator(login_required, name='dispatch')
class SampleCreate(TemplateView):

    """
    Sample create page.
    """

    template_name="tantalus/sample_create.html"

    def get_context_and_render(self, request, form, pk=None):
        context = {
            'pk':pk,
            'form': form
        }
        return render(request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        form = SampleForm()
        return self.get_context_and_render(request, form)

    def post(self, request, *args, **kwargs):
        form = SampleForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            msg = "Successfully created the Sample."
            messages.success(request, msg)
            return HttpResponseRedirect(instance.get_absolute_url())

        msg = "Failed to create the sample. Please fix the errors below."
        messages.error(request, msg)
        return self.get_context_and_render(request, form)

class HomeView(TemplateView):
    template_name = 'tantalus/index.html'
    
    def get_context_data(self, **kwargs):
        context = {
    		'deployment_count': Deployment.objects.all().count(),
            'sample_count': Sample.objects.all().count(),
    		'transfer_count': FileTransfer.objects.all().count()
    	}
        return context