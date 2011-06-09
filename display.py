import numpy, human

# MOVEME Convert to method of Job().
# TODO Safety.
def get_schema_entry(job, type_name, key):
    schema = list(job.types[type_name].schemas.values())[0]
    return schema.keys[key]

def get_schema_keys(job, type_name):
    schema = list(job.types[type_name].schemas.values())[0]
    return [entry.key for entry in schema.entries]


# TODO Allow filtering by host.
# TODO Allow filtering by dev.
# numpy for array

aggr_type_code = numpy.uint64

def aggregate(job, type_name, **opts):
    t_step = opts.get("step", 600)
    # TODO Check for ents before keys.
    keys = opts.get("keys") or get_schema_keys(job, type_name)
    key_indices = []
    for key in keys:
        ent = get_schema_entry(job, type_name, key)
        if not ent:
            error("cannot get schema entry for type `%s', key `%s'\n", type_name, key)
            return
        key_indices.append(ent.index)
    nr_cols = len(key_indices)
    t_max = max(host_entry.records[-1].time for host_entry in job.hosts.values())
    nr_rows = (t_max / t_step) + 1
    t_end = nr_rows * t_step
    aggr = numpy.zeros((nr_rows, nr_cols), aggr_type_code)
    for host_entry in job.hosts.itervalues():
        r = t = 0
        rec = host_entry.records[0]
        curr = numpy.zeros((nr_cols,), aggr_type_code)
        for stats in rec.types[type_name].itervalues():
            for j, k in enumerate(key_indices):
                curr[j] += stats[k]
        # trace("rec_time %d, rec_vals %s\n", rec.time, rec_vals)
        for next_rec in host_entry.records:
            while t < next_rec.time:
                aggr[r] += curr
                r += 1
                t += t_step
            rec = next_rec
            curr = numpy.zeros((nr_cols,), aggr_type_code)
            for stats in rec.types[type_name].itervalues():
                for j, k in enumerate(key_indices):
                    curr[j] += stats[k]
            # trace("rec_time %d, rec_vals %s\n", rec.time, rec_vals)
        while t < t_end:
            aggr[r] += curr
            r += 1
            t += t_step
    return aggr


def display(job, type_name, **opts):
    d_events = opts.get("d_events", True)
    d_time = opts.get("d_time", True)
    # header
    # host = opts.get("host")
    # dev = opts.get("dev")
    human = opts.get("human", True)
    # TODO Check for ents.
    keys = opts.get("keys") or get_schema_keys(job, type_name)
    t_step = opts.get("step", 600)
    key_entries = []
    for key in keys:
        entry = get_schema_entry(job, type_name, key)
        if not entry:
            error("cannot get schema entry for type `%s', key `%s'\n", type_name, key)
            return
        key_entries.append(entry)
    # TODO Pass ents, host, dev.
    aggr = aggregate(job, type_name, keys=keys, step=t_step)
    # Horrible.
    time_width = 10
    col_width = max(8, 80 / (len(key_entries) + 1))
    print "time".ljust(time_width),
    for entry in key_entries:
        print entry.key.rjust(col_width),
    print
    nr_rows = len(aggr)
    for r in range(0, nr_rows - 1):
        print human.fhms(r * t_step).ljust(time_width),
        for i, entry in enumerate(key_entries):
            if entry.event:
                v0 = aggr[r][i]
                v1 = aggr[r + 1][i]
                v = (v1 - v0) / t_step
            else:
                v = aggr[r][i]
            s = human.fsize(v)
            if entry.unit:
                s += entry.unit
            if entry.event:
                s += "/s"
            print s.rjust(col_width),
        print
    # TODO Last row.
