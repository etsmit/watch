"""
Class for computing the System Temperature from hot and cold loads
Cashes the hot+cold and off spectra as theses will remain relatively constant
Revised to store more data
"""

##################################################
# Imports
##################################################
import statistics
import radioastronomy
import numpy as np

MAXCHAN = 1024

class Tsys(object):
    """

    """
    def __init__(self):
        """
        initialize the components of the system temperature class
        """
        self.hot = radioastronomy.Spectrum()
        self.cold = radioastronomy.Spectrum()
        self.off = radioastronomy.Spectrum()
        self.tsys = radioastronomy.Spectrum()
        self.thot = 285.    # hot load (ground) temp
        self.tcold = 15.    # kelvins (feed+cmb+cables before 1st amp)
        self.dt = self.thot - self.tcold
        self.tmax  = 1000.  # maximum allowed returned hot load
        self.useoff = False
        self.usehot = False
        self.offdata = np.zeros(MAXCHAN+1)
        self.gain = np.zeros(MAXCHAN+1)
        self.epsilon = 1.E-8 # minimum counts for division

    def tmedian(self):
        """
        Compute median tsys value
        """
        tsys = 0.
        ndata =self.hot.nChan        #        print 'ndata = ',ndata
        bdata = int(ndata/4)
        edata = int(3*ndata/4)
        if ndata < 1:
            return tsys
        yminhot = min(self.hot.ydataA[bdata:edata]-self.offdata[bdata:edata])
        ymaxhot = max(self.hot.ydataA[bdata:edata]-self.offdata[bdata:edata])
        chot = 0.
        ccold = 0.
#        print 'Y Hot  min,max: ',yminhot,ymaxhot
        if yminhot != ymaxhot:
            chot = statistics.median(self.hot.ydataA[bdata:edata])
        ymincold = min(self.cold.ydataA[bdata:edata]-self.offdata[bdata:edata])
        ymaxcold = max(self.cold.ydataA[bdata:edata]-self.offdata[bdata:edata])
#        print 'Y Cold min,max: ',ymincold,ymaxcold
        if ymincold != ymaxcold:
            ccold = statistics.median(self.cold.ydataA[bdata:edata])
#        print 'hot,cold: ', chot, ccold
        # if there is a difference between the hot and cold load values
        if (chot - ccold) != 0:
            tsys = ((self.dt * ccold))/(chot - ccold)
        else:
            print "No differnce between hot and cold load counts"
        return tsys

    def tcalc( self, yhot, ycold, yoff):
        """
        Compute tsys arrays using arrays of yhot, ycold, yoff values
        """
        # compoueif there is a difference between the hot and cold load values
        dy = yhot - ycold  # difference between hot and cold load
        indicies = dy < self.epsilon # compute indicies of small differences 
        dy[indicies] = self.epsilon  # set minimum offsets
        tsys = self.dt * (ycold[:MAXCHAN]-yoff[:MAXCHAN])/dy[:MAXCHAN]
        return tsys

    def tmedian(self):
        """
        Compute median tsys value
        """
        tsys = 0.
        ndata =self.hot.nChan        #        print 'ndata = ',ndata
        bdata = int(ndata/4)
        edata = int(3*ndata/4)
        if ndata < 1:
            return tsys
        tsys = self.tcalc( self.hot.ydataA, self.cold.ydataA, self.offdata)
        tmed = statistics.median(tsys[bdata:edata])
        return tmed

    def __str__(self):
        """
        Define a spectrum summary string
        """
        tsys = self.tmedian()
        return "({0}, {1}, {2})".format(self.thot, self.tcold, tsys)

    def hotcalc(self):
        """
        Compute the parameters needed for repeated computations with the hot load.
        This module assumes hot load temperature has been set and the hot load data read.
        """
        indicies = self.hot.ydataA < self.epsilon  # avoid divide by zero
        self.hot.ydataA[indicies] = self.epsilon   # set values to min
        self.hot.ydataB = self.thot/self.hot.ydataA     # conversion from counts to kelvins
        return

    def gaincalc(self):
        """
        Compute the parameters needed for repeated computations with the hot load.
        This module assumes hot+cold load temperatures have been set and
        the hot load and cold load data read.
        """
        deltas = self.hot.ydataA - self.cold.ydataA
        indicies = deltas < self.epsilon  # avoid divide by zero
        deltas[indicies] = self.epsilon
        self.gain = self.dt/deltas
        indicies = self.hot.ydataA < self.epsilon
        self.hot.ydataA[indicies] = self.epsilon
        thot = statistics.median( self.hot.ydataA*self.gain)
#        if thot > self.dt:
#            print "gaincalc: Hot Load Equivalent Temperature: %8.3f (K)" % (thot)
        self.gain = thot/self.hot.ydataA
        return

    def readhot(self, hotname):
        """
        Read in the hot load intensity values Counts) for calibration.
        """
        self.hot.read_spec_ast(hotname)
        if len(self.hot.ydataA) > 0:
            self.usehot = True

    def readoff(self, offname):
        """
        Read in the hot load intensity values Counts) for calibration.
        """
        self.off.read_spec_ast(offname)
        if len(self.off.ydataA) > 0:
            self.useoff = True
            self.offdata = self.off.ydataA

    def readcold(self, coldname):
        """
        Read in the cold load intensity values Counts) for calibration.
        """
        self.cold.read_spec_ast(coldname)

    def tsysvalues(self, ycounts):
        """
        Return the system temperature array, based on cashed hot load parameters
        """
        tsys[:MAXCHAN] = ycounts[:MAXCHAN] * self.gain[:MAXCHAN]
        indices = tsys > self.tmax
        tsys[indicies] = self.tmax
        return tsys

    def tvalues(self):
        """
        Return the calibrated difference between the reference (cold) spectrum and
        the current spectrum
        """
        # subtract the counts from the reference location
        # now multiply by the gain factor
        tsys = 0.
        ndata =self.hot.nChan
        if ndata < 1:
            return tsys
        tsys = self.tcalc( self.hot.ydataA, self.cold.ydataA, self.offdata)
        self.tsys.ydataA = tsys
        return tsys # return temperatures without correction for reference location

    def tsky(self, ysky):
        """
        Return the calibrated difference between the reference (cold) spectrum and
        the current spectrum
        """
        # subtract the counts from the reference location
        # now multiply by the gain factor
        tsys = self.gain[:MAXCHAN] * (ysky[:MAXCHAN] - self.offdata[:MAXCHAN])
        return tsys # return temperatures without correction

# HISTORY
# 16OCT11 GIL separate array-only function
# 16OCT10 GIL correction for offdata
# 16SEP06 GIL initial version
