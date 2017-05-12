
AWR Job Scheduler Log Analysis
==============================

This package contains routines to parse AWR job scheduler log files to render
the data into a .csv format.

This package is only tested on Python 3.4 and above.

Usage
-----

The **process_logs.py** command will provide information about a log file or convert it to
a .csv file.  If you have multiple log files they should be concatenated together.

```
Usage: process_logs.py [options] filename
       Generate a job or event log from raw scheduler log files
       ex: process_logs.py -o myfile.csv -t jobs concat_log_files.txt

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


File Description
----------------

* Analyze_User_Log.ipynb - examples of various analyses on jobs log in a jupyter notebook
* js_pd.py - utility functions used when analyzing log CSV (used in Analyse_User_Log.ipynb)
* jsr.py - raw log file parsing module
* log_type.py - script to determine the type of log file
* process_logs.py - script to convert raw log files to CSV
* test_jsr.py - module tests

