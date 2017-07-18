#!/usr/bin/env python2
"""
watch is the main python program for collecting gnuradio
spectra for astronomical discoveries.
"""
##################################################
# GNU Radio Python Flow Graph
# Title: Nsf Watch
##################################################
# HISTORY
# 17MAY22 ETS this one works. adds some things to the path that helps all the imports go through
# 17JAN20 GIL auto-determine SDR tuner name
# 17JAN10 GIL allow restoring an observing with any observing file
# 16DEC23 GIL use observing_notes
# 16DEC17 GIL re-fix setting the center frequency
# 16OCT16 GIL fix setting the center frequency
# 16AUG24 GIL version that works on both ubuntu and mac
# 16AUG23 GIL increase fft_rate
# 16AUG21 GIL update pylint suggestions
# 16AUG20 GIL revise gains[]
# 16JUL07 GIL revision to transfer only floats to fft_astronomy

import os
import sys
sys.path.append("/Library/Library/Frameworks/Python.framework/Versions/2.7/lib/python2.7/site-packages")
sys.path.append("/opt/local/var/macports")
import time
import datetime
from optparse import OptionParser
from gnuradio import eng_notation
from gnuradio.eng_option import eng_option
from gnuradio import filter
import fftsink2
from gnuradio.wxgui import forms
from grc_gnuradio import wxgui as grc_wxgui
from gnuradio.filter import firdes
import osmosdr
import wx
import observing_notes
import gettuner

class watch(grc_wxgui.top_block_gui):
    """
    watch is the main NSF Astronomy class for accumulating spectra
    """
    def __init__(self):
        """
        Initialize the class which records Astronomical Spectra
        """
        grc_wxgui.top_block_gui.__init__(self, title="Nsf Watch")

        ##################################################
        # Variables
        ##################################################
        self.notes = observing_notes.observing_notes()
        self.notes.read_notes() # read the previous values
#        self.notes.SampleRate = 10e6
        self.nchan = 1024
        self.thot = 290.
        self.tcold = 10.
        self.FrequencyChooser_0 = self.notes.FrequencyStr
# end if a note file

        ##################################################
        # Blocks
        ##################################################
        self.notebook_0 = self.notebook_0 = wx.Notebook(self.GetWin(), style=wx.NB_TOP)
        self.notebook_0.AddPage(grc_wxgui.Panel(self.notebook_0), "Wideband")
        self.notebook_0.AddPage(grc_wxgui.Panel(self.notebook_0), "Notes")
        self.Add(self.notebook_0)

# get the device name
#        self.notes.noteC = gettuner.name()
        self.notes.noteC = "RTLSDR"
        self.notes.noteC = "AIRSPY"
        print "Tuner: ",self.notes.noteC
        TUNER = self.notes.noteC.upper() # convert to upper case
        if "AIRSPY" in TUNER:
            print "Airspy SDR found"
            airspybias = " airspy,bias=1" # AIRSPY with Bias T on
        else:
# the line below allows any SDR device
#           airspybias = "rtl=0, bias=1"
#            gettuner.biasT(True)
            airspybias = " "  # no bias

#        self.rtlsdr_source_0 = osmosdr.source(args="numchan=" + str(1) + " ")
        print "About to turn on the Bias T, OK?"
#        x = raw_input('Enter a character to continue: ')
        self.rtlsdr_source_0 = osmosdr.source(args="numchan=" + str(1) + airspybias)
        print self.rtlsdr_source_0
        self.rtlsdr_source_0.set_sample_rate(self.notes.SampleRate)
        samplerate = self.rtlsdr_source_0.get_sample_rate()
        if samplerate != self.notes.SampleRate:
            print "Returned Sample Rate: ", samplerate, " != set: ", self.notes.SampleRate
            self.notes.SampleRate = 2.5e6  # try 2.5 MHz
            self.rtlsdr_source_0.set_sample_rate(self.notes.SampleRate)
            samplerate = self.rtlsdr_source_0.get_sample_rate()
            if round(samplerate) != round(self.notes.SampleRate):
                print "Sample Rate: ", samplerate, " not set rate: ", self.notes.SampleRate
                print "!!!!!!!!!!! Check that USB SDR DONGLE IS PLUGGED IN !!!!!!!!!!!!!"
                exit()

        self.notes.SampleRate = self.rtlsdr_source_0.get_sample_rate()
        self.rtlsdr_source_0.set_center_freq(self.notes.FrequencyHz, 0)
        self.rtlsdr_source_0.set_freq_corr(0, 0)
        self.rtlsdr_source_0.set_dc_offset_mode(0, 0)
        self.rtlsdr_source_0.set_iq_balance_mode(2, 0)
