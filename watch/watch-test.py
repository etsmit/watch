#!/usr/bin/env python2
# -*- coding: utf-8 -*-
##################################################
# GNU Radio Python Flow Graph
# Title: Nsf Watch
##################################################
"""
watch is the main python program for collecting gnuradio
spectra for astronomical discoveries.
"""
##################################################
# GNU Radio Python Flow Graph
# HISTORY
# 16DEC12 GIL try to fix python environment
# 16NOV26 GIL fix setting the center frequency and bandwidth
# 16OCT16 GIL fix setting the center frequency
# 16AUG24 GIL version that works on both ubuntu and mac
# 16AUG23 GIL increase fft_rate
# 16AUG21 GIL update pylint suggestions
# 16AUG20 GIL revise gains[]
# 16JUL07 GIL revision to transfer only floats to fft_astronomy

import os
import time
import datetime
from optparse import OptionParser
#from gnuradio.eng_option import eng_option
from gnuradio import analog
from gnuradio import blocks
from gnuradio import eng_notation
from gnuradio import filter
from gnuradio import gr
from gnuradio import wxgui
from gnuradio.eng_option import eng_option
import fftsink2
from gnuradio.wxgui import forms
from gnuradio.fft import window
from gnuradio.filter import firdes
#from gnuradio.wxgui import fftsink2
from grc_gnuradio import wxgui as grc_wxgui
import osmosdr
import wx
#import time

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
        self.samp_rate = samp_rate = 10e6
#        self.SampleRate = 10e6
        self.SampleRate = samp_rate    #Hz
        self.SampleRateStr = str(self.SampleRate*1.E-6) #MHz
        self.AveCount = 0
        self.FileCount = 0
        self.nchan = 1024
        self.NoteName = "Watch.not"
        self.Observer = "Glen Langston"
        self.Site = "Moumau House, Green Bank, WV"
        self.gain1 = 8.0    # LNA GAIN
        self.gain2 = 3.0    # MIX GAIN
        self.gain3 = 8.0    # IF  GAIN
        self.gains = [self.gain1, self.gain2, self.gain3]
        self.Azimuth = 180.0
        self.Elevation = 45.0
        self.Integrations = int(3)
        self.Longitude = -79.8397
        self.Latitude = 38.4331
        self.Frequency = 1419.0E6     # setup for AIRSPY
        self.thot = 290.
        self.tcold = 10.
        self.FrequencyStr = str(self.Frequency*1.E-6) # String MHz
        self.fft_rate = 20000     # spectra averaged per second
# end if a note file
        self.Note_01 = "Notes are logged with observations in files"
        self.Note_02 = "Gain Chain notes"
        self.readnotes(self.NoteName) # read the previous values

        ##################################################
        # Blocks
        ##################################################
        self.notebook_0 = self.notebook_0 = wx.Notebook(self.GetWin(), style=wx.NB_TOP)
        self.notebook_0.AddPage(grc_wxgui.Panel(self.notebook_0), "Wideband")
        self.notebook_0.AddPage(grc_wxgui.Panel(self.notebook_0), "Notes")
        self.Add(self.notebook_0)
        # process complex ffts (sink_c)
        self.wxgui_fftsink2_0 = fftsink2.fft_sink_c(
            self.notebook_0.GetPage(0).GetWin(),
            baseband_freq=float(self.Frequency),
            y_per_div=5,
            y_divs=15,
            ref_level=-30,
            ref_scale=2.0,
            sample_rate=self.samp_rate,
            fft_size=self.nchan,
            fft_rate=self.fft_rate,
            average=False,
            avg_alpha=.7,
            title="FFT Astronomy Plot",
            peak_hold=False)
        self.notebook_0.GetPage(0).Add(self.wxgui_fftsink2_0.win)
