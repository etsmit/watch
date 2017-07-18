# Need to import the plotting package:
#import matplotlib.pyplot as plt
#plot the System temperature based on 2 hot load obs and two coldoad
#HISTORY
#16JUL10 GIL major revision to recalculate the coordinates
#16APR01 GIL parse date, recompute Lon,Lat
#16MAR24 GIL let the script find the hot load data and produces plots for averaged spectra
#16FEB17 GIL add anotations to plot
#15AUG27 GIL add option to fix 10.0 MHz axis looking like 2.5 MHz
#15JUL09 GIL Initial version based on pltraw.py

#The expected file format is below:
# File: 2016-03-22T22:12:04.ast
# Time range: 2016-03-22T22:12:04.792773 - 2016-03-22T22:07:04.753554
# ZX60 + Amp13 + 3 LNA4ALL + ZX60 + BigHornWaveGuideFilter
# LNA= 6.0; MIX= 3.0; IF= 6.0; 
# Count     = 4498
# CenterFreq= 1420100000.0
# Bandwidth = 10000000.0
# DeltaX    = 9765.625
# NCHAN     = 1024
# UTC       = 2016-03-22 22:12:04.792773
# LST       = 17:17:31.60
# AZ        = 80.0
# EL        = 45.0
# RA        = 21:07:08.78
# DEC       = 34:19:07.7
# LON       = 78:53:01.3
# LAT       = -8:45:08.7
# ALT_SUN   = -8:57:51.5
# AZ_SUN    = 80:19:49.1
#0000 1415100000 4.94589688592e-08
#0001 1415109765 5.1711648024e-08
#0002 1415119531 5.41282828544e-08
#0003 1415129296 5.69578262166e-08
#...

import pylab
import numpy as np
import sys
import statistics
from ephem import Observer
from ephem import Sun
from ephem import Equatorial
from ephem import Galactic
from ephem import hours
from ephem import degrees
import datetime
from dateutil import parser
#from scipy.interpolate import UnivariateSpline
#from scipy.signal import savgol_filter
from scipy.signal import filtfilt, butter

TimeAve = datetime.timedelta(minutes=1.)

# first define the observer location
me = Observer()
me.lon='-79.8397'
me.lat='38.4331'
me.elevation=800   # height in meters
# reformat the time into ephemerus format. 

dy = -1.
scalefactor=1e12
ymed = 100.
xrange = 500.

# Create an order 3 lowpass butterworth filter.
b, a = butter(3, 0.05)

dy = -1.0
MAXAVE = 3
#scale = 1.E12
dbzero = 100.

print 'Number of arguments:', len(sys.argv), 'arguments.'
nargs = len( sys.argv)
#print 'Argument List:', nargs
print '---------------------'
print 'Tsys finds all data taken with elevation below 0 and averages these as the hot load'
print 'The remaining data sets are all cold load data to be averaged for input time intervals'
print '---------------------'

linestyles = ['-','--','-.','-','--','-.','-','--','-.','-','--','-.','-','--','-.','-','--','-.']
colors = ['-b','-r','-g','-m','-c','-b','-r','-g','-m','-g','-b','-r','-g','-b','-r','-g','-b','-r','-g','-b','-r','-g']

c = 299792.  # (v km/sec)
nuh1 = 1420.4056 # neutral hydrogen frequency (MHz)
thot = 285.0  # define hot and cold
#thot = 272.0  # 30 Farenheit = 272 K
tcold = 10.0
tmin  = 20.0 
tmax  = 999.0 # define reasoanable value limits

print 'Argument List:', str(sys.argv)
nargs = len( sys.argv)

linestyles = ['-','-','--','-.','-','--','-.','-','--','-.','-','--','-.','-','--','-.','-','--','-','-','--','-.','-','--','-.','-','--','-.','-','--','-.','-','--','-.','-','--','-.']
colors = ['-b','-r','-g','-b','-r','-g','-b','-r','-g','-b','-r','-g','-b','-r','-g','-b','-r','-g','-b','-r','-g','-b','-r','-g','-b','-r','-g','-b','-r','-g','-b','-r','-g','-b','-r','-g']

pylab.figure()
pylab.hold(True)

xallmax = -9.e9
xallmin =  9.e9
yallmax = -9.e9
yallmin =  9.e9
az = '-1.'
el = '-90'
count = '0'
note = ''
lonoff = 0.0
latoff = 0.0
lonave = 0.0
latave = 0.0
ncold = 0
nave = 1
nHot = 0
nfiles = 0
nPlot = 0
fixx = 0
Bandwidth  = 2.5E6
CenterFreq = 1.42045e9
DeltaX     = 2441.40625
datacount = 0
aName = ""

