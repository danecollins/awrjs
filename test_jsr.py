from js.jsr import Job, Jobs, Timeline
from js.jsr import interval2string_m, elapsed2string, time2tuple, match

import math
import time


def test_match():
    assert match('This is a string', "is")
    assert not match('This is a string', "fubar")


def test_elapsed2string():
    assert elapsed2string(4200) == u'70.0 min. / 1.17 hr.'
    assert elapsed2string(4200.0) == u'70.0 min. / 1.17 hr.'


def test_interval2string_m():
    assert interval2string_m(60.0) == "1.0"
    assert interval2string_m("foo") == 'NA'


def test_time2string():
    x = time.mktime((2014, 1, 1, 12, 45, 0, 0, 0, 0))
    (a, b, c) = time2tuple(x)
    assert a == '2014-01-01'
    assert b == '12'
    assert c == 'Wednesday'

submit_msg = '2014-11-05T12:45:43.0188 - Job 1: Submitted. Name="mpiexec:3.0", \
User="dhoekstr", Priority=1'
started_msg = '2014-11-13T09:09:10.0581 - Job 254: started AXIEM:33.0, procId:0 on \
controller "dfw0awrsim01"'


def test_parse_job_message():
    j = Job()
    (time, num, cmd) = j.parse_job_message(submit_msg)

    assert int(time) == 1415220343
    assert int(num) == 1
    assert cmd.startswith('Submitted')

    (time, num, cmd) = j.parse_job_message(started_msg)
    assert int(time) == 1415898550
    assert int(num) == 254
    assert cmd.startswith('started')


def test_submitted():
    j = Job()
    j.submitted(submit_msg)
    assert int(j.job['submitted']) == 1415220343
    assert j.job['S_User'] == 'dhoekstr'
    assert j.job['S_Priority'] == '1'


def test_started():
    j = Job()
    j.started(started_msg)
    assert j.job['queued'] == 'NA'
    assert j.job['host'] == 'dfw0awrsim01'
    j.job['submitted'] = 1415220343.0188
    j.started(started_msg)
    assert j.job['queued'] == 678207.0392999649


def test_get_list():
    j = Jobs()
    j.read_log_file('tdata/axiem_success.log')
    jobs = j.get_list()
    assert len(jobs) == 1


def test_number_of_events():
    j = Jobs()
    j.read_log_file('tdata/axiem_success.log')
    assert len(j.timeline), 4


def test_number_of_jobs():
    j = Jobs()
    j.read_log_file('tdata/axiem_success.log')
    assert j.number_of_jobs() == 1
    j.read_log_file('tdata/axiem_fail.log')
    assert j.number_of_jobs() == 2
    j.read_log_file('tdata/analyst_success.log')
    assert j.number_of_jobs() == 3


def test_jobs_with_duration():
    j = Jobs()
    j.read_log_file('tdata/axiem_success.log')
    x = j.jobs_with_duration()
    assert len(x) == 1
    j.read_log_file('tdata/axiem_fail.log')
    x = j.jobs_with_duration()
    assert len(x) == 2


def test_success_job_fields():
    j = Jobs()
    j.read_log_file('tdata/axiem_success.log')
    jd = j.get_list()[0].job
    assert jd['R_MaxProcessors'] == '0'
    assert jd['R_MinProcessors'] == '1'
    assert jd['R_PreferredMemCap'] == 'low'
    assert jd['R_ThreadsPerProcessor'] == '1'
    assert jd['S_User'] == 'user1'
    assert jd['host'] == 'xyz0awrsim01'
    assert jd['exit'] == '0'
    assert jd['S_Name'] == 'AXIEM:5.0'
    assert jd['S_Priority'] == '1'


def test_fail_job_fields():
    j = Jobs()
    j.read_log_file('tdata/axiem_fail.log')
    jd = j.get_list()[0].job
    assert jd['R_MaxProcessors'] == '0'
    assert jd['R_MinProcessors'] == '1'
    assert jd['R_PreferredMemCap'] == 'low'
    assert jd['R_ThreadsPerProcessor'] == '1'
    assert jd['S_User'] == 'user4'
    assert jd['host'] == 'xyz0awrsim02'
    assert jd['exit'] == '-2147467259'
    assert jd['S_Name'] == 'AXIEM:4.0'
    assert jd['S_Priority'] == '1'


def test_multiple_logs():
    j = Jobs('tdata/axiem_success.log')
    j.read_log_file('tdata/axiem_fail.log')
    j.read_log_file('tdata/axiem_deque.log')
    assert j.number_of_jobs() == 3
    assert len(j.jobs_with_duration()) == 2


def test_axiem_dict():
    j = Jobs('tdata/axiem_success.log')
    d = {
        u'duration_m': 0.4,
        u'host': u'xyz0awrsim01',
        u'max_proc': 0,
        u'min_proc': 1,
        u'priotiry': 1,
        u'req_mem': u'low',
        u'req_perf': u'low',
        u'simulator': u'AXIEM',
        u'start_date': '2014-10-08',
        u'start_day': 'Wednesday',
        u'start_time': '14',
        u'submitted_date': '2014-10-08',
        u'submitted_day': 'Wednesday',
        u'submitted_time': '14',
        u'threads': 1,
        u'user': u'user1',
        u'wait_m': 0.18,
        u'exit': u'0',
        u'files_remaining': float('nan'),
        u'working_set': float('nan'),
        u'results_copy_m': float('nan'),
    }
    l = j.get_list()
    result = l[0].job2dict()

    for item in sorted(set(result.keys()) | set(d.keys())):
        a = result.get(item, 'missing')
        b = d.get(item, 'missing')
        if not (isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b)):
            assert a == b, 'Match failed on key {}, "{}" != "{}"'.format(item, a, b)


def test_analyst_dict():
    j = Jobs('tdata/axiem_success.log')
    d = {
        u'duration_m': 0.4,
        u'host': u'xyz0awrsim01',
        u'max_proc': 0,
        u'min_proc': 1,
        u'priotiry': 1,
        u'req_mem': u'low',
        u'req_perf': u'low',
        u'simulator': u'AXIEM',
        u'start_date': '2014-10-08',
        u'start_day': 'Wednesday',
        u'start_time': '14',
        u'submitted_date': '2014-10-08',
        u'submitted_day': 'Wednesday',
        u'submitted_time': '14',
        u'threads': 1,
        u'user': u'user1',
        u'wait_m': 0.18,
        u'exit': "0",
        u'working_set': float('nan'),
        u'files_remaining': float('nan'),
        u'results_copy_m': float('nan'),
    }
    l = j.get_list()
    result = l[0].job2dict()

    for item in sorted(set(result.keys()) | set(d.keys())):
        a = result.get(item, 'missing')
        b = d.get(item, 'missing')
        if not (isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b)):
            assert a == b, 'Match failed on key {}, "{}" != "{}"'.format(item, a, b)


def test_aggregate_stats():
    j = Jobs('tdata/awr_jobs_2016.txt')
    assert j.number_of_jobs() == 22
    assert j.first_job_at() == 1481566425.0794
    assert j.last_job_at() == 1481825588.0556
    assert len(j.jobs_with_duration()) == 17
