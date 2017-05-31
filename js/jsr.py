# [SublimeLinter flake8-max-line-length:120 flake8-max-complexity:10]
"""
Library to read in the log files produced by the AWR job scheduler

  - log file will usually be named AWR_JobScheduler_x64_log.txt

Usage:
  This was originally written to be used as a script but is being migrated
  to be an iPython library so that the analysis can be customized by users
  more easily.

This is very much a work-in-progress.  For additional information or
enhancement requests contact dane@awr.com
"""

from typing import List, Union, Dict, Tuple, IO

# standard imports
import codecs
import re
import time
from collections import defaultdict
from collections import Counter
from datetime import datetime
import sys


# Set to a port to generate debug information during run
debug_port = None  # type: IO[str]

running_hosts = {}  # type: Dict


def dprint(*args) -> None:

    global debug_port
    if debug_port:
        print(*args, file=debug_port)


# ###################################################################### Utility Parsing Functions
def match(s: str, substring: str) -> bool:
    """Return True if substring in str"""

    return s.find(substring) != -1


def elapsed2string(tm: Union[int, float, str]) -> str:
    """Return elapsed time as friendly string representation

        Arguments:
        :param tm: (float|str): is a number of seconds
        :return str: A string with the number of minutes and hours represented
    """

    if isinstance(tm, str) and (tm.isdigit() is False):
        return 'illegal time str <{}>'.format(tm)  # can't convert
    else:
        ftm = float(tm)  # in case tm is an int
    return "{} min. / {} hr.".format(round(ftm / 60, 1), round(ftm / 3600, 2))


def interval2float_m(i: float) -> float:
    """Convert a time interval to a float or to NA if it is does not have a value

        Arguments:
            i: is a number of seconds

        Returns:
            the number of minutes represented or NA if i is not a float
    """
    if isinstance(i, float):
        return round(i / 60.0, 2)
    else:
        return float('nan')


def interval2string_m(i: float) -> str:
    """Convert a time interval to a string or to NA if it is does not have a value

        Arguments:
            i: is a number of seconds

        Returns:
            a string of the number of minutes represented or NA if i is not a float
    """
    if type(i) == float:
        i_m = str(round(i / 60.0, 2))
    else:
        i_m = 'NA'
    return i_m


def time2tuple(tm: float) -> Tuple[str, str, str]:
    """ Convert a time string into separate date, time and day-of-week

        Arguments:
            tm: is a datetime floating point value from mktime()

        Returns:
            a tuple of date as YYYY-mm-dd, hour as string, day of week as string
    """
    if tm != '':
        tml = time.localtime(tm)
        tm_date = time.strftime("%Y-%m-%d", tml)
        tm_time = time.strftime("%H", tml)
        tm_dow = time.strftime("%A", tml)
    else:
        tm_date = 'NA'
        tm_time = 'NA'
        tm_dow = 'NA'
    return tm_date, tm_time, tm_dow


def float_to_date(f: float) -> str:
    if isinstance(f, float):
        return time.strftime('%y%m%d %H:%M:%S', time.localtime(f))
    else:
        return ''


def timestamp2float(ts: str) -> float:
    """ Converts a timestamp of the form 2016-03-10T04:15:02.0036 into a time float

        Arguments:
            ts: timestamp string

        Returns:
            floating point time from mktime with microseconds added to it.

    """
    (time_stamp, fractseconds) = ts.split('.')
    if len(time_stamp) != 19:
        time_stamp = time_stamp[1:]  # hack because of utf char added by cat!

    msgtm = time.strptime(time_stamp, "%Y-%m-%dT%H:%M:%S")
    float_time = time.mktime(msgtm)
    float_time += float(fractseconds) / 10000
    return float_time


def to_int_or_na(i):
    """Convert string to int"""
    if isinstance(i, float):
        return int(round(i, 0))
    try:
        return int(i)
    except ValueError:
        return float('nan')


