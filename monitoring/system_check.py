#!/usr/bin/env python

from argparse import ArgumentParser
from sys import exit
import psutil


def parseargs():
    p = ArgumentParser()
    p.add_argument('--cpu', action = 'store_true')
    p.add_argument('--memory', action = 'store_true')
    p.add_argument('--swap', action = 'store_true')
    p.add_argument('--du', action = 'store_true')
    p.add_argument('-c', '--critical', required=False, type=int, help='Critical threshold')
    p.add_argument('-w', '--warning', required=False, type=int, help='Warning threshold')
    return vars(p.parse_args())


def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def main():
    if params['cpu']:
        cpu = psutil.cpu_times_percent(interval=1)
        print 'CPU usage: system {0}, user {1}, idle {2}'.format(cpu.system, cpu.user, cpu.idle)

        if params['critical'] <= (100 - cpu.idle):
            exit(2)

        elif params['warning'] <= (100 - cpu.idle):
            exit(1)
        else:
            exit(0)

    elif params['memory']:
        memory = psutil.virtual_memory()
        print 'Memory usage: total {0}, available {1}, used {2}, free {3}'.format(
            sizeof_fmt(memory.total), sizeof_fmt(memory.available), sizeof_fmt(memory.used),
            sizeof_fmt(memory.free))

        if params['critical'] <= memory.percent:
            exit(2)

        elif params['warning'] <= memory.percent:
            exit(1)
        else:
            exit(0)

    elif params['swap']:
        swap = psutil.swap_memory()
        print 'Swap usage: total {0}, used {1}, free {2}'.format(
            sizeof_fmt(swap.total), sizeof_fmt(swap.used), sizeof_fmt(swap.free))

        if params['critical'] <= swap.percent:
            exit(2)

        elif params['warning'] <= swap.percent:
            exit(1)
        else:
            exit(0)

    elif params['du']:
        du = { mp.mountpoint: psutil.disk_usage(mp.mountpoint).percent for mp in psutil.disk_partitions() }

        print 'Disk usage:', '; '.join(map( lambda x: '{0} {1}% free'.format(x, 100 - du[x]), du))

        if len(filter(lambda x: du[x] > params['critical'], du)) > 0:
            exit(2)
        elif len(filter(lambda x: du[x] > params['warning'], du)) > 0:
            exit(1)
        else:
            exit(0)


if __name__ == '__main__':
    params = parseargs()
    main()
