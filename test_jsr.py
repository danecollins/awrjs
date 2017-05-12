from js.jsr import Job, Jobs, Timeline
from js.jsr import interval2string_m, elapsed2string, time2tuple, match

import unittest
import math
import time


class TestTimeFunctions(unittest.TestCase):

    def test_match(self):
        self.assertTrue(match('This is a string', "is"))
        self.assertFalse(match('This is a string', "fubar"))

    def test_elapsed2string(self):
        self.assertEqual(elapsed2string(4200),
                         u'70.0 min. / 1.17 hr.')
        self.assertEqual(elapsed2string(4200.0),
                         u'70.0 min. / 1.17 hr.')

    def test_interval2string_m(self):
        self.assertEqual(interval2string_m(60.0), "1.0")
        self.assertEqual(interval2string_m("foo"), 'NA')

    def test_time2string(self):
        x = time.mktime((2014, 1, 1, 12, 45, 0, 0, 0, 0))
        (a, b, c) = time2tuple(x)
        self.assertEqual(a, '2014-01-01')
        self.assertEqual(b, '12')
        self.assertEqual(c, 'Wednesday')

submit_msg = '2014-11-05T12:45:43.0188 - Job 1: Submitted. Name="mpiexec:3.0", \
User="dhoekstr", Priority=1'
started_msg = '2014-11-13T09:09:10.0581 - Job 254: started AXIEM:33.0, procId:0 on \
controller "dfw0awrsim01"'


class TestJobFunctions(unittest.TestCase):

    def test_parse_job_message(self):
        j = Job()
        (time, num, cmd) = j.parse_job_message(submit_msg)

        self.assertEqual(int(time), 1415220343)
        self.assertEqual(int(num), 1)
        self.assertTrue(cmd.startswith('Submitted'))

        (time, num, cmd) = j.parse_job_message(started_msg)
        self.assertEqual(int(time), 1415898550)
        self.assertEqual(int(num), 254)
        self.assertTrue(cmd.startswith('started'))

    def test_submitted(self):
        j = Job()
        j.submitted(submit_msg)
        self.assertEqual(int(j.job['submitted']), 1415220343)
        self.assertEqual(j.job['S_User'], 'dhoekstr')
        self.assertEqual(j.job['S_Priority'], '1')

    def test_started(self):
        j = Job()
        j.started(started_msg)
        self.assertEqual(j.job['queued'], 'NA')
        self.assertEqual(j.job['host'], 'dfw0awrsim01')
        j.job['submitted'] = 1415220343.0188
        j.started(started_msg)
        self.assertEqual(j.job['queued'], 678207.0392999649)


