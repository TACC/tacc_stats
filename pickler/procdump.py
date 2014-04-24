#!/usr/bin/python
import gzip
import sys
import base64
import StringIO
import re

class ProcDump:
    def __init__(self):
        self.uidprocs= dict()
        
        self.knownprocesses = set(['wnck-applet',
            'wc', 'which', 'vncserver', 'vncconfig', 'vim', 'vi', 'usleep', 'uname',
            'uniq', 'tr', 'top', 'time', 'tee', 'tail', 'sync-to-pcp1',
            'sync-pcp-logs', 'sshd:', 'sshd', 'sort', 'ssh', 'srun', 'sh', 'squeue',
            'slurmstepd:', 'slurmstepd', 'slurm_script', 'sleep', 'sinfo', 'sed',
            'screen', 'scontrol', 'sbcast', 'rsync', 'pulseaudio',
            'pulse/gconf-helper', 'ps', 'pmi_proxy', 'nrpe', 'nedit',
            'notification-area-applet', 'nautilus', 'mv', 'more', 'mktemp', 'mkdir',
            'ln', 'ldd', 'lsof', 'hostname', 'gzip', 'gvfsd-trash', 'gvfsd-metadata',
            'gvfsd-http', 'gvfsd-computer', 'gvfsd', 'gvfs-gdu-volume-monitor', 'grep',
            'gnome-terminal', 'gnome-settings-daemon', 'gnome-session',
            'gnome-pty-helper', 'gnome-panel', 'gnome-keyring-daemon', 'gedit',
            'gdm-user-switch-applet', 'gconfd-2', 'gawk', 'fgrep', 'emacs', 'echo',
            'dmtcp_restart_s', 'dmtcp_restart', 'dmtcp_checkpoint',
            'dmtcp_coordinator', 'dmtcp_coordinat', 'dmtcp_command', 'dmesg', 'df',
            'dbus-launch', 'dbus-daemon', 'cut', 'crond', 'cp', 'csh', 'cd',
            'clock-applet', 'cat', 'bash', 'bonobo-activation-server', 'awk', 'SCREEN',
            'CROND', '/usr/lib64/nagios/plugins/check_procs', '/etc/vnc/Xvnc-core'])
        
        self.procfilter = re.compile('^/user/[a-z0-9]+/\.vnc/xstartup|^/var\/spool\/slurmd.+|.*pmi_proxy$')

    def __str__(self):
        return str(self.getproclist())

    def getproclist(self, uid=None):
        if uid != None:
            if uid in self.uidprocs:
                return list(self.uidprocs[uid])

        allprocs = set()
        for procs in self.uidprocs.itervalues():
            allprocs.update(procs)

        return list(allprocs)

    def strippath(self, command):
        paths = ['/bin/', '/sbin/', '/usr/bin/', '/usr/sbin/', '/usr/libexec/', '/usr/local/bin/', '-' ]
        for path in paths:
            if command.startswith(path):
                return command[len(path):].strip('";')
        return command
    
    def getcommand(self, procname):
        shells = ["sh", "csh", "tcsh", "bash", "perl", "python"]
    
        cmdline = procname.split(" ")
        command = self.strippath(cmdline[0])
    
        if command in shells:
            command = None
            for s in cmdline[1:]:
                if not s.startswith("-"):
                    command = self.strippath(s)
                    break
        return command
    
    def blacklisted(self, commandline):
        command = self.getcommand(commandline)
        if command == None:
            return True
        if command in self.knownprocesses:
            return True
        if self.procfilter.search(command):
            return True
    
        return False

    def parse(self,indata):

        if len(indata) < 40:
            return

        decoded = StringIO.StringIO(base64.b64decode(indata[11:]))
        gzo = gzip.GzipFile(mode="rb",fileobj=decoded)

        (START, STATUS_LEN, STATUS_NAME, UIDSEARCH, CMDLINE_LEN, CMDLINE_NAME) = range(6)

        state = START
        pid = -1
        uidpids = dict()
        processes = dict()

        for line in gzo:
            if state == START:
                if "/status" in line:
                    m = re.search("^/proc/([0-9]+)/status", line)
                    if m:
                        pid = m.group(1)
                        state = STATUS_LEN
                        continue
                if "/cmdline" in line:
                    m = re.search("^/proc/([0-9]+)/cmdline", line)
                    if m:
                        pid = m.group(1)
                        state = CMDLINE_LEN
                continue
            if state == STATUS_LEN:
                state = STATUS_NAME
                continue
            if state == STATUS_NAME:
                if pid not in processes:
                    processes[pid] = line.split()[1]
                state = UIDSEARCH
                continue
            if state == UIDSEARCH:
                if line.startswith("Uid:"):
                    m = re.search("^Uid:\t+([0-9]+).*", line)
                    if m:
                        uid = m.group(1)
                        if uid not in uidpids:
                            uidpids[uid] = set()
                        uidpids[uid].add(pid)
                    state = START
                continue
            if state == CMDLINE_LEN:
                state = CMDLINE_NAME
                continue
            if state == CMDLINE_NAME:
                processes[pid] = line.replace("\0", " ").rstrip()
                state = START
                continue

        # post process
        for uid,pids in uidpids.iteritems():
            tmp = set()
            for pid in pids:
                procname = processes[pid]
                if not self.blacklisted(procname):
                    tmp.add(procname)

            if len(tmp) > 0:
                self.uidprocs[uid] = tmp

""" This helper function is a bare-bones parser to easily extract the """
""" procDump information from a raw taccstats output file. """

def getProcdumpData( filename, jid ):

    procParser = ProcDump()
    lineNum = 0
    cmd = ""
    procDumpData = []
    running = False
    ending = False
    procDumpLines = []
    try:
        with gzip.open(filename) as f:
            for line in f:
                # store line number
                lineNum += 1
                # test if its already running
                if line[0].isdigit():
                    jobs=line.strip().split()[1].split(',')
                    if jid in jobs:
                        running = True
                # test if it is starting
                if line.startswith("% begin"):
                    if line.strip().split()[2] == jid:
                        running = True
                # test if it is ending
                if line.startswith("% end"):
                    if line.strip().split()[2] == jid:
                        ending = True
                # test if its a procdump line and job is running
                if line.startswith("% procdump") and (running or ending):
                    procParser.parse(line)
                    if ending:
                        break
    except TypeError as e:
        print e
        pass
    
    return procParser

if __name__ == '__main__':
    print getProcdumpData( sys.argv[1], sys.argv[2] )