# Read all files and arguments
for iii in range(1, nargs):

    filename = sys.argv[iii]
    if (filename == '-t'):
        print "Time range"
        iii = iii + 1
        TimeAve = float( sys.argv[iii])

        continue
    
    nfiles = nfiles + 1
# Read the file. 
    f2 = open(filename, 'r')
# read the whole file into a single variable, which is a list of every row of the file.
    lines = f2.readlines()
    f2.close()

# initialize some variable to be lists:
    x1 = []
    y1 = []

#####################################################################################
# FIRST run through, read all the HOT LOAD data; skip all data with el > 0
#####################################################################################

    linecount = 0
# scan the rows of the file stored in lines, and put the values into some variables:
    for line in lines:
        parts = line.split()
        if linecount < 0:
            sys.stdout.write(line.replace("# ","",1))
        if parts[1] == 'File:':
            aName = parts[2]
        linecount = linecount + 1
        if linecount == 3:
            note = line.replace("# ","",1)

# if a comment or parameter lien
        if line[0] == '#':
            if len(parts) < 4:
                continue
            if parts[1] == 'File:':
                aName = parts[2]
# if a comment or parameter line
        if line[0] == '#':
            if len(parts) < 4:
                continue
            if parts[1] == 'UTC':
                parts = line.split('=')
                utc = parts[1]
                datadate = ephem.Date(utc)
                print ('UTC = %s %s', utc, datadate)
            if parts[1] == 'Count':
                Count = parts[3]
            if parts[1] == 'LST':
                lst = parts[3]
                print ('LST = %s', lst)
            if parts[1] == 'AZ':
                az = parts[3]
                azangle = ephem.degrees( az)
            if parts[1] == 'EL':
                el = parts[3]
                elangle = ephem.degrees( el)
# special case for hot load; break if above zero  elevation
                if (elangle > 0.0):
                    break
# convert string RA,DEC into float
            if parts[1] == 'RA':
                ra = parts[3]
                raangle = ephem.hours( parts[3])
                rafloat = raangle * rad2deg
            if parts[1] == 'DEC':
                dec = parts[3]
                decangle = ephem.degrees(parts[3])
                print decangle
                decfloat = decangle * rad2deg
# if latitude parse and turn into a float
            if parts[1] == 'LAT':
                lat = parts[3]
                latangle = ephem.degrees( lat)
                latfloat = latangle * rad2deg
            if parts[1] == 'LON':
                lon = parts[3]
                lonangle = ephem.degrees( lon)
                lonfloat = lonangle * rad2deg
            if parts[1] == 'CenterFreq':
                CenterFreq = float(parts[3])
            if parts[1] == 'Bandwidth':
                Bandwidth = float(parts[3])
            if parts[1] == 'DeltaX':
                DeltaX = float(parts[3])
            if parts[1] == 'Count':
                Count = float(parts[3])
            continue

# getting only HOT load data skip if above zero
        if (elangle > 0.0):
            break
        datacount = datacount+1
        p = line.split()
#        print(p)
        x = float(p[1])*1.E-6
        x1.append(x)
        y1.append(float(p[2])*scalefactor)
    if (el > 0.0):
        continue

    sys.stdout.write(":Hot: "+aName+"\n")
    
    xv = np.array(x1)
    yv = np.array(y1)
    nData = len(yv)  # get the size of the array

# must zero if the first hot load file    
    if nHot == 0:
        yon  = np.zeros(nData)
        yhot = np.zeros(nData)

# now average data 
    for jjj in range( 0, nData):
        yhot[jjj] = yv[jjj]
    nHot = nHot+1

print str(nHot) + ' Files found with elevation less than zero'
if nHot < 1:
    print 'No Hot Load observations, can not calibrate'
    exit()


# completed summing of all hot load data.  now smooth
# compute average
# compute average
ytemp  = np.zeros(nData)
ynoise = np.zeros(nData)

for jjj in range( 0, nData):
    ytemp[jjj] = yhot[jjj]
    ynoise[jjj] = ytemp[jjj]
    yhot[jjj] = ytemp[jjj]

#s = UnivariateSpline(xv, ytemp, s=1)
#s = UnivariateSpline(xv, ytemp, s=50, k=5)

# Use filtfilt to apply the filter.
ytemp = filtfilt(b, a, yhot)

#ytemp = savgol_filter( ynoise, 61, 3)
#ytemp = savitzky_golay( ynoise, 51, 2)

for jjj in range( 3, (nData-3)):
    yhot[jjj] = (ytemp[jjj-3]+ytemp[jjj-2] + ytemp[jjj-1] + ytemp[jjj] + ytemp[jjj+1] + ytemp[jjj+2] + ytemp[jjj+3])/7.0

