"""The database models of tacc stats"""

from django.db import models
import time
import math

COLORS = { 
    'Normal' : "background-color: rgba(0%, 0%, 100%, .2);",
    'High Files Open' : "background-color: rgba(100%, 0%, 0%, .2);",
    'High Memory Used' : "background-color: rgba(80%, 30%, 0%, .2)",
    'High Runtime' : "background-color: rgba(0%, 100%, 0%, .2)",
    'High Idle' : "background-color: rgba(50%, 0%, 50%, .2)"
}

class System(models.Model):
    """Details about the cluster"""
    name = models.CharField(max_length=128)

    def __unicode__(self):
        return self.name

class Node(models.Model):
    """Details about the specific node run on """
    name = models.CharField(max_length=128)
    system = models.ForeignKey(System)

    def __unicode__(self):
        return "%s.%s" % (self.name, self.system.name)

class User(models.Model):
    """ The person who submitted the job to the queue """
    user_name = models.CharField(max_length=128)
    systems = models.ManyToManyField(System)

    def __str__(self):
        return self.user_name

    def __unicode__(self):
        return "User(%s)" % self.user_name

class Job(models.Model):
    """
    Details about the task submitted to the compute cluster
    """
    system = models.ForeignKey(System)
    acct_id = models.BigIntegerField()
    owner = models.ForeignKey(User, null=True)
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

    amd64_pmc_CTL0 = models.BigIntegerField(null=True)
    amd64_pmc_CTL1 = models.BigIntegerField(null=True)
    amd64_pmc_CTL2 = models.BigIntegerField(null=True)
    amd64_pmc_CTL3 = models.BigIntegerField(null=True)
    amd64_pmc_CTR0 = models.BigIntegerField(null=True)
    amd64_pmc_CTR1 = models.BigIntegerField(null=True)
    amd64_pmc_CTR2 = models.BigIntegerField(null=True)
    amd64_pmc_CTR3 = models.BigIntegerField(null=True)
    block_in_flight = models.BigIntegerField(null=True)
    block_io_ticks = models.BigIntegerField(null=True)
    block_rd_ios = models.BigIntegerField(null=True)
    block_rd_merges = models.BigIntegerField(null=True)
    block_rd_sectors = models.BigIntegerField(null=True)
    block_rd_ticks = models.BigIntegerField(null=True)
    block_time_in_queue = models.BigIntegerField(null=True)
    block_wr_ios = models.BigIntegerField(null=True)
    block_wr_merges = models.BigIntegerField(null=True)
    block_wr_sectors = models.BigIntegerField(null=True)
    block_wr_ticks = models.BigIntegerField(null=True)
    cpu_idle = models.BigIntegerField(null=True)
    cpu_iowait = models.BigIntegerField(null=True)
    cpu_irq = models.BigIntegerField(null=True)
    cpu_nice = models.BigIntegerField(null=True)
    cpu_softirq = models.BigIntegerField(null=True)
    cpu_system = models.BigIntegerField(null=True)
    cpu_user = models.BigIntegerField(null=True)
    ib_sw_rx_bytes = models.BigIntegerField(null=True)
    ib_sw_rx_packets = models.BigIntegerField(null=True)
    ib_sw_tx_bytes = models.BigIntegerField(null=True)
    ib_sw_tx_packets = models.BigIntegerField(null=True)
    llite_alloc_inode_scratch = models.BigIntegerField(null=True)
    llite_alloc_inode_share = models.BigIntegerField(null=True)
    llite_alloc_inode_work = models.BigIntegerField(null=True)
    llite_close_scratch = models.BigIntegerField(null=True)
    llite_close_share = models.BigIntegerField(null=True)
    llite_close_work = models.BigIntegerField(null=True)
    llite_direct_read_scratch = models.BigIntegerField(null=True)
    llite_direct_read_share = models.BigIntegerField(null=True)
    llite_direct_read_work = models.BigIntegerField(null=True)
    llite_direct_write_scratch = models.BigIntegerField(null=True)
    llite_direct_write_share = models.BigIntegerField(null=True)
    llite_direct_write_work = models.BigIntegerField(null=True)
    llite_dirty_pages_hits_scratch = models.BigIntegerField(null=True)
    llite_dirty_pages_hits_share = models.BigIntegerField(null=True)
    llite_dirty_pages_hits_work = models.BigIntegerField(null=True)
    llite_dirty_pages_misses_scratch = models.BigIntegerField(null=True)
    llite_dirty_pages_misses_share = models.BigIntegerField(null=True)
    llite_dirty_pages_misses_work = models.BigIntegerField(null=True)
    llite_flock_scratch = models.BigIntegerField(null=True)
    llite_flock_share = models.BigIntegerField(null=True)
    llite_flock_work = models.BigIntegerField(null=True)
    llite_fsync_scratch = models.BigIntegerField(null=True)
    llite_fsync_share = models.BigIntegerField(null=True)
    llite_fsync_work = models.BigIntegerField(null=True)
    llite_getattr_scratch = models.BigIntegerField(null=True)
    llite_getattr_share = models.BigIntegerField(null=True)
    llite_getattr_work = models.BigIntegerField(null=True)
    llite_getxattr_scratch = models.BigIntegerField(null=True)
    llite_getxattr_share = models.BigIntegerField(null=True)
    llite_getxattr_work = models.BigIntegerField(null=True)
    llite_inode_permission_scratch = models.BigIntegerField(null=True)
    llite_inode_permission_share = models.BigIntegerField(null=True)
    llite_inode_permission_work = models.BigIntegerField(null=True)
    llite_ioctl_scratch = models.BigIntegerField(null=True)
    llite_ioctl_share = models.BigIntegerField(null=True)
    llite_ioctl_work = models.BigIntegerField(null=True)
    llite_listxattr_scratch = models.BigIntegerField(null=True)
    llite_listxattr_share = models.BigIntegerField(null=True)
    llite_listxattr_work = models.BigIntegerField(null=True)
    llite_mmap_scratch = models.BigIntegerField(null=True)
    llite_mmap_share = models.BigIntegerField(null=True)
    llite_mmap_work = models.BigIntegerField(null=True)
    llite_open_scratch = models.BigIntegerField(null=True)
    llite_open_share = models.BigIntegerField(null=True)
    llite_open_work = models.BigIntegerField(null=True)
    llite_read_bytes_scratch = models.BigIntegerField(null=True)
    llite_read_bytes_share = models.BigIntegerField(null=True)
    llite_read_bytes_work = models.BigIntegerField(null=True)
    llite_removexattr_scratch = models.BigIntegerField(null=True)
    llite_removexattr_share = models.BigIntegerField(null=True)
    llite_removexattr_work = models.BigIntegerField(null=True)
    llite_seek_scratch = models.BigIntegerField(null=True)
    llite_seek_share = models.BigIntegerField(null=True)
    llite_seek_work = models.BigIntegerField(null=True)
    llite_setattr_scratch = models.BigIntegerField(null=True)
    llite_setattr_share = models.BigIntegerField(null=True)
    llite_setattr_work = models.BigIntegerField(null=True)
    llite_setxattr_scratch = models.BigIntegerField(null=True)
    llite_setxattr_share = models.BigIntegerField(null=True)
    llite_setxattr_work = models.BigIntegerField(null=True)
    llite_statfs_scratch = models.BigIntegerField(null=True)
    llite_statfs_share = models.BigIntegerField(null=True)
    llite_statfs_work = models.BigIntegerField(null=True)
    llite_truncate_scratch = models.BigIntegerField(null=True)
    llite_truncate_share = models.BigIntegerField(null=True)
    llite_truncate_work = models.BigIntegerField(null=True)
    llite_write_bytes_scratch = models.BigIntegerField(null=True)
    llite_write_bytes_share = models.BigIntegerField(null=True)
    llite_write_bytes_work = models.BigIntegerField(null=True)
    lnet_rx_bytes_dropped = models.BigIntegerField(null=True)
    lnet_rx_bytes = models.BigIntegerField(null=True)
    lnet_rx_msgs_dropped = models.BigIntegerField(null=True)
    lnet_rx_msgs = models.BigIntegerField(null=True)
    lnet_tx_bytes = models.BigIntegerField(null=True)
    lnet_tx_msgs = models.BigIntegerField(null=True)
    mem_Active = models.BigIntegerField(null=True)
    mem_AnonPages = models.BigIntegerField(null=True)
    mem_Bounce = models.BigIntegerField(null=True)
    mem_Dirty = models.BigIntegerField(null=True)
    mem_FilePages = models.BigIntegerField(null=True)
    mem_HugePages_Free = models.BigIntegerField(null=True)
    mem_HugePages_Total = models.BigIntegerField(null=True)
    mem_Inactive = models.BigIntegerField(null=True)
    mem_Mapped = models.BigIntegerField(null=True)
    mem_MemFree = models.BigIntegerField(null=True)
    mem_MemTotal = models.BigIntegerField(null=True)
    mem_MemUsed = models.BigIntegerField(null=True)
    mem_NFS_Unstable = models.BigIntegerField(null=True)
    mem_PageTables = models.BigIntegerField(null=True)
    mem_Slab = models.BigIntegerField(null=True)
    mem_Writeback = models.BigIntegerField(null=True)
    net_collisions = models.BigIntegerField(null=True)
    net_multicast = models.BigIntegerField(null=True)
    net_rx_bytes = models.BigIntegerField(null=True)
    net_rx_compressed = models.BigIntegerField(null=True)
    net_rx_crc_errors = models.BigIntegerField(null=True)
    net_rx_dropped = models.BigIntegerField(null=True)
    net_rx_errors = models.BigIntegerField(null=True)
    net_rx_fifo_errors = models.BigIntegerField(null=True)
    net_rx_frame_errors = models.BigIntegerField(null=True)
    net_rx_length_errors = models.BigIntegerField(null=True)
    net_rx_missed_errors = models.BigIntegerField(null=True)
    net_rx_over_errors = models.BigIntegerField(null=True)
    net_rx_packets = models.BigIntegerField(null=True)
    net_tx_aborted_errors = models.BigIntegerField(null=True)
    net_tx_bytes = models.BigIntegerField(null=True)
    net_tx_carrier_errors = models.BigIntegerField(null=True)
    net_tx_compressed = models.BigIntegerField(null=True)
    net_tx_dropped = models.BigIntegerField(null=True)
    net_tx_errors = models.BigIntegerField(null=True)
    net_tx_fifo_errors = models.BigIntegerField(null=True)
    net_tx_heartbeat_errors = models.BigIntegerField(null=True)
    net_tx_packets = models.BigIntegerField(null=True)
    net_tx_window_errors = models.BigIntegerField(null=True)
    numa_interleave_hit = models.BigIntegerField(null=True)
    numa_local_node = models.BigIntegerField(null=True)
    numa_numa_foreign = models.BigIntegerField(null=True)
    numa_numa_hit = models.BigIntegerField(null=True)
    numa_numa_miss = models.BigIntegerField(null=True)
    numa_other_node = models.BigIntegerField(null=True)
    ps_ctxt = models.BigIntegerField(null=True)
    ps_load_15 = models.BigIntegerField(null=True)
    ps_load_1 = models.BigIntegerField(null=True)
    ps_load_5 = models.BigIntegerField(null=True)
    ps_nr_running = models.BigIntegerField(null=True)
    ps_nr_threads = models.BigIntegerField(null=True)
    ps_processes = models.BigIntegerField(null=True)
    sysv_shm_mem_used = models.BigIntegerField(null=True)
    sysv_shm_segs_used = models.BigIntegerField(null=True)
    tmpfs_bytes_used = models.BigIntegerField(null=True)
    tmpfs_files_used = models.BigIntegerField(null=True)
    vfs_dentry_use = models.BigIntegerField(null=True)
    vfs_file_use = models.BigIntegerField(null=True)
    vfs_inode_use = models.BigIntegerField(null=True)
    vm_allocstall = models.BigIntegerField(null=True)
    vm_kswapd_inodesteal = models.BigIntegerField(null=True)
    vm_kswapd_steal = models.BigIntegerField(null=True)
    vm_pageoutrun = models.BigIntegerField(null=True)
    vm_pgactivate = models.BigIntegerField(null=True)
    vm_pgalloc_normal = models.BigIntegerField(null=True)
    vm_pgdeactivate = models.BigIntegerField(null=True)
    vm_pgfault = models.BigIntegerField(null=True)
    vm_pgfree = models.BigIntegerField(null=True)
    vm_pginodesteal = models.BigIntegerField(null=True)
    vm_pgmajfault = models.BigIntegerField(null=True)
    vm_pgpgin = models.BigIntegerField(null=True)
    vm_pgpgout = models.BigIntegerField(null=True)
    vm_pgrefill_normal = models.BigIntegerField(null=True)
    vm_pgrotated = models.BigIntegerField(null=True)
    vm_pgscan_direct_normal = models.BigIntegerField(null=True)
    vm_pgscan_kswapd_normal = models.BigIntegerField(null=True)
    vm_pgsteal_normal = models.BigIntegerField(null=True)
    vm_pswpin = models.BigIntegerField(null=True)
    vm_pswpout = models.BigIntegerField(null=True)
    vm_slabs_scanned = models.BigIntegerField(null=True)

    #unique_together = ("system", "acct_id")

    @property
    def runtime(self):
        """ Returns the total length of the job in seconds """
        return self.end - self.begin

    @property
    def nr_hosts(self):
        """ Returns the total number of hosts used by the job """
        return len(self.hosts.all())

    def height(self):
        """ Returns a value to scale the table row height by in html """
        return math.log(len(self.hosts.all())) * 10

    def get_owner(self):
        """ Returns a formatted version of the owner field """
        return self.owner.__str__()

    def color(self):
        """
        Returns the color of the job row as a css style field
        """
        ret_val = COLORS['Normal']
        if self.llite_open_work > 3000:
            ret_val = COLORS['High Files Open']
        elif self.mem_MemUsed > 30*2**30:
            ret_val = COLORS['High Memory Used']
        elif self.runtime > 3000:
            ret_val = COLORS['High Runtime']
        return ret_val

    def timespent(self):
        """ Returns the runtime of the job in a readable format """
        return time.strftime('%H:%M:%S', time.gmtime(self.runtime))

    def start_time(self):
        """ Returns the start time of a the job in a readable format """
        return time.ctime(self.begin)

    def host_names(self):
        """ Returns a formatted list of the hosts of a job. """
        return ', '.join([host.name for host in self.hosts.all()])

    def host_list(self):

        hosts = []
        hosts.append(host.name for host in self.hosts.all())
        return hosts

class Monitor(models.Model):
    kind = models.CharField(max_length=32)
    system = models.ForeignKey(System)

