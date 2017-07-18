import subprocess

def name():
    """
    name() uses a command line function, rtl_biast,
    to find the name(s) of SDR devices connected via USB ports.
    A side effect of calling the function is turning of the bias T of some devices
    """

    p = subprocess.Popen('rtl_biast', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    line = p.stdout.readlines()
#    p.close()

    parts = line[0].split("Found ")
    if len(parts) < 2:
        print '!!! Did not find an SDR device'
        return '!!! Did not find an SDR device'

    names = parts[1].split(" tuner")
    if len(names) < 2:
        print '!!! Did not find expected name for SDR device:'
        print 'Found: ',parts
        return '!!! Did not find expected name for SDR devise.'

    tuner = names[0]
    return tuner

def biasT( on=True):
    """ 
    biasT takes a true or false argument for turning the bias t on or off
    """

    if on:
        p = subprocess.Popen('rtl_biast -b 1', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    else: # else turn the bias t off
        p = subprocess.Popen('rtl_biast', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

#    p.close()

    return

