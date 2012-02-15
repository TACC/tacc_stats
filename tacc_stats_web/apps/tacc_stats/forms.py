from django import forms
from django.forms import ModelForm
from models import Job

class SearchForm(ModelForm):
    class Meta:
        model = Job
        fields = ('owner', 'begin', 'end', 'hosts', 'acct_id')
#        widgets = {
#            'hosts': forms.TextInput(attrs={'size':'40'}),
#        }

    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)

        for key in self.fields:
            self.fields[key].required = False

