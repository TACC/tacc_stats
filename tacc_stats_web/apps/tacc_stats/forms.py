from django import forms
from django.forms import ModelForm
from models import Job

class SearchForm(ModelForm):
    begin = forms.DateTimeField()
    end = forms.DateTimeField()

    class Meta:
        model = Job
        fields = ('owner', 'begin', 'end', 'acct_id')
#        widgets = {
#            'begin': forms.DateTimeField(),
#        }

    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)

        for key in self.fields:
            self.fields[key].required = False