# 
#        self.Add(self.wxgui_fftsink2_0.win)
#        self.low_pass_filter_0 = filter.fir_filter_ccf(1, firdes.low_pass(
#        	1, samp_rate, .9e6, .1e6, firdes.WIN_HAMMING, 6.76))
        self.low_pass_filter_0 = filter.fir_filter_ccf(1, firdes.low_pass(
        	.8, samp_rate, samp_rate*.5*.95, 0.2e6, firdes.WIN_HAMMING, 6.76))
        self.blocks_add_xx_0 = blocks.add_vcc(1)
        self.blocks_throttle_0 = blocks.throttle(gr.sizeof_gr_complex*1, 3*samp_rate,True)
        self.analog_sig_source_x_0 = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, .77e6, .005, 0)
        self.analog_noise_source_x_0 = analog.noise_source_c(analog.GR_GAUSSIAN, .1, 0)

        self._Note_01_text_box = forms.text_box(
            parent=self.notebook_0.GetPage(1).GetWin(),
            value=self.Note_01,
            callback=self.set_Note_01,
            label="Note",
            converter=forms.str_converter()
        )
        self.notebook_0.GetPage(1).Add(self._Note_01_text_box)

        self._Note_02_text_box = forms.text_box(
            parent=self.notebook_0.GetPage(1).GetWin(),
            value=self.Note_02,
            label="Gain",
            callback=self.set_Note_02,
            converter=forms.str_converter())
        self.notebook_0.GetPage(1).Add(self._Note_02_text_box)

        self._Observer_text_box = forms.text_box(
            parent=self.notebook_0.GetPage(1).GetWin(),
            value=self.Observer,
            callback=self.set_Observer,
            label="Observer",
            converter=forms.str_converter()
        )
        self.notebook_0.GetPage(1).Add(self._Observer_text_box)

        self._Site_text_box = forms.text_box(
            parent=self.notebook_0.GetPage(1).GetWin(),
            value=self.Site,
            callback=self.set_Site,
            label="Site",
            converter=forms.str_converter()
        )
        self.notebook_0.GetPage(1).Add(self._Site_text_box)

# add astronomy inputs
        self._Integrations_01_text_box = forms.text_box(
            parent=self.notebook_0.GetPage(1).GetWin(),
            value=self.Integrations,
            callback=self.set_Integrations_01,
            label="Ave Time (s)",
            converter=forms.float_converter())
        self.notebook_0.GetPage(1).Add(self._Integrations_01_text_box)
        self._Azimuth_01_text_box = forms.text_box(
            parent=self.notebook_0.GetPage(1).GetWin(),
            value=self.Azimuth,
            callback=self.set_Azimuth_01,
            label="Azimuth",
            converter=forms.str_converter())
        self.notebook_0.GetPage(1).Add(self._Azimuth_01_text_box)
        self._Elevation_01_text_box = forms.text_box(
            parent=self.notebook_0.GetPage(1).GetWin(),
            value=self.Elevation,
            callback=self.set_Elevation_01,
            label="Elevation",
            converter=forms.str_converter())
        self.notebook_0.GetPage(1).Add(self._Elevation_01_text_box)
        self._fft_rate_01_text_box = forms.text_box(
            parent=self.notebook_0.GetPage(1).GetWin(),
            value=self.fft_rate,
            callback=self.set_fft_rate_01,
            label="FFT Rate",
            converter=forms.int_converter())
        self.notebook_0.GetPage(1).Add(self._fft_rate_01_text_box)
        self._Latitude_01_text_box = forms.text_box(
            parent=self.notebook_0.GetPage(1).GetWin(),
            value=self.Latitude,
            callback=self.set_Latitude_01,
            label="Latitude",
            converter=forms.float_converter()
        )
        self.notebook_0.GetPage(1).Add(self._Latitude_01_text_box)

        self._AveCount_01_text_box = forms.text_box(
            parent=self.notebook_0.GetPage(1).GetWin(),
            value=self.AveCount,
            label="Avg. Count",
            converter=forms.int_converter()
        )
        self.notebook_0.GetPage(1).Add(self._AveCount_01_text_box)
        self._FileCount_01_text_box = forms.text_box(
            parent=self.notebook_0.GetPage(1).GetWin(),
            value=self.FileCount,
            label="File Count",
            converter=forms.int_converter()
        )
        self.notebook_0.GetPage(1).Add(self._FileCount_01_text_box)
        self._SampleRate_01_text_box = forms.text_box(
            parent=self.notebook_0.GetPage(1).GetWin(),
            value=self.samp_rate,
            callback=self.set_samp_rate,
            label="Sample Rate",
            converter=forms.float_converter()
        )
        self.notebook_0.GetPage(1).Add(self._SampleRate_01_text_box)
        self._FrequencyMHz_01_text_box = forms.text_box(
            parent=self.notebook_0.GetPage(1).GetWin(),
            value=self.FrequencyStr,
            callback=self.set_Frequency,
            label="Frequency (MHz)",
            converter=forms.float_converter()
        )
        self.notebook_0.GetPage(1).Add(self._FrequencyMHz_01_text_box)
        self.set_Longitude_01(str(self.Longitude))
        self.set_fft_rate_01(str(self.fft_rate))
        self.set_Latitude_01(str(self.Latitude))
        # set integration time to a short time to update the displays
        self.set_Azimuth_01(self.Azimuth)
        self.set_Elevation_01(self.Elevation)
        self.set_SampleRate_01(self.SampleRate)
        # now set the desired integration time
        self.set_Integrations_01(str(self.Integrations))

        self._FrequencyChooser_0_chooser = forms.drop_down(
            parent=self.notebook_0.GetPage(1).GetWin(),
            value=self.FrequencyStr,
            callback=self.set_FrequencyChooser_0,
            label='Frequency "',
            choices=["90.9", "829", "1227.6", self.FrequencyStr, "1424.0",
                     "1436.2", "1575.42", "1666.0", "1710.0"],
            labels=['FM1', '3G', 'GPS L2', 'H1', 'HI-Off', 'Test', 'GPS L1', 'OH', '4G']
        )
        self.notebook_0.GetPage(1).Add(self._FrequencyChooser_0_chooser)

        gainCount = 0
