# python 3.4 only due to use of nonlocal

# standard python includes
import os
import sys
from collections import Counter
import pandas as pd
import numpy as np

# my includes


class ImproperFormat(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def read_and_validate(filename):
    df = pd.read_csv(filename)

    # validate the columns we have to have
    required_cols = ['simulator', 'exit_code', 'duration_m', 'user']
    for c in required_cols:
        if c not in df.columns:
            raise ImproperFormat('Required column named {} is missing'.format(c))

    return df


def jobs_with_duration(jobs_df):
    """Return the list of jobs that have a duration"""
    return jobs_df[jobs_df.duration_m.notnull()]


def successful_jobs(jobs_df):
    """Return the jobs with a zero exit status"""
    return jobs_df[(jobs_df.exit_code == '0') & (jobs_df.duration_m > 0)]


def sim_list(df):
    # need to filter out nan
    return sorted([x for x in df.simulator.unique() if isinstance(x, str)])


def jobs_by_type(jobs_df, sim_breakdown=True):
    """Compute a dataframe of the number of jobs by completion type"""
    results = {}
    simulators = sim_list(jobs_df) if sim_breakdown else []

    def add_row(label, df):
        nonlocal results
        row = {}
        row['Total'] = len(df)
        vc = df.simulator.value_counts()
        for sim in simulators:
            row[sim] = vc[sim] if sim in vc else 0
        results[label] = row

    add_row('Jobs Submitted', jobs_df)
    add_row('Completed Successfully', jobs_df[jobs_df.exit_code == '0'])
    add_row('Cancelled by User', jobs_df[jobs_df.exit_code == 'cancelled'])
    add_row('Host Reassigned', jobs_df[jobs_df.exit_code == 'host_reassigned'])
    add_row('Scheduler Shutdown', jobs_df[jobs_df.exit_code == 'shutdown'])
    add_row('Other Disposition', jobs_df[~ jobs_df.exit_code.isin(['0', 'cancelled', 'shutdown', 'host_reassigned'])])

    return pd.DataFrame.from_dict(results, orient="index")


def duration_stats(jobs_df, sim_breakdown=True):
    """Computes statistics on the durations of all jobs in the list"""

    results = {}
    simulators = sim_list(jobs_df) if sim_breakdown else []
    # only keep jobs that have durations
    df = jobs_with_duration(jobs_df)

    def add_row(label, stat_func):
        nonlocal results
        row = {}
        row['Overall'] = stat_func(df.duration_m)
        for sim in simulators:
            row[sim] = stat_func(df[df.simulator == sim].duration_m)
        results[label] = row

    add_row('Longest Job', max)
    add_row('Average Job Duration', np.mean)
    add_row('Median Job Duration', np.median)

    return pd.DataFrame.from_dict(results, orient="index")


def wait_stats(jobs_df, sim_breakdown=True):
    """Compute statistics on the amount of time jobs wait in the queue"""

    results = {}
    simulators = sim_list(jobs_df) if sim_breakdown else []
    # only keep jobs that were not cancelled
    df = jobs_df[jobs_df.exit_code != 'cancelled']

    def add_row(label, stat_func):
        nonlocal results
        row = {}
        row['Overall'] = stat_func(df.wait_m)
        for sim in simulators:
            row[sim] = stat_func(df[df.simulator == sim].wait_m)
        results[label] = row

    add_row('Longest Wait', max)
    add_row('Average Wait', np.mean)
    add_row('Median Wait', np.median)

    return pd.DataFrame.from_dict(results, orient="index")


def median_by_user(jobs_df, sim_breakdown=True):
    """Compute the median simulation time of successful jobs by user"""
    results = {}
    simulators = sim_list(jobs_df) if sim_breakdown else []
    # only keep jobs that were not cancelled
    jobs_df = succeeded_jobs(jobs_df)

    def add_row(label, df):
        nonlocal results
        row = {}
        row['Overall'] = np.median(df.duration_m)
        for sim in simulators:
            row[sim] = np.median(df[df.simulator == sim].duration_m)
        results[label] = row

    for user in sorted(df.user.unique()):
        add_row(user, jobs_df[jobs_df.user == user])

    return pd.DataFrame.from_dict(results, orient="index")


if __name__ == '__main__':
    df = read_and_validate('jobs.csv')
    print(median_by_user(df))