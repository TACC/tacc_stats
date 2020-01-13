"""The database models of tacc stats"""

from django.db import models
from django.forms import ModelForm
from django.contrib.postgres.fields import ArrayField

class Job(models.Model):
    id = models.BigIntegerField(primary_key=True)
    uid = models.BigIntegerField(null=True)
    project = models.CharField(max_length=128)
    start_time =  models.DateTimeField(null=True)
    end_time = models.DateTimeField(null=True)
    start_epoch =  models.PositiveIntegerField(null=True)
    end_epoch = models.PositiveIntegerField(null=True)
    run_time = models.PositiveIntegerField(null=True)
    requested_time = models.PositiveIntegerField(null=True)
    queue_time = models.PositiveIntegerField(null=True)
    queue = models.CharField(max_length=16, null=True)
    name =  models.CharField(max_length=128, null=True)
    status = models.CharField(max_length=16, null=True)
    nodes = models.PositiveIntegerField(null=True)
    cores = models.PositiveIntegerField(null=True)
    wayness = models.PositiveIntegerField(null=True)
    path =  models.FilePathField(max_length=128, null=True)
    date = models.DateField(db_index=True,null=True)
    user = models.CharField(max_length=128, null=True)
    exe = models.CharField(max_length=128, null=True)
    exec_path = models.CharField(max_length=1024, null=True)
    exe_list = models.TextField(null=True)
    cwd = models.CharField(max_length=128, null=True)
    threads = models.BigIntegerField(null=True)
    validated = models.BooleanField(default=False)

    avg_cpi = models.FloatField(null=True)
    avg_freq = models.FloatField(null=True)
    avg_mcdrambw =  models.FloatField(null=True)
    avg_mbw = models.FloatField(null=True)
    avg_page_hitrate =  models.FloatField(null=True)
    avg_flops_64b = models.FloatField(null=True)
    vecpercent_64b = models.FloatField(null=True)
    avg_vector_width_64b = models.FloatField(null=True)
    avg_flops_32b = models.FloatField(null=True)
    vecpercent_32b = models.FloatField(null=True)
    avg_vector_width_32b = models.FloatField(null=True)
    avg_loads    = models.BigIntegerField(null=True)
    avg_l1loadhits = models.BigIntegerField(null=True)
    avg_l2loadhits = models.BigIntegerField(null=True)
    avg_llcloadhits = models.BigIntegerField(null=True)
    avg_sf_evictrate = models.FloatField(null=True)
    max_sf_evictrate = models.FloatField(null=True)

    node_imbalance = models.FloatField(null=True)
    time_imbalance = models.FloatField(null=True)
    mem_hwm = models.FloatField(null=True)
    avg_cpuusage = models.FloatField(null=True)
    avg_blockbw = models.FloatField(null=True)

    max_packetrate = models.FloatField(null=True)
    avg_packetsize = models.FloatField(null=True)
    avg_fabricbw = models.FloatField(null=True)
    max_fabricbw = models.FloatField(null=True)
    avg_ethbw = models.FloatField(null=True)

    max_mds = models.FloatField(null=True)
    avg_lnetmsgs = models.FloatField(null=True)
    avg_lnetbw = models.FloatField(null=True)
    max_lnetbw = models.FloatField(null=True)
    avg_mdcreqs =  models.FloatField(null=True)
    avg_mdcwait =  models.FloatField(null=True)
    avg_oscreqs =  models.FloatField(null=True)
    avg_oscwait =  models.FloatField(null=True)
    avg_openclose =  models.FloatField(null=True)

    max_load15 =  models.FloatField(null=True)

    
    def __unicode__(self):
        return str(self.id)

    def color(self):
        if self.status == 'COMPLETED': 
            ret_val = "E1EDFA"
        elif self.status == 'FAILED':
            ret_val = "FFB2B2"
        else:
            ret_val = "silver"
        return ret_val

    def sus(self):
        factor = 1
        if self.queue == 'largemem': factor = 2 # double charge rate
        return self.nodes * self.run_time * 0.0002777777777777778 * factor

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

