
# AWR Job Scheduler Log Analysis

This package contains routines to parse AWR job scheduler log files to render
the data into a CSV format.

This package is only tested on Python 3.4 and above due to the use of type hints.

## Installation

After downloading the package, use:

    python setup.py install
    pip install -r requirements.<min or full>
    
to install.

Where requirements.min are the requirements to run the conversion of log files to CSV while requirements.all are the requirements for performing analysis in Jupyter notebook, run tests, and other development tasks.

## Usage

The **log\_to\_csv.py** command will convert a log file to a CSV file.
If you have multiple log files you can specify a directory. If a directory
is specified, the files will be ordered by their modification times.  Since
the ordering of the files is important, do not change the modification times
on the log files before conversion.

**NOTE:** You should not convert log files from different scheduler nodes
at the same time.  See _Log Types_ below.

```
Usage: log_to_csv.py [options] filename
       Generate a job or event log from raw scheduler log files
       ex: log_to_csv.py -o myfile.csv -t jobs concat_log_files.txt

Options:
  -h, --help            show this help message and exit
  -v, --verbose         print additional debugging information
  -o OUTPUT_FILENAME, --outputfile=OUTPUT_FILENAME
                        output file name, will be a .csv file, if not
                        specified only summary will be output
  -t OUTPUT_TYPE, --outputtype=OUTPUT_TYPE
                        Output File Type = [jobs (default) | events]
```

Two different output formats are available:

1. Jobs - output data contains one row per simulation job
2. Events - output data contains one row per event

Use the jobs format to determine statistics regarding the simulation jobs run such
as the submit time, memory used, simulation time used, users, etc.

Use the events format to analyse statistics such as the number of concurrent jobs.

## Log Types

A job scheduler process will run on any computer that is scheduling or simulating.
each job scheduler will create a local log file but a scheduler node will aggregate
all the log information of its compute notes.  When converting logs, it is essential
to only convert logs from one node at a time.

In general, only **scheduler** node logs should be converted.  While log\_to\_csv.py will
work on compute node logs, the information will be redundant with the information in
the logs for the scheduler node that manages it.

For example, if you have 2 scheduler nodes S1 and S2 managing 10 compute nodes C1-C10, you
would convert all the log files for S1 to one CSV file followed by converting all the logs
for S2 to a separate CSV file.  These CSV files could then be concatenated into one resulting
file if desired.

## File Description

* notebools/Analyze\_User\_Log.ipynb - examples of various analyses on jobs log in a Jupyter notebook
* js/js\_pd.py - utility functions used when analyzing log CSV (used in Analyse\_User\_Log.ipynb)
* js/jsr.py - raw log file parsing module
* log\_type.py - script to determine the type of log file
* log\_to\_csv.py - script to convert raw log files to CSV
* test\_jsr.py - module tests
* tdata/ - support data for test_jsr.py


## Log File Format

### Jobs Format

The Jobs format contains the following fields:

* submitted_date - date job was submitteed in YYYY-MM-DD format
* submitted_time - hour of the day submitted (int)
* submitted_day - day of the week submitted
* start_date - date simulation was started in YYYY-MM-DD format
* start_time - hour simulation was started (int)
* start_day - day of the week simulation was started
* duration_m - simulation duration in minutes (float)
* wait_m - amount of time job sat in queue before starting in minutes (float)
* user - name of the user submitting job
* simulator - which simulator was used
* host - name of the host which simulated the job
* working_set - maximum memory used in MB (float)
* priority - submitted priority (int)
* min_proc - value of the minimum processor setting (int)
* threads - value of the threads setting (int)
* max_proc - value of the maximum processor setting (int)
* req_perf - required performance setting (string)
* req_mem - required memory setting (string)
* exit_code - exit code or ending state
* results\_copy\_m - time to copy the results back to user, if it could be determined, in minutes (float or NA)
* uuid - uuid of the job (this is used to reconnect jobs after server restart)
* version - major version

### Events Format

The purpose of the event log format is to provide a way to track the number of jobs both running and queued at any given time.  The file format is:

* Timestamp string (YYYYMMDD HH:MM:SS)
* Timestamp in python floating point format
* Change in queue (whether a job has been queued, started, ended, etc)
* Number of jobs currently running
* Number of jobs in the queue
* Job name, identifier used to track job

Change Log
----------

### 2017-05-31

* Add support for directories as command line arguments to log\_to\_csv.py and log\_type.py
* Fixed requirements files
* Fix working set parsing for V13 so it handles MB and GB in logfiles
* Improve how cancellation messages are handled
* Fix parsing and storage of simulator version and add to csv output
* Improve output msg for log-type

