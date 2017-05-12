#!/usr/bin/python

import re
import sys
import pdb
from optparse import OptionParser


usage = "usage: %prog [options] filename(s)"
parser = OptionParser(usage)
parser.add_option("-d", "--debug",
                  action="store_true", dest="debug",
                  help="print lines in file that set file type")
parser.add_option("-l", "--long",
                  action="store_true", dest="long",
                  help="output in filename: type even for just 1 file")


# options will be a dict of the options
(options, args) = parser.parse_args()

p_local = re.compile('Started By')
p_override = re.compile('Queue Type Override set to: "(.*)"')
# p_local2 = re.compile('Remote Queue.*Type=Scheduler')
p_scheduler = re.compile('Remote Queue.*Type=Compute')

if len(args) > 1 or options.long:
    format = "long"
else:
    format = "short"

for file in args:
    with open(file) as fp:
        lines = fp.readlines()

    scheduler = False
    local = False
    compute = False
    override = False
    typ = False
    for l in lines:
        l = l.strip()
        if not scheduler:
            if p_scheduler.search(l):
                scheduler = l
        if not local:
            # if p_local1.search(l) or p_local2.search(l):
            if p_local.search(l):
                local = l
        x = p_override.search(l)
        if x:
            tmp = x.group(1)
            if tmp and tmp != 'Automatic' and typ and typ != tmp:
                print('File: {}'.format(file))
                print('ERROR: Log changed type override from {} to {}'.format(typ, tmp))
            if tmp != 'Automatic':
                typ = tmp
                override = l

    if options.debug:
        print(file)
        if scheduler:
            print('  Defined as job scheduler:', scheduler)

        if local:
            print('  Defined as local:', local)

        if override:
            print('  Override set:', override)

        if not (scheduler or local or override):
            print('  Default to compute')

    if format == 'long':
        print(file, ': ', end='')

    # determine type
    if not (scheduler or local or override):
        log_type = 'compute'
    elif scheduler and local:
        print('\nERROR: Found definition for both scheduler and local types')
        print('  ', scheduler)
        print('  ', local)
    elif scheduler:
        if override and typ != 'Scheduler':
                print('\nERROR: Found definition for scheduler but override says {}'.format(typ))
                print('  ', scheduler)
                print('  ', override)
        log_type = 'scheduler'
    elif local:
        if override and typ != 'Local':
            print('\nERROR: Found definition for local but override says {}'.format(typ))
            print('  ', local)
            print('  ', override)
        log_type = 'local'
    elif override:
        log_type = override
    print(log_type)
