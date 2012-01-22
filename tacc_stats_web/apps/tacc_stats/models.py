"""The database models of tacc stats"""

from django.db import models

class System(models.Model):
    """Details about the cluster"""
    name = models.CharField(max_length=128)

    def __unicode__(self):
        return self.name

class Node(models.Model):
    name = models.CharField(max_length=128)
    system = models.ForeignKey(System)

    def __unicode__(self):
        return "%s.%s" % (self.name, self.system.name)

class User(models.Model):
    user_name = models.CharField(max_length=128)
    systems = models.ManyToManyField(System)

    def __unicode__(self):
        return "User(%s)" % self.user_name

class Job(models.Model):
    system = models.ForeignKey(System)
    acct_id = models.BigIntegerField()
    owner = models.ForeignKey(User)
    hosts = models.ManyToManyField(Node)
    queue = models.CharField(max_length=16, null=True)
    queue_wait_time = models.IntegerField(null=True)
    begin = models.PositiveIntegerField(null=True)
    end = models.PositiveIntegerField(null=True)
    #run_time = models.IntegerField(null=True)
    #nr_hosts = models.IntegerField(null=True)
    nr_bad_hosts = models.IntegerField(null=True)
    nr_slots = models.IntegerField(null=True)
    pe = models.CharField(max_length=8, null=True)
    failed = models.BooleanField()
    exit_status = models.IntegerField(null=True)
    USER_FLOPS = models.BigIntegerField(null=True)
    SSE_FLOPS = models.BigIntegerField(null=True)
    DCSF = models.BigIntegerField(null=True)
    DRAM = models.BigIntegerField(null=True)
    HT0 = models.BigIntegerField(null=True)
    HT1 = models.BigIntegerField(null=True)
    HT2 = models.BigIntegerField(null=True)
    user = models.BigIntegerField(null=True)
    nice = models.BigIntegerField(null=True)
    system_time = models.BigIntegerField(null=True)
    idle = models.BigIntegerField(null=True)
    iowait = models.BigIntegerField(null=True)
    irq = models.BigIntegerField(null=True)
    softirq = models.BigIntegerField(null=True)
    share_open = models.IntegerField(null=True)
    share_read_bytes = models.BigIntegerField(null=True)
    share_write_bytes = models.BigIntegerField(null=True)
    work_open = models.IntegerField(null=True)
    work_read_bytes = models.BigIntegerField(null=True)
    work_write_bytes = models.BigIntegerField(null=True)
    scratch_open = models.IntegerField(null=True)
    scratch_read_bytes = models.BigIntegerField(null=True)
    scratch_write_bytes = models.BigIntegerField(null=True)
    lnet_rx_bytes = models.BigIntegerField(null=True)
    lnet_tx_bytes = models.BigIntegerField(null=True)
    ib_sw_rx_bytes = models.BigIntegerField(null=True)
    ib_sw_tx_bytes = models.BigIntegerField(null=True)
    net_rx_bytes = models.BigIntegerField(null=True)
    net_tx_bytes = models.BigIntegerField(null=True)
    MemTotal = models.BigIntegerField(null=True)
    MemUsed = models.BigIntegerField(null=True)
    FilePages = models.BigIntegerField(null=True)
    Mapped = models.BigIntegerField(null=True)
    AnonPages = models.BigIntegerField(null=True)
    Slab = models.BigIntegerField(null=True)

    #unique_together = ("system", "acct_id")

    @property
    def runtime(self):
        self.end - self.begin

    @property
    def nr_hosts(self):
        len(self.hosts.all())

    @property
    def timespent(self):
        return self.end - self.begin

    def color(self):
        ret_val = "LightBlue"
        if self.work_open > 3000:
            ret_val = "red"
        elif self.MemUsed > 30*2**30:
            ret_val = "orange"
        elif self.timespent > 3000:
            ret_val = "LightCoral"
        return ret_val


class Monitor(models.Model):
    kind = models.CharField(max_length=32)
    system = models.ForeignKey(System)