#pylab.plot( xv, ynoise, colors[0], label='noisy')
#pylab.plot( xv, ytemp, colors[1], label='sav-gol')
#pylab.plot( xv, yhot, colors[2], label='smoothed')
#pylab.legend(loc='upper right')
#pylab.show()

# Now re-do file check, excluding Hot load data.

FileCount = nfiles
nfiles = 0
nCold = 0
datacount = 0

#####################################################################################
# SECOND TIME through, read all the SKY data; skip all data with el < 0
#####################################################################################

# offset plots by a temperature increment
offset = 0.0
dK     = 10.0
# read all files and arguments again, this time collecting cold load data
for iii in range(1, nargs):

    filename = sys.argv[iii]
    if (filename == '-t'):
        print "Time range"
        TimeAve = float( sys.argv[iii+1])
        iii = iii + 1
        continue
    if nfiles == 0:
        firstname = filename
    lastname = filename
    
    nfiles = nfiles + 1
# Read the file. 
    f2 = open(filename, 'r')
# read the whole file into a single variable, which is a list of every row of the file.
    lines = f2.readlines()
    f2.close()

# initialize some variable to be lists:
    x1 = []
    y1 = []

    linecount = 0
# scan the rows of the file stored in lines, and put the values into some variables:
    for line in lines:
        parts = line.split()
        linecount = linecount + 1
        if linecount == 3:
            note = line.replace("# ","",1)

# if a comment or parameter line
        if line[0] == '#':
            if len(parts) < 4:
                continue
            if parts[1] == 'UTC':
                parts = line.split('=')
                utc = parts[1]
                datadate = ephem.Date(utc)
                print ('UTC = %s %s', utc, datadate)
            if parts[1] == 'Count':
                Count = parts[3]
            if parts[1] == 'LST':
                lst = parts[3]
                print ('LST = %s', lst)
            if parts[1] == 'AZ':
                az = parts[3]
                azangle = ephem.degrees( az)
            if parts[1] == 'EL':
                el = parts[3]
                elangle = ephem.degrees( el)
# special case for hot load; break if below zero elevation
                if (elangle < 0.0):
                    break
# convert string RA,DEC into float
            if parts[1] == 'RA':
                ra = parts[3]
                raangle = ephem.hours( parts[3])
                rafloat = raangle * rad2deg
            if parts[1] == 'DEC':
                dec = parts[3]
                decangle = ephem.degrees(parts[3])
                print decangle
                decfloat = decangle * rad2deg
# if latitude parse and turn into a float
            if parts[1] == 'LAT':
                lat = parts[3]
                latangle = ephem.degrees( lat)
                latfloat = latangle * rad2deg
            if parts[1] == 'LON':
                lon = parts[3]
                lonangle = ephem.degrees( lon)
                lonfloat = lonangle * rad2deg
            if parts[1] == 'CenterFreq':
                CenterFreq = float(parts[3])
            if parts[1] == 'Bandwidth':
                Bandwidth = float(parts[3])
            if parts[1] == 'DeltaX':
                DeltaX = float(parts[3])
            if parts[1] == 'Count':
                Count = float(parts[3])
            continue

# getting only COLD load data, skip if below zero elevation
        if (elangle < 0.0):
            break

        sys.stdout.write(filename+"\r")

        if (datacount < 1):
            firstutc = datadate
            me = ephem.Observer()
            me.lat, me.lon, me.elev = str(geolat), str(geolon), geoelev
            me.date = datadate
            rame, decme = me.radec_of( azangle, elangle)
            print ('UTC = %s -> %s LST', datadate, me.sidereal_time())

            azfloat = azangle*rad2deg
            elfloat = elangle*rad2deg
            eqdate = ephem.Equatorial( rame, decme, epoch=me.date)
            eq2000 = ephem.Equatorial( eqdate, epoch=ephem.J2000)
            ga2000 = ephem.Galactic( eq2000)

#now compute the ra,dec from the azimuth,elevation, time and location
            print('Horn Ra,Dec = %s,%s for Az,El %5.1f,%5.1f ' % (rame,decme, azfloat, elfloat))
#radec_a = Equatorial( ra_a, dec_a, me.date)
#finally calculate the galactic coordiates for the ra, dec coordinates
            print(ga2000.lon, ga2000.lat)

        datacount = datacount+1
        p = line.split()
#        print(p)
        x = float(p[1])*1.E-6
        x1.append(x)
        y1.append(float(p[2])*scalefactor)
    
# if this was a hot load, skip rest of processing
    if (elangle < 0.):
        continue

    xv = np.array(x1)
    yv = np.array(y1)
    nData = len(yv)  # get the size of the array

# if first file in this series, zero before average
    if nCold == 0:
        yon  = np.zeros(nData)
        ycold = np.zeros(nData)
        latoff = 0.
        lonoff = 0.

    for jjj in range( 0, nData):
        ycold[jjj] = yv[jjj]
    nCold = nCold+1