# turn AGC on, then off, to set (?)
        self.rtlsdr_source_0.set_gain_mode(True, 0)
        self.rtlsdr_source_0.set_gain_mode(False, 0)
        self.rtlsdr_source_0.set_antenna("", 0)
        self.rtlsdr_source_0.set_bandwidth(0, 0)

#            average=True,
        self.wxgui_fftsink2_0 = fftsink2.fft_sink_c(
            self.notebook_0.GetPage(0).GetWin(),
            baseband_freq=float(self.notes.FrequencyHz),
            y_per_div=5,
            y_divs=15,
            ref_level=-30,
            ref_scale=2.0,
            sample_rate=self.notes.SampleRate,
            fft_size=self.nchan,
            fft_rate=self.notes.fft_rate,
            average=False,
            avg_alpha=.7,
            title="FFT Astronomy Plot",
            peak_hold=False)
        self.notebook_0.GetPage(0).Add(self.wxgui_fftsink2_0.win)
        self._NoteA_text_box = forms.text_box(
            parent=self.notebook_0.GetPage(1).GetWin(),
            value=self.notes.noteA,
            callback=self.set_NoteA,
            label="Note",
            converter=forms.str_converter()
        )
        self.notebook_0.GetPage(1).Add(self._NoteA_text_box)

        self._NoteB_text_box = forms.text_box(
            parent=self.notebook_0.GetPage(1).GetWin(),
            value=self.notes.noteB,
            label="Gain",
            callback=self.set_NoteB,
            converter=forms.str_converter())
        self.notebook_0.GetPage(1).Add(self._NoteB_text_box)

        self._Observer_text_box = forms.text_box(
            parent=self.notebook_0.GetPage(1).GetWin(),
            value=self.notes.Observer,
            callback=self.set_Observer,
            label="Observer",
            converter=forms.str_converter()
        )
        self.notebook_0.GetPage(1).Add(self._Observer_text_box)

        self._Site_text_box = forms.text_box(
            parent=self.notebook_0.GetPage(1).GetWin(),
            value=self.notes.Site,
            callback=self.set_Site,
            label="Site",
            converter=forms.str_converter()
        )
        self.notebook_0.GetPage(1).Add(self._Site_text_box)

