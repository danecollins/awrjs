from js.jsr import Job, Jobs, Timeline
from js.jsr import interval2string_m, elapsed2string, time2tuple, match

import math
import time
import os


def test_match():
    assert match('This is a string', "is")
    assert not match('This is a string', "fubar")


def test_elapsed2string():
    assert elapsed2string(4200) == '70.0 min. / 1.17 hr.'
    assert elapsed2string(4200.0) == '70.0 min. / 1.17 hr.'


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


# Legacy tests
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


def test_aggregate_stats():
    j = Jobs('tdata/awr_jobs_2016.txt')
    assert j.number_of_jobs() == 22
    assert j.first_job_at() == 1481566425.0794
    assert j.last_job_at() == 1481825588.0556
    assert len(j.jobs_with_duration()) == 17


# # Tests on files with one complete job #####################
def compare_dict(standard, job_dict):
    for item in sorted(set(job_dict.keys()) | set(standard.keys())):
        a = job_dict.get(item, 'key "{}" is missing from job'.format(item))
        b = standard.get(item, 'key "{}" is missing from standard'.format(item))
        if not (isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b)):
            assert a == b, 'Match failed on key {}, "{}" != "{}"'.format(item, a, b)


# ## AXIEM
def test_axiem_v11_success_dict():
    j = Jobs('tdata/axiem_success.log')
    d = {
        'duration_m': 0.4,
        'major_version': 11,
        'minor_version': '11.02.7015',
        'host': 'xyz0awrsim01',
        'max_proc': 0,
        'min_proc': 1,
        'priotiry': 1,
        'req_mem': 'low',
        'req_perf': 'low',
        'simulator': 'AXIEM',
        'start_date': '2014-10-08',
        'start_day': 'Wednesday',
        'start_time': '14',
        'submitted_date': '2014-10-08',
        'submitted_day': 'Wednesday',
        'submitted_time': '14',
        'threads': 1,
        'user': 'user1',
        'wait_m': 0.18,
        'exit': '0',
        'files_remaining': float('nan'),
        'working_set': float('nan'),
        'results_copy_m': float('nan'),
    }
    l = j.get_list()
    result = l[0].job2dict()
    compare_dict(d, result)


def test_axiem_v12_success_dict():
    assert os.path.exists('tdata/v12_xem_success.txt'), 'Test file is missing'
    j = Jobs('tdata/v12_xem_success.txt')
    d = {
        'duration_m': 0.28,
        'major_version': 12,
        'minor_version': '12.04.7721',
        'host': 'sim1a',
        'max_proc': 4,
        'min_proc': 1,
        'priotiry': 1,
        'req_mem': 'normal',
        'req_perf': 'normal',
        'simulator': 'AXIEM',
        'start_date': '2016-11-28',
        'start_day': 'Monday',
        'start_time': '08',
        'submitted_date': '2016-11-28',
        'submitted_day': 'Monday',
        'submitted_time': '08',
        'threads': 1,
        'user': 'cbean',
        'wait_m': 0.07,
        'exit': '0',
        'files_remaining': float('nan'),
        'working_set': 92,
        'results_copy_m': float('nan'),
    }
    job = j.get_list()[0]
    result = job.job2dict()
    compare_dict(d, result)

    # uuid is internal only so test it separately
    assert '{F1205AD4-0003-438F-9001-86B335F49148}' == job.job['S_UniqueID']


def test_axiem_v12_fail_dict():
    assert os.path.exists('tdata/v12_xem_fail.txt'), 'Test file is missing'
    j = Jobs('tdata/v12_xem_fail.txt')
    d = {
        'duration_m': 0.0,
        'major_version': 12,
        'minor_version': '12.01.7628',
        'host': 'awrsim1',
        'max_proc': 8,
        'min_proc': 1,
        'priotiry': 1,
        'req_mem': 'normal',
        'req_perf': 'normal',
        'simulator': 'AXIEM',
        'start_date': '2017-02-08',
        'start_day': 'Wednesday',
        'start_time': '10',
        'submitted_date': '2017-02-08',
        'submitted_day': 'Wednesday',
        'submitted_time': '10',
        'threads': 1,
        'user': 'user1',
        'wait_m': 0.03,
        'exit': '-2147467259',
        'files_remaining': float('nan'),
        'working_set': 1,
        'results_copy_m': float('nan'),
    }
    job = j.get_list()[0]
    result = job.job2dict()
    compare_dict(d, result)

    # uuid is internal only so test it separately
    assert '{10871D0D-065C-467D-838D-BFB04816B01D}' == job.job['S_UniqueID']