# ######################################################################################## TIMELINE
class Timeline(list):
    running_jobs = 0
    queued_jobs = 0
    next_id = 0
    """
    Keeps a list of events along with the running list of the queued and running jobs

    Outputs:
        Timeline events can be written out in different formats depending on what the goal is.

    Methods
        queue_input
            this format writes jobs out in a format that could be used to replicate the job
            submission behavior.  this will write out job submits with an incremental time
            stamp and the job information required to determine the job to be run.

        user_input
            this format write the queue_input information but adds in other user input such as
            job cancellations and job queue restarts/shutdowns
    """
    def add_event(self, event):
        """
        Adds an event to the event list

        Args:
            event: event object

        Returns: nothing

        """
        cls = type(self)
        id = cls.next_id
        cls.next_id += 1

        if event.ev_type == 'queued':
            cls.queued_jobs += 1
            event.queued_jobs = cls.queued_jobs
            event.running_jobs = cls.running_jobs
        elif event.ev_type == 'cancelled':
            cls.queued_jobs -= 1
            event.queued_jobs = cls.queued_jobs
            event.running_jobs = cls.running_jobs
        elif event.ev_type == 'started':
            cls.queued_jobs -= 1
            cls.running_jobs += 1
            event.running_jobs = cls.running_jobs
            event.queued_jobs = cls.queued_jobs
        elif event.ev_type == 'ended' or event.ev_type == 'terminated':
            cls.running_jobs -= 1
            event.running_jobs = cls.running_jobs
            event.queued_jobs = cls.queued_jobs
        elif event.ev_type == 'shutdown':
            cls.queued_jobs = 0
            cls.running_jobs = 0
            event.running_jobs = cls.running_jobs
            event.queued_jobs = cls.queued_jobs
        elif event.ev_type == 'vanished':
            cls.running_jobs -= 1
            event.queued_jobs = cls.queued_jobs
            event.running_jobs = cls.running_jobs
        else:
            print('Unknown evert type {}'.format(event.ev_type))
            assert False

        event.seq = id
        self.append(event)

    def shutdown(self, tm):
        """
        Jobs that are pending when the scheduler are shutdown need to be handled
        If the run is running, leave it alone and it should re-connect
        If it is in the queue, cancel it, I think
        Args:
            tm: timestamp of when showdown is happening
            job: job that is pending

        Returns: none
        """
        self.add_event(Event(tm, 'shutdown', None))
        return True

    def write_queue_input(self, fp=sys.stdout):
        start_time = False
        for ev in self:
            if ev.ev_type == 'queued':  # job submitted
                # need to wait until we get a queue event (as opposed to shutdown) to get start time
                if not start_time:
                    start_time = ev.job['submitted']  # this is considered t0
                print(ev.queue_input_fmt(start_time), file=fp)

    def write(self, fp=sys.stdout):
        print('date,time,type,running,queued,id', file=fp)
        for ev in self:
            s = '20{},{},{},{},{}'.format(float_to_date(ev.tm), ev.tm, ev.ev_type, ev.running_jobs, ev.queued_jobs)
            if ev.job:
                s += "," + ev.job['id']
            else:
                s += ',NA'
            print(s, file=fp)


class Event:
    """
    Stores one event change in the scheduler status

    Members:
        tm: event time as a floating point number (seconds.microseconds)
        ev_type: type of event, [queued, cancelled, started, ended]
        job: job object
    """
    def __init__(self, tm, ev_type, job):
        self.tm = tm
        self.ev_type = ev_type
        self.job = job
        self.seq = 0

        # these will get set if the object is added to a timeline
        self.running_jobs = None
        self.queued_jobs = None

    def __str__(self):
        job_id = self.job['id'] if self.job else 'none'
        return 'Event({}, Q={}, R={}, {} {}, {})'.format(float_to_date(self.tm),
                                                     self.queued_jobs or 0, self.running_jobs or 0,
                                                     job_id, self.ev_type, self.seq)

    def queue_input_fmt(self, start_time):
        """
        Generate a string output for the queue input file

        Returns: (str) of event
        """
        job = self.job

        start = job['submitted'] - start_time  # offset start time to t0
        (sim, _) = job['S_Name'].split(':')
        s = "At {:10.2f} sec. started {} job with these attributes:\n".format(start, sim)
        if job['duration']:
            s += "    A duration of {:.0f} sec.\n".format(job['duration'])
            if job['working_set']:  # working set only on v12 jobs
                s += "    Requiring {:.0f} Mb of memory\n".format(job['working_set'])
        else:
            s += '    Job did not finish\n'
        s += "    Requesting {}-{} processors\n".format(job['R_MinProcessors'], job['R_MaxProcessors'])

        return s