# add astronomy inputs
        self._Integrations_01_text_box = forms.text_box(
            parent=self.notebook_0.GetPage(1).GetWin(),
            value=self.notes.Integrations,
            callback=self.set_Integrations_01,
            label="Ave Time (s)",
            converter=forms.float_converter())
        self.notebook_0.GetPage(1).Add(self._Integrations_01_text_box)
        self._Azimuth_01_text_box = forms.text_box(
            parent=self.notebook_0.GetPage(1).GetWin(),
            value=self.notes.Azimuth,
            callback=self.set_Azimuth_01,
            label="Azimuth",
            converter=forms.str_converter())
        self.notebook_0.GetPage(1).Add(self._Azimuth_01_text_box)
        self._Elevation_01_text_box = forms.text_box(
            parent=self.notebook_0.GetPage(1).GetWin(),
            value=self.notes.Elevation,
            callback=self.set_Elevation_01,
            label="Elevation",
            converter=forms.str_converter())
        self.notebook_0.GetPage(1).Add(self._Elevation_01_text_box)
        self._fft_rate_01_text_box = forms.text_box(
            parent=self.notebook_0.GetPage(1).GetWin(),
            value=self.notes.fft_rate,
            callback=self.set_fft_rate_01,
            label="FFT Rate",
            converter=forms.int_converter())
        self.notebook_0.GetPage(1).Add(self._fft_rate_01_text_box)

        self._SampleRate_01_text_box = forms.text_box(
            parent=self.notebook_0.GetPage(1).GetWin(),
            value=self.notes.SampleRate,
            callback=self.set_SampleRate_01,
            label="Sample Rate",
            converter=forms.float_converter()
        )
        self.notebook_0.GetPage(1).Add(self._SampleRate_01_text_box)
        self._FrequencyMHz_01_text_box = forms.text_box(
            parent=self.notebook_0.GetPage(1).GetWin(),
            value=self.notes.FrequencyStr,
            callback=self.set_Frequency,
            label="Frequency (MHz)",
            converter=forms.str_converter()
        )
        self.notebook_0.GetPage(1).Add(self._FrequencyMHz_01_text_box)
        self.set_fft_rate_01(str(self.notes.fft_rate))
        # set integration time to a short time to update the displays
        self.set_Azimuth_01(self.notes.Azimuth)
        self.set_Elevation_01(self.notes.Elevation)
        self.set_SampleRate_01(self.notes.SampleRate)
        # now set the desired integration time
        self.set_Integrations_01(str(self.notes.Integrations))

        self.Frequency_Chooser_0 = self.notes.FrequencyStr 
        self._FrequencyChooser_0_chooser = forms.drop_down(
            parent=self.notebook_0.GetPage(1).GetWin(),
            value=self.FrequencyChooser_0,
            callback=self.set_FrequencyChooser_0,
            label='FrequencyChooser_0',
            choices=['90.9', '99.7', '829.0', '1227.6', self.FrequencyChooser_0, '1424.0',
                     '1436.2', '1575.0', '1666.0', '1710.0'],
            labels=['FM1', 'FM2', '3G', 'GPS L2', 'H1', 'HI-Off', 'Test', 'GPS L1', 'OH', '4G']
        )
        self.notebook_0.GetPage(1).Add(self._FrequencyChooser_0_chooser)

        gainCount = 0
#        devicename = self.rtlsdr_source_0.name()
#        print 'Device: ', devicename

        GAINs = self.rtlsdr_source_0.get_gain_names()
        nGAINs = len(GAINs)
        gains = [1., 1., 1.]

        print 'Gain Names: ', GAINs
        for GAIN in GAINs:
            R = self.rtlsdr_source_0.get_gain(GAIN)
            time.sleep(1)
            gainCount = gainCount + 1
            if gainCount == 1:
                self._gain1_text_box = forms.text_box(
                    parent=self.notebook_0.GetPage(1).GetWin(),
                    value=self.notes.gain1,
                    callback=self.set_gain1,
                    label=GAIN+" Gain",
                    converter=forms.float_converter(),
                    proportion=0
                    )
                self.notebook_0.GetPage(1).Add(self._gain1_text_box)
            if gainCount == 2:
                self._gain2_text_box = forms.text_box(
                    parent=self.notebook_0.GetPage(1).GetWin(),
                    value=self.notes.gain2,
                    callback=self.set_gain2,
                    label=GAIN+" Gain",
                    converter=forms.float_converter(),
                    proportion=0,
                    )
                self.notebook_0.GetPage(1).Add(self._gain2_text_box)
            if gainCount == 3:
                self._gain3_text_box = forms.text_box(
                    parent=self.notebook_0.GetPage(1).GetWin(),
                    value=self.notes.gain3,
                    callback=self.set_gain3,
                    label=GAIN+" Gain",
                    converter=forms.float_converter(),
                    proportion=0,
                    )
                self.notebook_0.GetPage(1).Add(self._gain3_text_box)

        self.set_gain1(self.notes.gain1)
        self.set_gain2(self.notes.gain2)
        self.set_gain3(self.notes.gain3)
        self.set_NoteA(str(self.notes.noteA))
        self.wxgui_fftsink2_0.win.set_gain_note(self.notes.gains)
        self._NoteB_text_box.set_value(str(self.notes.noteB))

