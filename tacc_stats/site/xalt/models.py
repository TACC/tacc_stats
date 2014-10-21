"""The database models of tacc stats"""

from django.db import models
from django.forms import ModelForm

class run(models.Model):
    run_id = models.BigIntegerField(primary_key=True)
    job_id = models.CharField(max_length=11)
    run_uuid =  models.CharField(max_length=36)

    date =  models.DateTimeField()
    syshost = models.CharField(max_length=64)
    uuid = models.CharField(max_length=36,null=True)
    hash_id = models.CharField(max_length=40)

    account = models.CharField(max_length=11)
    exec_type = models.CharField(max_length=7)
    start_time =  models.FloatField()
    end_time = models.FloatField()
    run_time = models.FloatField()

    num_cores = models.PositiveIntegerField()
    num_nodes = models.PositiveIntegerField()
    num_threads = models.PositiveIntegerField()

    queue = models.CharField(max_length=32)
    user = models.CharField(max_length=32)
    exec_path = models.CharField(max_length=1024)

    module_name = models.CharField(max_length=64,null=True)
    cwd = models.CharField(max_length=1024, null=True)

    def __unicode__(self):
        return str(self.run_id)
