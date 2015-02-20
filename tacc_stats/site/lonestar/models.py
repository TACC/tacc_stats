"""The database models of tacc stats"""

from django.db import models
from django.forms import ModelForm

class LS4Job(models.Model):
    id = models.BigIntegerField(primary_key=True)
    project = models.CharField(max_length=128)
    start_time =  models.DateTimeField(null=True)
    end_time = models.DateTimeField(null=True)
    start_epoch =  models.PositiveIntegerField(null=True)
    end_epoch = models.PositiveIntegerField(null=True)
    run_time = models.PositiveIntegerField(null=True)
    submission_time = models.PositiveIntegerField(null=True)
    queue = models.CharField(max_length=16, null=True)
    name =  models.CharField(max_length=128, null=True)
    status = models.CharField(max_length=16, null=True)
    nodes = models.PositiveIntegerField(null=True)
    cores = models.PositiveIntegerField(null=True)
    #wayness = models.PositiveIntegerField(null=True)
    path =  models.FilePathField(max_length=128, null=True)
    date = models.DateField(db_index=True,null=True)
    user = models.CharField(max_length=128, null=True)
    exe = models.CharField(max_length=128, null=True)
    cwd = models.CharField(max_length=128, null=True)
    threads = models.BigIntegerField(null=True)

    #cpi = models.FloatField(null=True)
    #mbw = models.FloatField(null=True)

    def __unicode__(self):
        return str(self.id)

    def color(self):

        if self.status == 'COMPLETED': 
            ret_val = "lightblue"
        elif self.status == 'FAILED':
            ret_val = "red"
        else:
            ret_val = "silver"

        return ret_val


class LS4JobForm(ModelForm):
    class Meta:
        model = LS4Job
        fields = ['id']