#        devicename = self.rtlsdr_source_0.name()
#        print 'Device: ', devicename

#        nGAINs = len(GAINs)
        gains = [1., 1., 1.]

        ##################################################
        # Connections
        ##################################################
        self.connect((self.analog_noise_source_x_0, 0), (self.blocks_add_xx_0, 1))    
        self.connect((self.analog_sig_source_x_0, 0), (self.blocks_add_xx_0, 0))    
        self.connect((self.blocks_add_xx_0, 0), (self.low_pass_filter_0, 0))    
        self.connect((self.blocks_throttle_0, 0), (self.wxgui_fftsink2_0, 0))    
        self.connect((self.low_pass_filter_0, 0), (self.blocks_throttle_0, 0))    
#        self.connect((self.rtlsdr_source_0, 0), (self.wxgui_fftsink2_0, 0))

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = float(samp_rate)
        self.wxgui_fftsink2_0.set_sample_rate(self.samp_rate)
        self.low_pass_filter_0.set_taps(firdes.low_pass(1, self.samp_rate, .9e6, .1e6, firdes.WIN_HAMMING, 6.76))
        self.blocks_throttle_0.set_sample_rate(self.samp_rate)
        self.analog_sig_source_x_0.set_sampling_freq(self.samp_rate)
        self.SampleRate = samp_rate
        self.SampleRateStr = str(self.SampleRate*1.E-6) #MHz

    def readnotes(self, notefilename):
        """
        function to read a note file and set class values
        """
        if os.path.isfile(notefilename):
            noteFile = open(notefilename, 'r')
            notelines = noteFile.readlines()
            noteFile.close()
        # reread the last note file
            for line in notelines:
                parts = line.split(": ")
            #            print parts
                if parts[0] == "Note":
                    Note_01 = parts[1].strip()
                    print Note_01
                    self.Note_01 = Note_01
                if parts[0] == "Gain1":
                    self.gain1 = float(parts[1].strip())
                if parts[0] == "Gain2":
                    self.gain2 = float(parts[1].strip())
                if parts[0] == "Gain3":
                    self.gain3 = float(parts[1].strip())
                if parts[0] == "Observer":
                    self.Observer = parts[1].strip()
                if parts[0] == "Site":
                    self.Site = parts[1].strip()
                if parts[0] == "Az":
                    self.Azimuth = float(parts[1].strip())
                if parts[0] == "El":
                    self.Elevation = float(parts[1].strip())