# ############################################################################################ JOBS
class Jobs:
    """
    Stores a list of all jobs read in and computes statistics on them

    Operations on a list of jobs
        All jobs are stored as a list and this class provides the interface to
        that list

        The stat functions compute data and return it as a dict as well as in a
        formatted string which is ready to print.
        This allows the caller to format the data or to just the pre-formatted
        format.

    Attributes
        joblist - this is a list of job objects
        files   - this is a list of the names of the files that have been read
    """
    last_version_line = False

    def __init__(self, load=None):
        self.joblist = list()
        self.files = list()
        self.starts = list()
        self.timeline = Timeline()
        if load:
            self.read_log_file(load)

    def read_log_file(self, filename):
        """
        Parse through the logfile and create the joblist

        To make it easier to detect changes in the log file format, if branches
        are added for all Job # messages even if they are not processed.  By
        turning on debug_port we can see all the lines in the log that are
        ignored.
        """
        c = Counter()
        self.files.append(filename)
        with codecs.open(filename, encoding='utf-8') as fp:

            jobre = re.compile('- Job \d\d*:')
            re_restore_job = re.compile('- Job \d\d* ')
            dequere = re.compile('job number \d\d* ')
            terminating = re.compile('job number \d\d* ')

            for lineno, line in enumerate(fp.readlines()):
                lineno += 1  # enumerate 0 based, line numbers 1 based
                if (lineno % 100000) == 0:
                    print(lineno)
                line = line.rstrip()
                if not line:
                    continue
                line = line[1:] if line[0] == '\ufeff' else line
                j = None