def test_axiem_v13_success_dict():
    assert os.path.exists('tdata/v13_xem_success.txt'), 'Test file is missing'
    j = Jobs('tdata/v13_xem_success.txt')
    d = {
        'duration_m': 0.23,
        'major_version': 13,
        'minor_version': '13.00.8271',
        'host': 'sim1a',
        'max_proc': 4,
        'min_proc': 1,
        'priotiry': 1,
        'req_mem': 'normal',
        'req_perf': 'normal',
        'simulator': 'AXIEM',
        'start_date': '2016-11-10',
        'start_day': 'Thursday',
        'start_time': '19',
        'submitted_date': '2016-11-10',
        'submitted_day': 'Thursday',
        'submitted_time': '19',
        'threads': 1,
        'user': 'John',
        'wait_m': 0.05,
        'exit': '0',
        'files_remaining': float('nan'),
        'working_set': 132,
        'results_copy_m': float('nan'),
    }
    job = j.get_list()[0]
    result = job.job2dict()
    compare_dict(d, result)

    # uuid is internal only so test it separately
    assert '{AFC35CB7-5C48-477C-BF63-723EBE869560}' == job.job['S_UniqueID']


def test_axiem_v14_success_dict():
    assert os.path.exists('tdata/v14_xem_success.txt'), 'Test file is missing'
    j = Jobs('tdata/v14_xem_success.txt')
    d = {
        'duration_m': 3.7,
        'major_version': 14,
        'minor_version': '14.00.8754',
        'host': 'local service',
        'max_proc': 8,
        'min_proc': 1,
        'priotiry': 1,
        'req_mem': 'normal',
        'req_perf': 'normal',
        'simulator': 'AXIEM',
        'start_date': '2017-05-30',
        'start_day': 'Tuesday',
        'start_time': '15',
        'submitted_date': '2017-05-30',
        'submitted_day': 'Tuesday',
        'submitted_time': '15',
        'threads': 1,
        'user': 'mshattuc',
        'wait_m': 0.02,
        'exit': '0',
        'files_remaining': float('nan'),
        'working_set': 3159,
        'results_copy_m': float('nan'),
    }
    job = j.get_list()[0]
    result = job.job2dict()
    compare_dict(d, result)

    # uuid is internal only so test it separately
    assert '{358E9E3E-0D8D-4DB4-B89B-5B0540120C6F}' == job.job['S_UniqueID']


# ## Analyst
def test_analyst_v11_dict():
    j = Jobs('tdata/axiem_success.log')
    d = {
        'duration_m': 0.4,
        'major_version': 11,
        'minor_version': '11.02.7015',
        'host': 'xyz0awrsim01',
        'max_proc': 0,
        'min_proc': 1,
        'priotiry': 1,
        'req_mem': 'low',
        'req_perf': 'low',
        'simulator': 'AXIEM',
        'start_date': '2014-10-08',
        'start_day': 'Wednesday',
        'start_time': '14',
        'submitted_date': '2014-10-08',
        'submitted_day': 'Wednesday',
        'submitted_time': '14',
        'threads': 1,
        'user': 'user1',
        'wait_m': 0.18,
        'exit': "0",
        'working_set': float('nan'),
        'files_remaining': float('nan'),
        'results_copy_m': float('nan'),
    }
    l = j.get_list()
    result = l[0].job2dict()
    compare_dict(d, result)


def test_analyst_v12_dict():
    # v12 adds working_set parameter and uuid
    assert os.path.exists('tdata/v12_ana_success.txt'), 'Test file is missing'
    j = Jobs('tdata/v12_ana_success.txt')
    d = {
        'duration_m': 31.92,
        'major_version': 12,
        'minor_version': '12.03.7688',
        'host': 'local service',
        'max_proc': 1,
        'min_proc': 1,
        'priotiry': 1,
        'req_mem': 'normal',
        'req_perf': 'normal',
        'simulator': 'Analyst',
        'start_date': '2016-04-20',
        'start_day': 'Wednesday',
        'start_time': '11',
        'submitted_date': '2016-04-20',
        'submitted_day': 'Wednesday',
        'submitted_time': '11',
        'threads': 1,
        'user': 'cbean',
        'wait_m': 0.0,
        'exit': "0",
        'working_set': 3838,
        'files_remaining': float('nan'),
        'results_copy_m': float('nan'),
    }
    job = j.get_list()[0]
    result = job.job2dict()
    compare_dict(d, result)
    assert '{40981585-0E57-4E92-9000-0379C1EBD733}' == job.job['S_UniqueID']