class TestAxiemLog(unittest.TestCase):

    def test_get_list(self):
        j = Jobs()
        j.read_log_file('js/tdata/axiem_success.log')
        jobs = j.get_list()
        self.assertEqual(len(jobs), 1)

    def test_number_of_events(self):
        j = Jobs()
        j.read_log_file('js/tdata/axiem_success.log')
        self.assertEqual(len(j.timeline), 4)

    def test_number_of_jobs(self):
        j = Jobs()
        j.read_log_file('js/tdata/axiem_success.log')
        self.assertEqual(j.number_of_jobs(), 1)
        j.read_log_file('js/tdata/axiem_fail.log')
        self.assertEqual(j.number_of_jobs(), 2)
        j.read_log_file('js/tdata/analyst_success.log')
        self.assertEqual(j.number_of_jobs(), 3)

    def test_jobs_with_duration(self):
        j = Jobs()
        j.read_log_file('js/tdata/axiem_success.log')
        x = j.jobs_with_duration()
        self.assertEqual(len(x), 1)
        j.read_log_file('js/tdata/axiem_fail.log')
        x = j.jobs_with_duration()
        self.assertEqual(len(x), 2)

    def test_success_job_fields(self):
        j = Jobs()
        j.read_log_file('js/tdata/axiem_success.log')
        jd = j.get_list()[0].job
        self.assertEqual(jd['R_MaxProcessors'], '0')
        self.assertEqual(jd['R_MinProcessors'], '1')
        self.assertEqual(jd['R_PreferredMemCap'], 'low')
        self.assertEqual(jd['R_ThreadsPerProcessor'], '1')
        self.assertEqual(jd['S_User'], 'dcrittenden')
        self.assertEqual(jd['host'], 'dfw0awrsim01')
        self.assertEqual(jd['exit'], '0')
        self.assertEqual(jd['S_Name'], 'AXIEM:5.0')
        self.assertEqual(jd['S_Priority'], '1')

    def test_fail_job_fields(self):
        j = Jobs()
        j.read_log_file('js/tdata/axiem_fail.log')
        jd = j.get_list()[0].job
        self.assertEqual(jd['R_MaxProcessors'], '0')
        self.assertEqual(jd['R_MinProcessors'], '1')
        self.assertEqual(jd['R_PreferredMemCap'], 'low')
        self.assertEqual(jd['R_ThreadsPerProcessor'], '1')
        self.assertEqual(jd['S_User'], 'rclark')
        self.assertEqual(jd['host'], 'dfw0awrsim02')
        self.assertEqual(jd['exit'], '-2147467259')
        self.assertEqual(jd['S_Name'], 'AXIEM:4.0')
        self.assertEqual(jd['S_Priority'], '1')

    def test_multiple_logs(self):
        j = Jobs('js/tdata/axiem_success.log')
        j.read_log_file('js/tdata/axiem_fail.log')
        j.read_log_file('js/tdata/axiem_deque.log')
        self.assertEqual(j.number_of_jobs(), 3)
        self.assertEqual(len(j.jobs_with_duration()), 2)


class TestDictOutput(unittest.TestCase):

    def test_axiem_dict(self):
        j = Jobs('js/tdata/axiem_success.log')
        d = {
            u'duration_m': 0.4,
            u'host': u'dfw0awrsim01',
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
            u'user': u'dcrittenden',
            u'wait_m': 0.18,
            u'exit': u'0',
            u'files_remaining': float('nan'),
            u'working_set': float('nan'),
            u'results_copy_m': float('nan'),
        }
        l = j.get_list()
        result = l[0].job2dict()

        for item in sorted(set(result.keys())|set(d.keys())):
            a = result.get(item, 'missing')
            b = d.get(item, 'missing')
            if not (isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b)):
                self.assertEqual(a, b, msg='Match failed on key {}, "{}" != "{}"'.format(item, a, b))

    def test_analyst_dict(self):
        j = Jobs('js/tdata/axiem_success.log')
        d = {
            u'duration_m': 0.4,
            u'host': u'dfw0awrsim01',
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
            u'user': u'dcrittenden',
            u'wait_m': 0.18,
            u'exit': "0",
            u'working_set': float('nan'),
            u'files_remaining': float('nan'),
            u'results_copy_m': float('nan'),
        }
        l = j.get_list()
        result = l[0].job2dict()

        for item in sorted(set(result.keys())|set(d.keys())):
            a = result.get(item, 'missing')
            b = d.get(item, 'missing')
            if not (isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b)):
                self.assertEqual(a, b, msg='Match failed on key {}, "{}" != "{}"'.format(item, a, b))


class TestCompleteLog(unittest.TestCase):

    def test_number_of_events(self):
        j = Jobs()
        j.read_log_file('js/tdata/combined.log')
        self.assertEqual(len(j.timeline), 583)

    def test_max_queue(self):
        j = Jobs()
        j.read_log_file('js/tdata/combined.log')
        timeline = j.timeline
        max_queue = max(x.queued_jobs for x in timeline)
        self.assertEqual(max_queue, 6)

    def test_max_running(self):
        j = Jobs()
        j.read_log_file('js/tdata/combined.log')
        timeline = j.timeline
        max_running = max(x.running_jobs for x in timeline)
        self.assertEqual(max_running, 2)

    def test_get_list(self):
        j = Jobs()
        j.read_log_file('js/tdata/combined.log')
        self.assertEqual(j.number_of_jobs(), 221)


if __name__ == '__main__':
    unittest.main()