#                    print "Elevation = ", self.Elevation
                if parts[0] == "Int":
                    self.Integrations = float(parts[1].strip())
#                    print 'Int==',self.Integrations
                if parts[0] == "Lon":
                    self.Longitude = float(parts[1].strip())
                if parts[0] == "Lat":
                    self.Latitude = float(parts[1].strip())
                if parts[0] == "Freq":
                    self.FrequencyStr = float(parts[1].strip())
                if parts[0] == "Rate":
                    self.SampleRate = float(parts[1].strip())
                if parts[0] == "FFTrate":
                    self.fft_rate = int(parts[1].strip())
# end of readnotes()

    def get_RF_Gain(self):
        """
        function to return Gain value in dB (float)
        """
        return self.RF_Gain

    def save_Notes(self):
        """
        function to write out all note values
        """
        outFile = open(self.NoteName, 'w')
        outFile.write('File: ' + self.NoteName + '\n')
        outFile.write('Date: ' + str(datetime.datetime.utcnow()) + '\n')
        outFile.write('Note: ' + self.Note_01 + '\n')
        outFile.write('Observer: ' + self.Observer + '\n')
        outFile.write('Site: ' + self.Site + '\n')
        outFile.write('Gain1: ' + str(self.gain1) + '\n')
        outFile.write('Gain2: ' + str(self.gain2) + '\n')
        outFile.write('Gain3: ' + str(self.gain3) + '\n')
        outFile.write('Freq: ' + str(self.FrequencyStr) + '\n')
        outFile.write('Rate: ' + str(self.SampleRate) + '\n')
        outFile.write('Az:   ' + str(self.Azimuth) + '\n')
        outFile.write('El:   ' + str(self.Elevation) + '\n')
        outFile.write('Int:  ' + str(self.Integrations) + '\n')
        outFile.write('Lon:  ' + str(self.Longitude) + '\n')
        outFile.write('Lat:  ' + str(self.Latitude) + '\n')
        outFile.write('FFTrate:  ' + str(self.fft_rate) + '\n')
        outFile.close()

    def set_Note_02(self, mystr):
        """
        The second note string records the gains of the amps
        """
        Note_02 = 'GAIN = '
        
#        ngains = len(self.rtlsdr_source_0.get_gain_names())
#        gainnames = self.rtlsdr_source_0.get_gain_names()
        self.gains = [1]
#        Note_02 = Note_02 + str(self.rtlsdr_source_0.get_gain(GAIN))
        Note_02 = "No simulated Gains"
        self.Note_02 = Note_02
        self.wxgui_fftsink2_0.win.set_gain_note(self.gains)
        self._Note_02_text_box.set_value(self.Note_02)
        self.save_Notes()

    def set_Note_01(self, Note_01):
        self.Note_01 = Note_01
        self.wxgui_fftsink2_0.win.set_note(str(Note_01))
        self._Note_01_text_box.set_value(self.Note_01)
        self.save_Notes()

    def set_Observer(self, Observer):
        self.Observer = Observer
        self.save_Notes()

    def set_Site(self, Site):
        self.Site = Site
        self.save_Notes()

    def set_gain1(self, gain1):
        """
        Set gain and Record gain setting in note file
        """
        gain1 = 1.
        print 'set_gain 1: ', gain1
        self.gain1 = gain1
        self._gain1_text_box.set_value(gain1)
        self.gains[0] = float(gain1)
        self.set_Note_02("")
        self.save_Notes()

    def set_gain2(self, gain2):
        """
        Record gain setting in note file
        """
        GAINs = ["LNA"]

    def set_gain3(self, gain3):
        """
        Set gain and Record gain setting in note file
        """
        GAINs = ["LNA"]

    def get_Note_01(self):
        """
        Return gain String
        """
        return self.Note_01

    def get_Note_02(self):
        return self.Note_02

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
        return self.FrequencyStr

    def set_Frequency(self, FrequencyMHz):
        self.FrequencyStr = str(FrequencyMHz)
        self.Frequency = float(FrequencyMHz)*1.E6
        self.wxgui_fftsink2_0.set_baseband_freq(self.Frequency)
