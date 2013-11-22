"""The database models of tacc stats"""

from django.db import models
from django.forms import ModelForm

class Job(models.Model):
    id = models.BigIntegerField(primary_key=True)
    uid = models.BigIntegerField(null=True)
    project = models.CharField(max_length=128)
    start_time =  models.DateTimeField(null=True)
    end_time = models.DateTimeField(null=True)
    start_epoch =  models.PositiveIntegerField(null=True)
    end_epoch = models.PositiveIntegerField(null=True)
    run_time = models.PositiveIntegerField(null=True)
    queue_time = models.PositiveIntegerField(null=True)
    queue = models.CharField(max_length=16, null=True)
    name =  models.CharField(max_length=128, null=True)
    status = models.CharField(max_length=16, null=True)
    nodes = models.PositiveIntegerField(null=True)
    cores = models.PositiveIntegerField(null=True)
    path =  models.FilePathField(max_length=128, null=True)
    date = models.DateField(null=True)
    user = models.CharField(max_length=128, null=True)
    exe = models.CharField(max_length=128, null=True)
    cwd = models.CharField(max_length=128, null=True)
    threads = models.BigIntegerField(null=True)

    def __unicode__(self):
        return str(self.id)
    """
    @property
    def timespent(self):
        dt = self.end_epoch-self.start_epoch
        return dt
    """    
    def color(self):
        ret_val = "silver"
        if self.status != 'COMPLETED':
            ret_val = "red"
        elif self.run_time > 600:
            ret_val = "lightblue"
        return ret_val


class JobForm(ModelForm):
    class Meta:
        model = Job
        fields = ['id']