# ##################################################################################### LOG PARSING
                # Identify the type of line and dispatch to right parsing function
                if match(line, 'Found version'):
                    j = Job()
                    j.jl = self
                    j.found(line)
                    self.add(j)
                elif match(line, 'Submitted.'):
                    job_number = jobre.search(line).group()[6:-1]  # del  -Job and :
                    j = self.__find_by_number(job_number, lineno)
                    j.submitted(line)
                    if Jobs.last_version_line:
                        j.job['version'] = Jobs.last_version_line
                        Jobs.last_version_line = False
                    c['jobs'] += 1
                elif match(line, 'restored. UniqueID'):  # Job 1 restored. UniqueID={828BDD14-...-ACDCCF69756A}
                    # need to reconnect a job number to a job.
                    # print(line)
                    job_number = re_restore_job.search(line).group()[6:-1]
                    uuid = line[line.find('=') + 1:-1]
                    self.set_jobno_from_uuid(uuid, job_number, lineno)
                elif match(line, 'Creating Process'):
                    job_number = jobre.search(line).group()[6:-1]  # del  -Job and :
                    j = self.__find_by_number(job_number, lineno)
                    j.creating(line)
                elif match(line, 'on controller'):
                    job_number = jobre.search(line).group()[6:-1]  # del  -Job and :
                    j = self.__find_by_number(job_number, lineno)
                    j.started(line)
                elif match(line, 'releasing'):
                    job_number = jobre.search(line).group()[6:-1]  # del  -Job and :
                    j = self.__find_by_number(job_number, lineno)
                    j.releasing(line)
                elif match(line, 'Job Scheduler shutting down'):  # Job Scheduler shutting down with exit code 0x00000000
                    dprint('DEBUG: restarting scheduler on line {}'.format(lineno))
                    self.restart_scheduler(line, shutdown=True)
                elif match(line, 'Processing Command Line'):
                    dprint('DEBUG: restarting scheduler on line {}'.format(lineno))
                    self.restart_scheduler(line)
                elif match(line, 'MaxProcessors'):
                    job_number = jobre.search(line).group()[6:-1]  # del  -Job and :
                    j = self.__find_by_number(job_number, lineno)
                    j.request_info(line)
                elif match(line, 'peak working set ='):  # could be peak working set not reported so = needed
                    job_number = jobre.search(line).group()[6:-1]
                    j = self.__find_by_number(job_number, lineno)
                    j.working_set(line)
                elif match(line, 'Exit status'):
                    job_number = jobre.search(line).group()[6:-1]  # del  -Job and :
                    j = self.__find_by_number(job_number, lineno)
                    j.exit_status(line)
                elif match(line, 'exit code '):  # this will also match scheduler shutdown, must come after
                    job_number = jobre.search(line).group()[6:-1]  # del  -Job and :
                    j = self.__find_by_number(job_number, lineno)
                    j.exit_code(line)
                elif match(line, 'Dequeueing job'):
                    job_number = dequere.search(line).group()[11:-1]
                    j = self.__find_by_number(job_number, lineno)
                    j.cancelled(line)
                elif match(line, 'Dequeueing scheduled job'):  # v12 dequeue different from v11
                    job_number = jobre.search(line).group()[6:-1]  # del  -Job and :
                    j = self.__find_by_number(job_number, lineno)
                    j.cancelled(line)
                elif match(line, 'Setting job to CANCELING state'):
                    job_number = jobre.search(line).group()[6:-1]
                    j = self.__find_by_number(job_number, lineno)
                    j.cancelled(line)
                elif match(line, 'Terminating job'):  # 2016-....0468 - Terminating job number 26 (mpiexec:2.2)
                    job_number = terminating.search(line).group()[11:-1]
                    j = self.__find_by_number(job_number, lineno)
                    j.terminated(line)
                elif match(line, 'Output Files remaining:'):
                    job_number = jobre.search(line).group()[6:-1]  # del  -Job and :
                    j = self.__find_by_number(job_number, lineno)
                    if line[-2:] == ' 0':
                        # if this is the last file then copying back of results is done
                        j.copy_back_end(line)
                    else:
                        j.copy_back_start(line)
                elif match(line, 'Registering Task token') or match(line, 'Registering task id'):
                    # we don't need to track these for now
                    pass
                elif match(line, 'Child Process'):
                    # child process exit messages, we don't need these
                    pass
                elif match(line, 'assigned'):
                    # 2016-01-20T19:08:31.0676 - Job 46: assigned AXIEM:3.0 to controller "dfw0awrsim01"
                    # this is the beginning of the input file copy process but also a good place to check
                    # that last job on this machine is done.
                    job_number = jobre.search(line).group()[6:-1]  # del  -Job and :
                    j = self.__find_by_number(job_number, lineno)
                    j.assigned(line)
                elif match(line, 'Requesting input file') or\
                        match(line, 'Preparing to wait for transfer of input file') or\
                        match(line, 'Transfer complete for outgoing input file') or\
                        match(line, 'Transfer complete for all input files') or\
                        match(line, 'File requested by remote queue') or\
                        match(line, 'Transfer complete for input file'):
                    # we don't track file copying
                    pass
                elif match(line, 'Transfer complete for output file') or\
                        match(line, 'Preparing to wait for transfer of output file') or\
                        match(line, 'Requesting output file'):
                    # we don't track file copying
                    pass
                elif match(line, 'Responded to ping from') or match(line, 'has disconnected'):
                    pass
                elif match(line, 'Starting Job Scheduler'):
                    # job scheduler is starting
                    (tm, rest) = line.split(' - ', 1)
                    (time_stamp, fractseconds) = tm.split('.')
                    self.starts.append((time_stamp, rest[len(' Starting Job Scheduler '):]))
                elif match(line, 'Output Files remaining'):
                    job_number = jobre.search(line).group()[6:-1]
                    j = self.__find_by_number(job_number, lineno)
                    j.files_remaining(line)
                else:
                    dprint('unmatched line:', line)
                if j:
                    j.lines.append(line)

        # at end of every file close out all open jobs
        self.restart_scheduler(line)  # don't really have a choice but to use last line for time stamp
        return c['jobs']

    def add(self, job):
        """ Add a job object to the master list"""
        self.joblist.append(job)

    def get_list(self):
        return self.joblist

    def set_jobno_from_uuid(self, uuid, jobno, lineno):
        jobs_matching_uuid = [x for x in self.joblist if x.job['S_UniqueID'] == uuid]
        if len(jobs_matching_uuid) == 1:
            job = jobs_matching_uuid[0].job
            job['number'] = jobno
            job['exit'] = 'restored'
            return True
        else:
            if jobs_matching_uuid:
                print('ERROR: {} jobs matched uuid, should only be 1'.format(len(jobs_matching_uuid)))
                for j in jobs_matching_uuid:
                    print(j)
            else:
                print('ERROR: Could not find job matching uuid {}'.format(uuid))
                print('       error occured on line {}'.format(lineno))
            return False

    def __find_by_number(self, n, lineno):
        """ Returns the job that matches based on the number n"""
        jobs_matching_number = [x for x in self.joblist if x.job['number'] == n]
        num_jobs_found = len(jobs_matching_number)
        if num_jobs_found == 0:
            print('ERROR: Could not find job with number {}'.format(n))
            print('       error occured processing line {}'.format(lineno))
            # print(self.joblist)
        elif num_jobs_found > 1:
            print('ERROR: jobs_matching_number {} jobs with number {}'.format(num_jobs_found, n))
            assert len(jobs_matching_number) < 2
        else:
            return jobs_matching_number[0]

    def restart_scheduler(self, line, shutdown=False):
        """
        When the scheduler is restarted it will start reusing job numbers so we need to renove
        the number on all the existing jobs
        """
        s = line.rstrip()
        (tm, rest) = s.split(' - ', 1)
        message_time = timestamp2float(tm)
        for x in self.joblist:
            if x.job['number'] != 0:
                if shutdown and 'exit' not in x.job:
                    x.job['exit'] = 'shutdown'
                x.job['number'] = 0
        self.timeline.shutdown(message_time)