# def test_analyst_v13_success_dict():
#     assert os.path.exists('tdata/v13_ana_success.txt'), 'Test file is missing'
#     j = Jobs('tdata/v13_ana_success.txt')


# def test_analyst_v14_success_dict():
#     assert os.path.exists('tdata/v14_ana_success.txt'), 'Test file is missing'
#     j = Jobs('tdata/v14_ana_success.txt')


def test_analyst_v14_cancel_dict():
    assert os.path.exists('tdata/v14_ana_cancel.txt'), 'Test file is missing'
    j = Jobs('tdata/v14_ana_cancel.txt')
    d = {
        'duration_m': 0.23,
        'major_version': 14,
        'minor_version': '14.00.8732',
        'host': 'local service',
        'max_proc': 4,
        'min_proc': 1,
        'priotiry': 1,
        'req_mem': 'normal',
        'req_perf': 'normal',
        'simulator': 'Analyst',
        'start_date': '2017-05-03',
        'start_day': 'Wednesday',
        'start_time': '01',
        'submitted_date': '2017-05-03',
        'submitted_day': 'Wednesday',
        'submitted_time': '01',
        'threads': 1,
        'user': 'sylin',
        'wait_m': 0.02,
        'exit': "cancelled",
        'working_set': 351,
        'files_remaining': float('nan'),
        'results_copy_m': float('nan'),
    }
    job = j.get_list()[0]
    result = job.job2dict()
    compare_dict(d, result)
    assert '{9E0BDFC8-D442-46D4-BC94-380BFEDF0432}' == job.job['S_UniqueID']


# ## 3rd Party Simulator
def test_sonnet_v13_success_dict():
    assert os.path.exists('tdata/v13_sonnet_success.txt'), 'Test file is missing'
    j = Jobs('tdata/v13_sonnet_success.txt')
    d = {
        'duration_m': 0.0,
        'major_version': 13,
        'minor_version': '13.00.8316',
        'host': 'sim01',
        'max_proc': 1,
        'min_proc': 1,
        'priotiry': 1,
        'req_mem': 'normal',
        'req_perf': 'normal',
        'simulator': 'EM_3rd_Party',
        'start_date': '2017-03-06',
        'start_day': 'Monday',
        'start_time': '11',
        'submitted_date': '2017-03-06',
        'submitted_day': 'Monday',
        'submitted_time': '11',
        'threads': 1,
        'user': 'user0',
        'wait_m': 0.03,
        'exit': '0',
        'files_remaining': float('nan'),
        'working_set': 0,
        'results_copy_m': float('nan'),
    }
    job = j.get_list()[0]
    result = job.job2dict()
    compare_dict(d, result)

    # uuid is internal only so test it separately
    assert '{0EA2FBAB-29A1-47CA-A437-847B89492E03}' == job.job['S_UniqueID']


# ## 3rd Party Simulator
def test_working_set_in_kb():
    assert os.path.exists('tdata/v13_working_set_kb.txt'), 'Test file is missing'
    j = Jobs('tdata/v13_working_set_kb.txt')
    d = {
        'duration_m': 0.0,
        'major_version': 13,
        'minor_version': '13.00.8316',
        'host': 'sim01',
        'max_proc': 1,
        'min_proc': 1,
        'priotiry': 1,
        'req_mem': 'normal',
        'req_perf': 'normal',
        'simulator': 'EM_3rd_Party',
        'start_date': '2017-03-06',
        'start_day': 'Monday',
        'start_time': '11',
        'submitted_date': '2017-03-06',
        'submitted_day': 'Monday',
        'submitted_time': '11',
        'threads': 1,
        'user': 'user0',
        'wait_m': 0.03,
        'exit': '0',
        'files_remaining': float('nan'),
        'working_set': 0,
        'results_copy_m': float('nan'),
    }
    job = j.get_list()[0]
    result = job.job2dict()  # note this round working set to an int.
    assert result['working_set'] == 1, "failed: {}".format(result)