# new addion, low pass filter
#        self.low_pass_filter_0 = filter.fir_filter_ccf(1, firdes.low_pass( \
#        	.8, self.notes.SampleRate, self.notes.SampleRate*.475, 0.1e6, \
#                     firdes.WIN_RECTANGULAR, 6.76))


        ##################################################
        # Connections
        ##################################################
        self.connect((self.rtlsdr_source_0, 0), (self.wxgui_fftsink2_0, 0))
#        self.connect((self.rtlsdr_source_0, 0), (self.low_pass_filter_0, 0))    
#        self.connect((self.low_pass_filter_0, 0), (self.wxgui_fftsink2_0, 0))

    def set_NoteB(self, mystr):
        """
        The second note string records the gains of the amps
        """
        NoteB = 'GAIN = '
        GAINs = self.rtlsdr_source_0.get_gain_names()
        ngains = len(GAINs)
        for GAIN in GAINs:
            R = self.rtlsdr_source_0.get_gain(GAIN)
#            R = self.rtlsdr_source_0.get_gain_range(GAIN)
            NoteB = NoteB + str(R) + ' ; '
#            if jjj > 0:
#                break
        GAIN = GAINs[0]
        self.notes.noteB = NoteB
        self.wxgui_fftsink2_0.win.set_gain_note(self.notes.gains)
        self._NoteB_text_box.set_value(self.notes.noteB)
        self.notes.write_notes()

    def set_NoteA(self, NoteA):
        self.notes.noteA = NoteA
        self.wxgui_fftsink2_0.win.set_note(str(NoteA))
        self._NoteA_text_box.set_value(self.notes.noteA)
        self.notes.write_notes()

    def set_Observer(self, Observer):
        self.notes.Observer = Observer
        self.notes.write_notes()

    def set_Site(self, Site):
        self.notes.Site = Site
        self.notes.write_notes()

    def set_gain1(self, gain1):
        """
        Set gain and Record gain setting in note file
        """
        GAINs = self.rtlsdr_source_0.get_gain_names()
        self.rtlsdr_source_0.set_gain(gain1, GAINs[0])
        gain1 = self.rtlsdr_source_0.get_gain(GAINs[0])
        print 'set_gain 1: ', gain1
        self.notes.gain1 = gain1
        self._gain1_text_box.set_value(gain1)
        self.notes.gains[0] = float(gain1)
        self.set_NoteB("")
        self.notes.write_notes()

    def set_gain2(self, gain2):
        """
        Record gain setting in note file
        """
        GAINs = self.rtlsdr_source_0.get_gain_names()
        nGAINs = len(GAINs)
        if nGAINs > 1:
            self.rtlsdr_source_0.set_gain(gain2, GAINs[1])
            gain2 = self.rtlsdr_source_0.get_gain(GAINs[1])
            print 'set_gain 2: ', gain2
            self.notes.gain2 = gain2
            self._gain2_text_box.set_value(gain2)
            self.notes.gains[1] = float(gain2)
            self.set_NoteB("")
            self.notes.write_notes()

    def set_gain3(self, gain3):
        """
        Set gain and Record gain setting in note file
        """
        GAINs = self.rtlsdr_source_0.get_gain_names()
        nGAINs = len(GAINs)
        if nGAINs > 2:
            self.rtlsdr_source_0.set_gain(gain3, GAINs[2])
            gain3 = self.rtlsdr_source_0.get_gain(GAINs[2])
            print 'set_gain 3: ', gain3
            self.notes.gain3 = gain3
            self._gain3_text_box.set_value(gain3)
            self.notes.gains[2] = float(gain3)
            self.set_NoteB("")
            self.notes.write_notes()
        else:
            return

    def get_NoteA(self):
        """
        Return observing summary String
        """
        return self.notes.noteA

    def get_NoteB(self):
        """
        Return gain String
        """
        return self.notes.noteB

    def get_Observer(self):
        """
        Return observer name
        """
        return self.Observer

    def get_Site(self):
        return self.Site

    def get_FrequencyChooser_0(self):
        """
        return class value
        """
        return self.FrequencyChooser_0

    def set_Frequency(self, FrequencyMHz):
        self.FrequencyHz = float(FrequencyMHz)*1.E6
        self.FrequencyStr = str(FrequencyMHz)
        self.FrequencyChooser_0 = self.FrequencyStr
        baseband = self.FrequencyHz
