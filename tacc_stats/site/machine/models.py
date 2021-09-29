"""The database models of tacc stats"""

from django.db import models
from django.forms import ModelForm
from django.contrib.postgres.fields import ArrayField

class job_data(models.Model):
    class Meta:
        db_table = 'job_data'
        indexes = [models.Index(fields=['jid'])]
        ordering = ['jid']

    jid         = models.CharField(primary_key = True, max_length=32)
    account     = models.CharField(max_length=64, null = True)
    submit_time = models.DateTimeField()
    start_time  = models.DateTimeField()
    end_time    = models.DateTimeField(null = True)
    runtime     = models.FloatField()
    timelimit   = models.FloatField()
    node_hrs    = models.FloatField()    
    nhosts      = models.PositiveIntegerField(null = True)
    ncores      = models.PositiveIntegerField(null = True)
    username    = models.CharField(max_length = 64)
    state       = models.CharField(max_length = 64)
    queue       = models.CharField(max_length = 64)
    jobname     = models.TextField()
    host_list   = ArrayField(models.TextField())
    
    def __unicode__(self):
        return str(self.id)

    def color(self):
        if self.state == 'COMPLETED': 
            ret_val = "E1EDFA"
        elif self.state == 'FAILED':
            ret_val = "FFB2B2"
        else:
            ret_val = "silver"
        return ret_val
"""
class Proc(models.Model):
    job  = models.ForeignKey(Job, on_delete = models.CASCADE)
    name = models.CharField(max_length=128)
    host = models.CharField(max_length=128)
    uid  = models.IntegerField(null=True)
    pid  = models.IntegerField(null=True)
    VmHWM = models.FloatField(null=True)
    Threads = models.IntegerField(null=True)
    Cpus_allowed_list = models.CharField(max_length=128)
    Mems_allowed_list = models.CharField(max_length=128)

    def __unicode__(self):
        return str(self.name)


class Host(models.Model):
    name = models.CharField(max_length=128)
    jobs = models.ManyToManyField(Job)
    class Meta: ordering = ('name',)

    def __unicode__(self):
        return str(self.name)

class Libraries(models.Model):
    object_path = models.CharField(max_length=1024)
    module_name = models.CharField(max_length=64)
    jobs = models.ManyToManyField(Job)

    class Meta: ordering = ('object_path',)

    def __unicode__(self):
        return str(self.object_path)


class JobForm(ModelForm):
    class Meta:
        model = Job
        fields = ['id']

"""
