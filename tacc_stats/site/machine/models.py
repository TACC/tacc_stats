"""The database models of tacc stats"""

from django.db import models
from django.forms import ModelForm
from django.contrib.postgres.fields import ArrayField

# manage.py inspectdb

class job_data(models.Model):
    jid = models.CharField(primary_key = True, max_length=32)
    submit_time = models.DateTimeField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    runtime = models.FloatField(blank=True, null=True)
    timelimit = models.FloatField(blank=True, null=True)
    node_hrs = models.FloatField(blank=True, null=True)
    nhosts = models.IntegerField(blank=True, null=True)
    ncores = models.IntegerField(blank=True, null=True)
    username = models.CharField(max_length=64)
    account = models.CharField(max_length=64, blank=True, null=True)
    queue = models.CharField(max_length=64, blank=True, null=True)
    state = models.CharField(max_length=64, blank=True, null=True)
    jobname = models.TextField(blank=True, null=True)
    host_list   = ArrayField(models.TextField())

    class Meta:
        managed = False
        db_table = 'job_data'
    
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

class metrics_data(models.Model):
    jid = models.ForeignKey(job_data, on_delete = models.CASCADE, db_column='jid', blank=True, null=True)
    type = models.CharField(max_length=32, blank=True, null=True)
    metric = models.CharField(max_length=32, blank=True, null=True)
    units = models.CharField(max_length=16, blank=True, null=True)
    value = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'metrics_data'
        unique_together = (('jid', 'type', 'metric'),)

    def __unicode__(self):
        return str(self.jid + '_' + type  + '_' + metric)
