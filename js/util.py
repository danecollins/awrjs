import sys
import os


def is_logfile(f):
    f = f.lower()
    return f.startswith('awr_jobscheduler') and f.endswith('.txt')


def expand_file_list(file_args):
    file_list = []
    for f in file_args:
        if os.path.isfile(f):
            if is_logfile(f):
                file_list.append(f)
        elif os.path.isdir(f):
            for root, dirs, files in os.walk(f):
                for file in files:
                    fn = os.path.basename(file)
                    if is_logfile(fn):
                        full_name = os.path.join(root, file)
                        file_list.append(full_name)
    # need to sort by file date
    ordered_file_list = sorted(file_list, key=lambda x: os.path.getmtime(x))

    return ordered_file_list

if __name__ == '__main__':
    print(sys.argv[1:])
    for f in expand_file_list(sys.argv[1:]):
        print(f)