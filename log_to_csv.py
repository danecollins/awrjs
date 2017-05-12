
# standard python includes
import os
import sys
import time
from optparse import OptionParser

# my includes
import js.jsr as jsr


usage = """%prog [options] filename
       Generate a job or event log from raw scheduler log files
       ex: %prog -o myfile.csv -t jobs concat_log_files.txt"""

parser = OptionParser(usage)
parser.add_option("-v", "--verbose",
                  action="store_true", dest="verbose",
                  help="print additional debugging information")
parser.add_option('-o', '--outputfile',
                  action="store", dest='output_filename',
                  help="output file name, will be a .csv file, if not specified only summary will be output")
parser.add_option('-t', '--outputtype',
                  action="store", dest='output_type', default='jobs',
                  help='Output File Type = [jobs (default) | events]')

# options will be a dict of the options
(options, args) = parser.parse_args()

if len(args) != 1:
    parser.print_help()
    exit(1)
else:
    filename = args[0]
    if not os.path.exists(filename):
        print("ERROR: Could not open '{}'\n".format(filename))
        parser.print_help()
        exit(1)
    if options.verbose:
        jsr.debug_port = sys.stdout
print('Parsing log...')
jobs = jsr.Jobs(filename)
timeline = jobs.timeline

if jobs.number_of_jobs() > 0:
    start = jobs.first_job_at()
    tml = time.localtime(start)
    start = time.strftime("%Y-%m-%d", tml)

    end = jobs.last_job_at()
    tml = time.localtime(end)
    end = time.strftime("%Y-%m-%d", tml)
else:
    print('No jobs found in log.')
    exit(1)


if options.output_type == 'jobs':
    if options.output_filename:
        jobs.write_csv(options.output_filename)
        print('produced {} containing {} jobs from {} to {}.'.format(options.output_filename,
                                                                     jobs.number_of_jobs(),
                                                                     start, end
                                                                     ))
else:
    if options.output_filename:
        fp = open(options.output_filename, 'w')
        timeline.write(fp=fp)
        fp.close()
        print('produced {}.'.format(options.output_filename))