# ############################################################################# ANALYSIS FUNCTIONS
    def number_of_jobs(self):
        return len(self.joblist)

    def first_job_at(self):
        """Return date/time of first job"""

        if len(self.joblist) > 0:
            return self.joblist[0].job['submitted']
        else:
            return None

    def last_job_at(self):
        """Return date/time of last job"""

        if len(self.joblist) > 0:
            return self.joblist[-1].job['submitted']
        else:
            return None

    def jobs_with_duration(self):
        """Returns the list of jobs that have a duration

            Jobs may not have a duration if they are in progress when
            scheduler is restarted or if cancelled
        """
        return [x for x in self.joblist if x.duration() != '']

    def write_xml(self, filename):
        """Write all jobs into an Excel friendly xml file"""
        with open(filename, "w") as fp:
            print('<Jobs>\n', file=fp)
            for j in self.joblist:
                print(j.job2xml(), file=fp)
            print('</Jobs>\n', file=fp)

    def write_csv(self, filename):
        """Write all jobs out into an Excel friendly csv file"""
        with open(filename, "w") as fp:
            header = True
            for j in self.joblist:
                if header:
                    print(j.job2csv(header), file=fp)
                    header = False

                print(j.job2csv(header), file=fp)



class Job:
    """
    Operations on a specific job

    Members:
        job: a dict with the items {S_Name S_User S_Priority duration number submitted start queued}
        jl: a pointer back to the job list if the job is in one. needed to track events
        lines: a list of all the source file lines that were used to build the job

    """

    __JOB_COUNTER__ = 0  # used to create unique identifier for jobs
    last_version_line = False

    def __init__(self):
        self.job = defaultdict(str)
        self.jl = None  # pointer back to the job list this job is in
        self.lines = []

    @staticmethod
    def parse_job_message(s):
        """Takes line from log file and separate it into time, job number and command"""
        s = s.rstrip()
        (tm, rest) = s.split(' - ', 1)
        float_time = timestamp2float(tm)
        (num, cmd) = rest.split(': ', 1)
        job_number = num[4:]
        return float_time, job_number, cmd

    def duration(self):
        # because duration is used so much I want to abstract the actual key name in case
        # I want to change it later
        return self.job['duration']

    def sim(self):
        """The name of the simulator is unfriendly in the log file so this returns a
           friendlier name for the EM simulator"""
        if self.job['S_Name'].startswith('mpiexec'):
            return 'Analyst'
        elif self.job['S_Name'].startswith('AXIEM') or self.job['S_Name'].startswith('Axiem'):
            return 'AXIEM'
        elif self.job['S_Name'].startswith('AWR_EMS2Proxy'):
            return 'EM_3rd_Party'
        else:
            return self.job['S_Name']

    #
    # Set of functions to parse the various types of lines found in the log
    #
    def found(self, message):
        # Found version 11111 for task id "AXIEM"
        (message_time, job_number, command) = self.parse_job_message(message)
        self.job['id'] = 'JOB' + str(Job.__JOB_COUNTER__)
        Job.__JOB_COUNTER__ += 1
        self.job['number'] = job_number
        version = command[command.find('version') + 8:]
        version = version[0:version.find(' ')]
        self.job['version'] = version

    def submitted(self, message):
        # 2014-11-05T12:45:43.0188 - Job 1: Submitted. Name="mpiexec:3.0", User="dhoekstr",
        # Priority=1
        (message_time, job_number, command) = self.parse_job_message(message)
        command = command[len('submitted. '):]
        # self.job['id'] = 'JOB' + str(Job.__JOB_COUNTER__) moved to found
        # Job.__JOB_COUNTER__ += 1 moved to found
        self.job['submitted'] = message_time
        # self.job['number'] = job_number moved to found

        # submitted command contains pairs of name=value keyword pairs
        for keyword_pair in [f.strip() for f in command.split(',')]:
            (name, value) = keyword_pair.split('=')
            self.job['S_' + name] = value.rstrip('"').lstrip('"')
        if self.jl:
            self.jl.timeline.add_event(Event(message_time, 'queued', self.job))

    def creating(self, message):
        # 2014-11-05T12:46:42.0140 - Job 1: Creating Process C:\Program Files\AWR\V11\mpiexec.exe
        # -np 8 -localonly "C:\Program Files\AWR\V11\grsim.exe"
        # "C:\ProgramData\AWR\Design Environment\11.
        (message_time, job_number, command) = self.parse_job_message(message)
        self.job['start'] = message_time
        if self.job['submitted'] == '':
            # the start time got lost in a server restart
            self.job['queued'] = 'NA'
        else:
            self.job['queued'] = self.job['start'] - self.job['submitted']
        if match(command, '-np'):
            tmp = command[command.find('-np') + 4:]
            tmp = tmp[0:tmp.find(' ')]
            self.job['num_processors'] = int(tmp)

    def assigned(self, message):
        global running_hosts
        assigned_re = re.compile('to controller "(.*)"')
        (message_time, job_number, command) = self.parse_job_message(message)
        host_name = assigned_re.search(message).group(1)
        if host_name in running_hosts:
            j = running_hosts[host_name]
            job = j.job
            if not job['exit']:
                job['exit'] = 'host_reassigned'
                del running_hosts[host_name]
                job['exceptions'] += 'exit status set by next assignment - '
                # old job did not see an exit message but host is getting re-assigned
                if job['start'] != '' and not job['stop']:  # we know that job is over so set stop time
                    job['stop'] = message_time
                    if self.duration() == '':
                        job['duration'] = job['stop'] - job['start']
                        if job['duration'] < 0:
                            # this seems to be possible under odd restart conditions
                            # where the log lines are out of order. It has to be bogus
                            # data so null out the duration
                            job['duration'] = ''
                            job['exceptions'] += 'negative duration deleted = '

                if self.jl:
                    self.jl.timeline.add_event(Event(message_time, 'vanished', job))

    def started(self, message):
        global running_hosts
        # 2014-11-13T09:09:10.0581 - Job 254: started AXIEM:33.0, procId:0 on
        # controller "dfw0awrsim01"
        (message_time, job_number, command) = self.parse_job_message(message)
        self.job['start'] = message_time
        if self.job['submitted'] == '':
            # the start time got lost in a server restart
            self.job['queued'] = 'NA'
        else:
            self.job['queued'] = self.job['start'] - self.job['submitted']
        host = command[command.find('controller ') + 12: -1]
        self.job['host'] = host
        running_hosts[host] = self

        if self.jl:
            self.jl.timeline.add_event(Event(message_time, 'started', self.job))

    def working_set(self, message):
        # 2015-03-03T16:49:10.0093 - Job 97: peak working set = 4546879488.
        (message_time, job_number, command) = self.parse_job_message(message)
        size = command[command.find('=') + 2:-1]  # from equal to before period
        if "MB" in size:
            size = float(size[:-2])
        elif "GB" in size:
            size = float(size[:-2]) * 1024
        else:
            size = int(size) / 1024 / 1024  # convert to MB
        self.job['working_set'] = size

    def releasing(self, message):
        # 2014-11-05T13:56:43.0531 - Job 1: releasing 8 processors (processor
        # reservations available before:0, after:8)
        (message_time, job_number, command) = self.parse_job_message(message)
        self.job['stop'] = message_time
        if self.job['start'] == '':
            # the start time got lost in a server restart
            self.job['duration'] = 'NA'
        else:
            self.job['duration'] = self.job['stop'] - self.job['start']
            if self.job['duration'] < 0:
                print('----- Job has negative duration -----')
                print('Set due releasing')
                print(self.job)

    def request_info(self, message):
        # 014-10-21T12:37:31.0010 - Job 1: MaxProcessors=8, MinProcessors=1,
        # ThreadsPerProcessor=1, PreferredPerf="low", PreferredMemCap="low".
        (message_time, job_number, command) = self.parse_job_message(message)
        for keyword_pair in [f.strip() for f in command.split(',')]:
            (name, value) = keyword_pair.split('=')

            self.job['R_' + name] = value.rstrip('.').rstrip('"').lstrip('"')

    def reserving(self, message):
        # 2014-10-21T12:37:31.0665 - Job 1: reserving 8 processors (0 processor
        # reservations remaining)
        (message_time, job_number, command) = self.parse_job_message(message)
        num_proc = command[10:command.find(' processors')]
        self.job['processors'] = int(num_proc)

    def files_remaining(self, message):
        # 2015-05-01T09:42:34.0945 - Job 1: Output Files remaining: 1
        (message_time, job_number, command) = self.parse_job_message(message)
        files_remaining = command[command.find(': ') + 1:]
        self.job['files_remaining'] = int(files_remaining)

    def exit_status(self, message):
        global running_hosts
        # 2014-10-21T12:37:59.0573 - Job 1: (AXIEM:1.0) Ended. Exit status: 0
        (message_time, job_number, command) = self.parse_job_message(message)

        # remove job from running host table
        if self.job['host'] in running_hosts:
            del running_hosts[self.job['host']]

        # need to check whether job has already see other exist status message
        if self.job['exit']:
            return

        self.job['exit'] = command.split(': ')[1]  # extract numerical exit status
        if self.duration() == '':
            if self.job['start'] != '':
                self.job['stop'] = message_time
                self.job['duration'] = self.job['stop'] - self.job['start']
                if self.job['duration'] < 0:
                    print('----- Job has negative duration -----')
                    print('Set due to exit status')
                    print(self.job)
            else:
                print('Job {} has no start time {}.'.format(job_number, self.job['start']))
        if self.jl:
            self.jl.timeline.add_event(Event(message_time, 'ended', self.job))

    def exit_code(self, message):
        global running_hosts
        # 20...0 - Job 18: Process 404 ("C:\Program Files\AWR\V12\mpiexec.exe") ended with exit code 1.
        (message_time, job_number, command) = self.parse_job_message(message)

        # remove job from running host table
        if self.job['host'] in running_hosts:
            del running_hosts[self.job['host']]

        # need to check whether job has already see other exist status message
        if self.job['exit'] and self.job['start'] and self.job['duration']:
            return

        if self.job.get('exit') != 'cancelled':
            # cancelled precedes the exit code as it is a more useful message
            self.job['exit'] = command.split('exit code ')[1][:-1]  # extract numerical exit status
        if self.duration() == '':
            if self.job['start'] != '':
                self.job['stop'] = message_time
                self.job['duration'] = self.job['stop'] - self.job['start']
                if self.job['duration'] < 0:
                    print('----- Job has negative duration -----')
                    print('Set due to exit status')
                    print(self.job)
            else:
                print('Job {} has no start time {}.'.format(job_number, self.job['start']))
        if self.jl:
            self.jl.timeline.add_event(Event(message_time, 'ended', self.job))

    def cancelled(self, message):
        # 2014-11-13T14:17:10.0419 - Dequeueing job number 263 (AXIEM:39.0)
        # for some weird reason this message is non-standard
        if self.job['exit']:
            # job already cancelled or terminated, do nothing
            return

        s = message.rstrip()
        (tm, rest) = s.split(' - ', 1)
        message_time = timestamp2float(tm)

        if self.duration() == '':
            # jobs being cancelled may not have been started yet
            if self.job['start'] != '':
                self.job['stop'] = message_time
                # don't set duration because job was cancelled

        self.job['exit'] = 'cancelled'

        # remove job from running host table
        if self.job['host'] in running_hosts:
            del running_hosts[self.job['host']]

        if self.jl:
            self.jl.timeline.add_event(Event(message_time, 'cancelled', self.job))

    def terminated(self, message):
        # 2016 - 03 - 28T13:44:17.0468 - Terminating job number 26(mpiexec:2.2)

        if self.job['exit']:
            # job already cancelled or terminated, do nothing
            return

        s = message.rstrip()
        (tm, rest) = s.split(' - ', 1)
        message_time = timestamp2float(tm)
        self.job['stop'] = message_time
        self.job['exit'] = 'cancelled'
        # don't set duration because job was cancelled

        # remove job from running host table
        if self.job['host'] in running_hosts:
            del running_hosts[self.job['host']]

        if self.jl:
            self.jl.timeline.add_event(Event(message_time, 'terminated', self.job))

    def copy_back_start(self, message):
        # 2016-02-27T20:10:50.0577 - Job 464: Output Files remaining: 1
        (message_time, job_number, command) = self.parse_job_message(message)
        if not self.job['stop']:
            # file copying started so job is over but no exit message seen yet.
            # set stop time make mark that it is set from copy
            self.job['stop'] = message_time
            self.job['exceptions'] += 'set stop time from copy line - '

    def copy_back_end(self, message):
        # 2016-02-19T09:23:59.0571 - Job 22: Output Files remaining: 1
        (message_time, job_number, command) = self.parse_job_message(message)
        if self.job['stop']:
            self.job['results_copy'] = message_time - self.job['stop']
        elif self.job['exit'] == 'cancelled':
            # cancelled, output file message is actually erronious
            return
        else:
            print('Error: Found a "output files=0" log line in a job with no exit status on job:')
            self.pprint()

        # End of parsing functions

    # ############################################################################### OUTPUT FUNCTION

    def job2csv(self, is_header):
        """For writing out jobs as CSV, take one job and convert it to a string in csv format"""

        s = ''
        (date, tm, day) = time2tuple(self.job['submitted'])
        s += 'submitted_date' if is_header else date
        s += ','
        s += 'submitted_time' if is_header else tm
        s += ','
        s += 'submitted_day' if is_header else day
        s += ','

        (date, tm, day) = time2tuple(self.job['start'])
        s += 'start_date' if is_header else date
        s += ','
        s += 'start_time' if is_header else tm
        s += ','
        s += 'start_day' if is_header else day
        s += ','
        s += 'duration_m' if is_header else interval2string_m(self.job['duration'])
        s += ','
        s += 'wait_m' if is_header else interval2string_m(self.job['queued'])
        s += ','
        s += 'user' if is_header else self.job['S_User']
        s += ','
        s += 'simulator' if is_header else self.sim()
        s += ','
        s += 'host' if is_header else self.job['host']
        s += ','
        s += 'working_set' if is_header else str(self.job['working_set'])
        s += ','
        s += 'priority' if is_header else self.job['S_Priority']
        s += ','
        s += 'min_proc' if is_header else self.job['R_MinProcessors']
        s += ','
        s += 'threads' if is_header else self.job['R_ThreadsPerProcessor']
        s += ','
        s += 'max_proc' if is_header else self.job['R_MaxProcessors']
        s += ','
        s += 'req_perf' if is_header else self.job['R_PreferredPerf']
        s += ','
        s += 'req_mem' if is_header else self.job['R_PreferredMemCap']
        s += ','
        s += 'exit_code' if is_header else self.job['exit']
        s += ','
        s += 'results_copy_m' if is_header else interval2string_m(self.job['results_copy'])
        s += ','
        s += 'uuid' if is_header else str(self.job['S_UniqueID'])
        s += ','
        s += 'version' if is_header else str(self.job['major_version'])

        return s

    def job2dict(self):
        """convert a job into a 'clean' dictionary (I know, it already is)"""
        d = {}

        (date, tm, day) = time2tuple(self.job['submitted'])
        d['submitted_date'] = date
        d['submitted_time'] = tm
        d['submitted_day'] = day

        (date, tm, day) = time2tuple(self.job['start'])
        d['start_date'] = date
        d['start_time'] = tm
        d['start_day'] = day
        d['duration_m'] = interval2float_m(self.job['duration'])
        d['wait_m'] = interval2float_m(self.job['queued'])
        d['user'] = self.job['S_User']
        d['major_version'] = to_int_or_na(self.job['version'][:2])
        d['minor_version'] = self.job['version']
        d['simulator'] = self.sim()
        d['host'] = self.job['host']
        d['priotiry'] = to_int_or_na(self.job['S_Priority'])
        d['min_proc'] = to_int_or_na(self.job['R_MinProcessors'])
        d['threads'] = to_int_or_na(self.job['R_ThreadsPerProcessor'])
        d['max_proc'] = to_int_or_na(self.job['R_MaxProcessors'])
        d['req_perf'] = self.job['R_PreferredPerf']
        d['req_mem'] = self.job['R_PreferredMemCap']
        d['exit'] = self.job['exit']
        d['files_remaining'] = to_int_or_na(self.job['files_remaining'])
        d['working_set'] = to_int_or_na(self.job['working_set'])
        d['results_copy_m'] = interval2float_m(self.job['results_copy'])
        return d

    def pprint(self):
        ordered_keys = ['submitted', 'start', 'stop', 'exit', 'S_Name', 'host']
        d = self.job
        print('\n{} =============================================='.format(self.job['id']))
        max_key = max([len(k) for k in d.keys()])
        fmt_str = "%{}s: %s" .format(max_key + 1)
        for k in ordered_keys + sorted([x for x in d.keys() if x not in ordered_keys]):
            if k in ['start', 'submitted', 'stop']:
                print(fmt_str % (k, float_to_date(d[k])))
            else:
                print(fmt_str % (k, d[k]))
        print('----- Log Lines -----')
        for l in self.lines:
            print(l)

    def __str__(self):
        return self.job['id']

    def __repr__(self):
        return 'Job({})'.format(self.job)
