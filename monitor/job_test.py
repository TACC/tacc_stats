import job, sge_acct, shelve

def test1(jobid='2255593'):
    with open(job.sge_acct_path) as acct_file:
        for acct in sge_acct.reader(acct_file):
            if acct['id'] == jobid:
                return job.from_acct(acct)

def test_shelve(shelf_path='/tmp/sample-jobs/jobs'):
    with shelve.open(shelf_path, protocol=-1) as shelf:
        with open(job.sge_acct_path) as acct_file:
            for acct in sge_acct.reader(acct_file):
                j = job.from_acct(acct)
                shelf[j.id] = j
