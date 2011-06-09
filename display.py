import human, job, numpy

# MOVEME Convert to method of Job().
# TODO Safety.
def get_schema_entry(job, type_name, key):
    schema = list(job.types[type_name].schemas.values())[0]
    return schema.keys[key]


def get_schema_keys(job, type_name):
    schema = list(job.types[type_name].schemas.values())[0]
    return [entry.key for entry in schema.entries]


def get_record_times(job): # XXX
    host_entry = list(job.hosts.values)[0]
    return host_entry.times


# Display sum.
# d_events = opts.get("d_events", True)
# d_time = opts.get("d_time", True)

def display(job, type_name, **opts):
    use_human = opts.get("human", True)
    hosts = opts.get("hosts") or job.hosts.keys()
    # Should use host/type/devs.
    devs = opts.get("devs") or job.types[type_name].devs
    schema = list(job.types[type_name].schemas.values())[0]
    if hosts:
        times = job.hosts[hosts[0]].times
    if not times:
        times = get_record_times(job)
    times = numpy.array(times, numpy.uint64) # XXX
    # XXX Make this an option `rel_time' or something.
    times -= min(host_entry.times[0] for host_entry in job.hosts.itervalues())
    nr_cols = len(schema.entries)
    nr_rows = len(times)
    stats = numpy.zeros((nr_rows, nr_cols), numpy.uint64)
    for host in hosts:
        for dev in devs:
            stats += job.hosts[host].types[type_name].stats[dev]
    for i in range(0, nr_rows):
        for j, entry in enumerate(schema.entries):
            if entry.event:
                if i < nr_rows - 1:
                    v0 = stats[i][j]
                    v1 = stats[i + 1][j]
                    stats[i][j] = (v1 - v0) / (times[i + 1] - times[i])
                else:
                    stats[i][j] = 0
    display1(schema.entries, times, stats, human=use_human)


def display1(schema_entries, times, stats, **opts):
    use_human = opts.get("human", True)
    if use_human:
        time_width = len(human.fhms(0))
        val_width = 10
    else:
        time_width = len(str(2 * 86400))
        val_width = 15
    def pr(time_str, val_strs):
        print time_str.ljust(time_width), string.join(str.rjust(val_width) for str in val_strs)
    def fmt(ent, val):
        str = human.fsize(val)
        if ent.unit:
            str += ent.unit
        if ent.event:
            str += "/s"
        return str
    row = 0
    for time, vals in zip(times, stats):
        if row % 20 == 0:
            pr('TIME', [entry.key for entry in schema_entries])
        row += 1
        if use_human:
            pr(human.fhms(time), map(fmt, schema_entries, vals)) # HMS or time.
        else:
            pr(str(time), [str(val) for val in vals])
#     keys = opts.get("keys") or get_schema_keys(job, type_name)
#     display_entries = []
#     for key in keys:
#         entry = get_schema_entry(job, type_name, key)
#         if not entry:
#             error("cannot get schema entry for type `%s', key `%s'\n", type_name, key)
#             return
#         display_entries.append(entry)

