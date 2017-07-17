#Python Script to plot raw NSF record data.
#import matplotlib.pyplot as plt
#plot the raw data from the observation
#HISTORY
#16AUG29 GIL make more efficient
#16AUG16 GIL use new radiospectrum class
#15AUG30 add option to plot range fo values
#15JUL01 GIL Initial version
#
import matplotlib.pyplot as plt
import numpy as np
import sys
import datetime
import statistics
import radioastronomy

avetimesec = 120.
dy = -1.

nargs = len( sys.argv)

linestyles = ['-','-','-', '-.','-.','-.','--','--','--','-','-','-', '-.','-.','-.','--','--','--','-','-','-', '-.','-.','-.','--','--','--','-','-','-', '-.','-.','-.','--','--','--']
colors =  ['-b','-r','-g', '-b','-r','-g','-b','-r','-g','-b','-r','-g','-b','-r','-g','-b','-r','-g','-b','-r','-g','-b','-r','-g','-b','-r','-g','-b','-r','-g','-b','-r','-g','-b','-r','-g']
nmax = len(colors)
scalefactor = 1e8
xallmax = -9.e9
xallmin =  9.e9
yallmax = -9.e9
yallmin =  9.e9

c = 299792.  # (v km/sec)
nuh1 = 1420.4056 # neutral hydrogen frequency (MHz)
thot = 285.0  # define hot and cold
#thot = 272.0  # 30 Farenheit = 272 K
tcold = 10.0
tmin  = 20.0 
tmax  = 999.0 # define reasoanable value limits

#for symbol, value in locals().items():
#    print symbol, value

nplot = 0
nhot = 0
ncold = 0

# first read through all data and find hot load
for iii in range(1, nargs):

    filename = sys.argv[iii]

    rs = radioastronomy.Spectrum()
    rs.read_spec_ast( filename)
    rs.azel2radec()    # compute ra,dec from az,el

    if rs.telel < 0:
        if nhot == 0:
            hot = rs
            nhot = 1
        else:
            hot.ydataA = hot.ydataA + rs.ydataA
            hot.count = hot.count + rs.count
            nhot = nhot + 1

if nhot > 0:
    hot.ydataA = scalefactor * hot.ydataA / float(nhot)
    print "Found %3d hot load obs" % nhot
else:
    print "No hot load data, can not calibrate"
    exit()

xv = hot.xdata * 1.E-6
yv = hot.ydataA
hv = yv               # will need hot load values in remaining calc
yallmin = min(yv)
yallmax = max(yv)

fig,ax1 = plt.subplots(figsize=(10,6))
plt.hold(True)
az = hot.telaz
el = hot.telel
ymin = 1000.  # initi to large values
ymax = 0.
ymed = statistics.median(yv)
count = hot.count
ncold = 0
#print(' Max: %9.1f  Median: %9.1f SNR: %6.2f ; %s %s' % (ymax, ymed, ymax/ymed, count, label))
#plt.plot(xv, yv, colors[0], linestyle=linestyles[0],label=label)

nData = len(xv)
# condition data for avoid divide by zero later (2 depends on scalefactor)
for iii in range(nData):
    if (hv[iii] < 2.):
        hv[iii] = 2.

avetime = datetime.timedelta(seconds=avetimesec)

nread = 0        
# now read through all data and average cold sky obs
for iii in range(1, nargs):

    filename = str(sys.argv[iii])

    parts = filename.split('/')
    nparts = len(parts)
    aname = parts[nparts-1]
    parts = aname.split('.')
    aname = parts[0]
    parts = aname.split('T')
    date  = parts[0]
    time  = parts[1]
    time  = time.replace('_',':')

    rs = radioastronomy.Spectrum()
#    print filename
    rs.read_spec_ast( filename)
    rs.azel2radec()    # compute ra,dec from az,el

    if rs.telel > 0:
        cold = rs
        gallon = cold.gallon
        gallat = cold.gallat
        az = cold.telaz
        el = cold.telel
        parts = filename.split('T')
        date = parts[0]
        aname = parts[1]
        parts = aname.split('.')
        aname = parts[0]
        xv = cold.xdata * 1.E-6
        yv = cold.ydataA * scalefactor
        
        xmin = min(xv)
        xmax = max(xv)
        xallmin = min(xmin,xallmin)
        xallmax = max(xmax,xallmax)
        count = cold.count
        ncold = 0
        note = cold.noteA
                    #print('%s' % note)
        ncolor = min(nmax-1, nplot) 
        nplot = nplot + 1
        
        tsys = np.zeros(nData)    # initialize arrays
        iss = np.zeros(nData)
        Z = np.zeros(nData)
        oneMZ = np.zeros(nData)
        for jjj in range( 0, nData):
            iss[jjj] = jjj
            if yv[jjj] < 1.:
                yv[jjj] = 1.
                
            Z[jjj] = yv[jjj]/hv[jjj]
            oneMZ[jjj] = 1. - Z[jjj]
            if (oneMZ[jjj] < .001):
                oneMZ[jjj] = 0.001
            tsys[jjj] = ((Z[jjj]*thot) - tcold)/oneMZ[jjj]

            vel = np.zeros(nData)
            for jjj in range (0, nData):
                vel[jjj] = c * (xv[jjj] - nuh1)/nuh1
                
        tsky  = np.zeros(nData)    # initialize arrays
        S     = np.zeros(nData)    # initialize arrays

        for jjj in range (0, nData):
            vel[jjj] = c * (xv[jjj] - nuh1)/nuh1
            S[jjj] = hv[jjj]/(tsys[jjj] + thot)
            tsky[jjj] = yv[jjj]/S[jjj]
            
        icenter = 512
        tsky[icenter] = (tsky[icenter-2] + tsky[icenter+2])*.5
        tsky[icenter-1] = (3.*tsky[icenter-2] + tsky[icenter+2])*.25
        tsky[icenter+1] = (tsky[icenter-2] + 3.*tsky[icenter+2])*.25
        
        label = 'Lon,Lat=%5.1f,%5.1f' % (gallon,gallat)

        ymin = min(tsky)
        ymax = max(tsky)
        yallmin = min(ymin,yallmin)
        yallmax = max(ymax,yallmax)
        ymed = statistics.median(tsky)
        label = '%s Lon,Lat=%5.1f,%5.1f' % (aname,gallon,gallat)
        label = '%s, Az,El: %5s,%5s, Lon,Lat: %5.1f,%5.1f' % (aname,az,el,gallon,gallat)
        print(' Max: %9.1f  Median: %9.1f SNR: %6.2f ; %s %s' % (ymax, ymed, ymax/ymed, count, label))
        plt.plot(vel, tsky, colors[ncolor], linestyle=linestyles[ncolor],label=label)
#                plt.plot(iss, tsky, colors[ncolor], linestyle=linestyles[ncolor],label=label)
        # end if a cold file
    #end for all files to sum

#plt.xlim(xallmin,xallmax)
plt.xlim(-250., 250.)
plt.ylim(105.,1.1*yallmax)
fig.canvas.set_window_title(date)
for tick in ax1.xaxis.get_major_ticks():
    tick.label.set_fontsize(14) 
for tick in ax1.yaxis.get_major_ticks():
    tick.label.set_fontsize(14) 
plt.title(date)
plt.xlabel('Velocity (km/sec)', fontsize=14)
plt.ylabel('Intensity (Kelvins)', fontsize=14)
plt.legend(loc='upper right')
plt.show()