#        self.rtlsdr_source_0.set_center_freq(self.Frequency)
#        centerfreq = self.rtlsdr_source_0.get_center_freq()
        centerfreq = self.Frequency
        
        if round(centerfreq) != round(self.Frequency):
            print "Error Setting Cente Frequency"
            print "Commanded Frequency: ", self.FrequencyStr
            print "Reported  Frequency:", centerfreq
        self.save_Notes()

    def set_FrequencyChooser_0(self, FrequencyChooser_0):
        print "Starting set_FrequencyChooser_0"
        self._FrequencyMHz_01_text_box.set_value(str(float(FrequencyChooser_0)))
        self.set_Frequency(float(FrequencyChooser_0))

    def set_Integrations_01(self, Integrations_01):
        self.Integrations = float(Integrations_01)
        self.wxgui_fftsink2_0.win.set_Integrations(float(Integrations_01))
#        self._Integrations_01_text_box.set_value(str(self.Integrations))
        self.save_Notes()

    def set_Azimuth_01(self, Azimuth_01):
        """
        set_Azimuth takes a user input string
        sets a float class value
        """
        self.Azimuth = float(Azimuth_01)
        self.wxgui_fftsink2_0.win.set_Azimuth(self.Azimuth)
        self._Azimuth_01_text_box.set_value(self.Azimuth)
        self.save_Notes()

    def set_Elevation_01(self, Elevation_01):
        """
        set_Elevation takes a user input string
        sets a float class value
        """
        self.Elevation = float(Elevation_01)
        self.wxgui_fftsink2_0.win.set_Elevation(self.Elevation)
        self._Elevation_01_text_box.set_value(str(self.Elevation))
        self.save_Notes()

    def set_AveCount_01(self, AveCount_01):
        self.AveCount = int(AveCount_01)
#        self._AveCount_01_text_box.set_value(str(self.AveCount))

    def set_FileCount_01(self, FileCount_01):
        self.FileCount = int(FileCount_01)
#        self._FileCount_01_text_box.set_value(str(self.FileCount))

    def set_Longitude_01(self, Longitude_01):
        self.Longitude = float(Longitude_01)
        self.wxgui_fftsink2_0.win.set_Longitude(float(Longitude_01))
        self.save_Notes()

    def set_fft_rate_01(self, fft_rate_01):
        self.fft_rate = int(fft_rate_01)
        self.save_Notes()

    def set_Latitude_01(self, Latitude_01):
        self.Latitude = float(Latitude_01)
        self.wxgui_fftsink2_0.win.set_Latitude(Latitude_01)
        self.save_Notes()

    def set_SampleRate_01(self, SampleRate_01):
        self.SampleRate = float(SampleRate_01)
#        self.rtlsdr_source_0.set_sample_rate(self.SampleRate)
#        samplerate = self.rtlsdr_source_0.get_sample_rate()
        samplerate = self.SampleRate
        if samplerate != self.SampleRate:
            print "Error setting Sample rate"
            print "Commanded Rate: ",self.SampleRate
            print "Reported  Rate: ",samplerate
        self.wxgui_fftsink2_0.win.set_SampleRate(float(SampleRate_01))
        self.save_Notes()

    def get_SampleRate(self):
        """
        return a class value
        """
        return self.SampleRate

    def get_Latitude(self):
        """
        return a class value
        """
        return self.Latitude

    def get_Longitude(self):
        return self.Longitude

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