#    latoff = latoff + gal.lat
    latoff = latoff + latfloat
#    lonoff = lonoff + gal.lon
    lonoff = lonoff + lonfloat

    dt = utc - firstutc
# optionally show remainder of last obs, but is noisier than other obs
    if ((dt > TimeAve) or ((nfiles+1 >= FileCount) and nPlot == 0)):
#    if (dt > TimeAve) or ((nfiles == FileCount) and (nPlot == 0)):
#    if (dt > TimeAve) or ((nfiles == FileCount) and (nPlot == 0)):
        # average coordinates
#        latoff = 180.0*latoff/float(nCold)/3.1415926
#        lonoff = 180.0*lonoff/float(nCold)/3.1415926
        latoff = latoff/float(nCold)
        lonoff = lonoff/float(nCold)

# now average and smooth
        ytemp = np.zeros(nData)    # initialize arrays
        for jjj in range( 0, nData):
            ytemp[jjj] = ycold[jjj]

# next smooth
        for jjj in range( 1, (nData-2)):
            ycold[jjj] = (ytemp[jjj-1] + ytemp[jjj] + ytemp[jjj+1])/3.0

        tsys  = np.zeros(nData)    # initialize arrays
        Z     = np.zeros(nData)
        oneMZ = np.zeros(nData)
        for jjj in range( 0, nData):

            if ycold[jjj] < 1.:
                ycold[jjj] = 1.
            if (yhot[jjj] < 2.):
                yhot[jjj] = 2.

            Z[jjj] = ycold[jjj]/yhot[jjj]

            oneMZ[jjj] = 1. - Z[jjj]
            if (oneMZ[jjj] < .001):
                oneMZ[jjj] = 0.001
            tsys[jjj] = ((Z[jjj]*thot) - tcold)/oneMZ[jjj]

        vel = np.zeros(nData)
        for jjj in range (0, nData):
            vel[jjj] = c * (xv[jjj] - nuh1)/nuh1

        label = ""

        tsky  = np.zeros(nData)    # initialize arrays
        S     = np.zeros(nData)    # initialize arrays

        if yon[jjj] < 1.:
            yon[jjj] = 1.
        S[jjj] = yhot[jjj]/(tsys[jjj] + thot)
        tsky[jjj] = yon[jjj]/S[jjj]

        label = 'Lon,Lat=%5.1f,%5.1f' % (lonave,latave)

        tmedian =  statistics.median(tsys[round(nData/3):round(2*nData/3)])
        ymin = min(tsys[round(nData/4):round(3*nData/4)])
        ymax = max(tsys[round(nData/4):round(3*nData/4)])
        ymed = statistics.median(tsys[round(nData/4):round(3*nData/4)])
        print(' Max: %9.1f  Median: %9.1f SNR: %6.2f ; %s %s' % (ymax, ymed, ymax/ymed, count, label)) 
        print('%s' % note)
#pylab.xlim( -190, 190)
        xrange = 350.
        pylab.xlim( -xrange, xrange*.8)
#pylab.xlim( -200, 200)
#pylab.xlim( -90, 90)
        pylab.title("Galactic Neutral Hydrogen Emission")
        pylab.xlabel('Velocity (Km/Second)')
        pylab.ylabel('Intensity (Kelvins)')
        plottwo = 1
#        if plottwo == 0:
#    pylab.ylim( -20, 80)
#            pylab.plot(vel, tsky-tsys, colors[1], linestyle=linestyles[1],label=label, linewidth=3)
#        else:
#            pylab.ylim( ymed*.8, ymed*1.6)
#    pylab.ylim( -30, 150)
#    pylab.ylim( 500, 1600)
        labelTsys = 'Lon,Lat=%5.1f,%5.1f' % (lonoff,latoff)
#        offset = 0
        pylab.plot(vel, tsys+offset, colors[nPlot], linestyle=linestyles[0],label=labelTsys, linewidth=3)
        offset = offset+dK
        nave = 0
        nCold = 0
        firstutc = utc
        nPlot = nPlot + 1
        datacount = 0
        print firstname,lastname

#dK = 0
#offset = 0
ytop = (ymed*1.3)+offset+dK
ybot = ymed*.9
yrange = ytop-ybot
pylab.ylim( ybot, ytop)
xmin = min(vel)
xmax = max(vel)
xmin = int((xmin+10)/50.)
xmin = 50.*xmin
xmax = int((xmax+10)/50.)
xmax = 50.*xmax
pylab.xlim(xmin,xmax)
pylab.text( xmin+10., ytop-(yrange*.05), firstname + ' - ' + lastname)
pylab.text( xmin+10., ytop-(yrange*.15), note)
pylab.legend(loc='upper right')
pylab.show()
# end for all files
    