#        self.wxgui_fftsink2_0.set_baseband_freq(str(baseband))
        self.wxgui_fftsink2_0.set_baseband_freq(baseband)
        self.rtlsdr_source_0.set_center_freq(self.FrequencyHz)
        centerfreq = self.rtlsdr_source_0.get_center_freq()
        
        if round(centerfreq) != round(self.FrequencyHz):
            print "Error Setting Cente Frequency"
            print "Commanded Frequency: ", self.FrequencyHz
            print "Reported  Frequency:", centerfreq
#        self._FrequencyMHz_01_text_box.set_value(self.FrequencyStr)
        self._FrequencyMHz_01_text_box.set_value(self.FrequencyHz*1.E-6)
        self.notes.write_notes()

    def set_FrequencyChooser_0(self, FrequencyChooser_0):
        print "Starting set_FrequencyChooser_0"
        self.FrequencyStr = FrequencyChooser_0
        self.FrequencyHz  = float(FrequencyChooser_0)*1.e6
        self.set_Frequency(float(FrequencyChooser_0))

    def set_Integrations_01(self, Integrations_01):
        self.Integrations = float(Integrations_01)
        self.wxgui_fftsink2_0.win.set_Integrations(float(Integrations_01))
#        self._Integrations_01_text_box.set_value(str(self.Integrations))
        self.notes.write_notes()

    def set_Azimuth_01(self, Azimuth_01):
        """
        set_Azimuth takes a user input string
        sets a float class value
        """
        self.Azimuth = float(Azimuth_01)
        self.wxgui_fftsink2_0.win.set_Azimuth(self.Azimuth)
        self._Azimuth_01_text_box.set_value(self.Azimuth)
        self.notes.write_notes()

    def set_Elevation_01(self, Elevation_01):
        """
        set_Elevation takes a user input string
        sets a float class value
        """
        self.Elevation = float(Elevation_01)
        self.wxgui_fftsink2_0.win.set_Elevation(self.Elevation)
        self._Elevation_01_text_box.set_value(str(self.Elevation))
        self.notes.write_notes()

    def set_fft_rate_01(self, fft_rate_01):
        self.notes.fft_rate = int(fft_rate_01)
        self.notes.write_notes()

    def set_SampleRate_01(self, SampleRate_01):
        self.notes.SampleRate = float(SampleRate_01)
        self.rtlsdr_source_0.set_sample_rate(self.notes.SampleRate)
        samplerate = self.rtlsdr_source_0.get_sample_rate()
        if samplerate != self.notes.SampleRate:
            print "Error setting Sample rate"
            print "Commanded Rate: ",self.notes.SampleRate
            print "Reported  Rate: ",samplerate
        self.wxgui_fftsink2_0.win.set_SampleRate(SampleRate_01)
        self.notes.write_notes()

    def get_SampleRate(self):
        """
        return a class value
        """
        return self.notes.SampleRate

    def get_Azimuth(self):
        return self.Azimuth

    def get_Elevation(self):
        """
        function to return elevation (deg) float
        """
        return self.Elevation

if __name__ == '__main__':
    parser = OptionParser(option_class=eng_option, usage="%prog: [options]")
    (options, args) = parser.parse_args()
# Check the Time is correct or all coordinates are a mess!
    nowutc = datetime.datetime.utcnow()
    now = datetime.datetime.now()
    print 'Check the time before all observations, or coordinates will be off!'
    print 'The local time is usually offset from UTC'
    print 'Check your Time-zone for your computer'
    print 'Local Time: ', now
    print ' UTC  Time: ', nowutc
    print ''
    x = raw_input('Enter a character to continue: ')
    topblock = watch()
    topblock.Start(True)
    topblock.Wait()

if __name__ == '__main__':
###    """
###    If main, confirm threads is loading
###    """
    import ctypes
    import sys
    if sys.platform.startswith('linux'):
        try:
            x11 = ctypes.cdll.LoadLibrary('libX11.so')
            x11.XInitThreads()
        except:
            print "Warning: failed to XInitThreads()"
