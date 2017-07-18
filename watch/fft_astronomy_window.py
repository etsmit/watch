"""
Radio Astronomy Sink is based on Gnu Radio's fft sink.
The modules track the averaging of spectra and add information
necessary to use the spectra averaged for astronomy.

Glen Langston, 2017 try to fix save of average
Glen Langston, 2016 October 11 -- fix Tsys cal
Glen Langston, 2016 October 7 -- Code cleanup
HISTORY
17JAN10 GIL remove use of the OFF spectra as this seems to be adding trouble
"""

##################################################
# Imports
##################################################
#import time
import datetime
import copy
import plotter
import common
import wx
import numpy
import pubsub
from constants import *
from gnuradio import gr #for gr.prefs
import forms
import radioastronomy
import tsys

##################################################
# Constants
##################################################
SLIDER_STEPS = 51
AVG_ALPHA_MIN_EXP, AVG_ALPHA_MAX_EXP = -3, 0
PERSIST_ALPHA_MIN_EXP, PERSIST_ALPHA_MAX_EXP = -2, 0
DEFAULT_WIN_SIZE = (700, 600)
DEFAULT_FRAME_RATE = gr.prefs().get_long('wxgui', 'fft_rate', 2441)
DB_DIV_MIN = 0.5
DB_DIV_MAX = 1000
EPSILON = 1.E-10
FFT_PLOT_COLOR_SPEC = (0.4, 0.3, 0.4)
PEAK_VALS_COLOR_SPEC = (0.3, 0.8, 0.3)
EMPTY_TRACE = list()
TRACES = ('Ave', 'Cold', 'Hot', 'Off', 'Temp')
NPLOTTYPES = 3
PLOTLOG = 0
PLOTLINEAR = 1
PLOTTSYS = 2
PLOTTYPES = ('(db)', '(counts)', '(Kelvins)')
TRACES_COLOR_SPEC = {
    'Ave': (0.1, 0.9, 0.1),
    'Cold': (0.1, 0.1, 0.7),
    'Hot': (1.0, 0.1, 0.1),
    'Off': (0.5, 0.5, 0.1),
    'Temp': (0.2, 0.4, 0.2)
}

class control_panel(wx.Panel):
##################################################
# FFT window control class control_panel(wx.Panel):
    """
    A control panel with wx widgits to control the plotter and fft block chain.
    """

    def __init__(self, parent):
        """
        Create a new control panel.

        Args:
            parent: the wx parent window
        """
        self.parent = parent
        wx.Panel.__init__(self, parent, style=wx.SUNKEN_BORDER)
        parent[SHOW_CONTROL_PANEL_KEY] = True
        parent.subscribe(SHOW_CONTROL_PANEL_KEY, self.Show)
        control_box = wx.BoxSizer(wx.VERTICAL)
        control_box.AddStretchSpacer()
        #checkboxes for average and peak hold
        options_box = forms.static_box_sizer(
            parent=self, sizer=control_box, label='Trace Options',
            bold=True, orient=wx.VERTICAL,
            )
        forms.check_box(
            sizer=options_box, parent=self, label='Peak Hold',
            ps=parent, key=PEAK_HOLD_KEY,
            )
        forms.check_box(
            sizer=options_box, parent=self, label='Record',
            ps=parent, key=RECORD_KEY,
            )
#        forms.check_box(
#            sizer=options_box, parent=self, label='Average',
#            ps=parent, key=AVERAGE_KEY,
#            )
        #static text and slider for averaging
#        avg_alpha_text = forms.static_text(
#            sizer=options_box, parent=self, label='Avg Alpha',
#            converter=forms.float_converter(lambda x: '%.4f'%x),
#            ps=parent, key=AVG_ALPHA_KEY, width=50,
#        )
#        avg_alpha_slider = forms.log_slider(
#            sizer=options_box, parent=self,
#            min_exp=AVG_ALPHA_MIN_EXP,
#            max_exp=AVG_ALPHA_MAX_EXP,
#            num_steps=SLIDER_STEPS,
#            ps=parent, key=AVG_ALPHA_KEY,
#        )
#        for widget in (avg_alpha_text, avg_alpha_slider):
#            parent.subscribe(AVERAGE_KEY, widget.Enable)
#            widget.Enable(parent[AVERAGE_KEY])
#            parent.subscribe(AVERAGE_KEY, widget.ShowItems)
            #allways show initially, so room is reserved for them
#            widget.ShowItems(True) # (parent[AVERAGE_KEY])

#        parent.subscribe(AVERAGE_KEY, self._update_layout)

#        forms.check_box(
#            sizer=options_box, parent=self, label='Persistence',
#            ps=parent, key=USE_PERSISTENCE_KEY,
#        )
        #static text and slider for persist alpha
#        persist_alpha_text = forms.static_text(
#            sizer=options_box, parent=self, label='Persist Alpha',
#            converter=forms.float_converter(lambda x: '%.4f'%x),
#            ps=parent, key=PERSIST_ALPHA_KEY, width=50,
#            )
#        persist_alpha_slider = forms.log_slider(
#            sizer=options_box, parent=self,
#            min_exp=PERSIST_ALPHA_MIN_EXP,
#            max_exp=PERSIST_ALPHA_MAX_EXP,
#            num_steps=SLIDER_STEPS,
#            ps=parent, key=PERSIST_ALPHA_KEY,
#        )
#        for widget in (persist_alpha_text, persist_alpha_slider):
#            parent.subscribe(USE_PERSISTENCE_KEY, widget.Enable)
#            widget.Enable(parent[USE_PERSISTENCE_KEY])
#            parent.subscribe(USE_PERSISTENCE_KEY, widget.ShowItems)
#            #allways show initially, so room is reserved for them
#           widget.ShowItems(True) # (parent[USE_PERSISTENCE_KEY])

        #trace menu
        for trace in TRACES:
            trace_box = wx.BoxSizer(wx.HORIZONTAL)
            options_box.Add(trace_box, 0, wx.EXPAND)
            forms.check_box(
                sizer=trace_box, parent=self,
                ps=parent, key=TRACE_SHOW_KEY+trace,
                label='%s'%trace,
                )
            trace_box.AddSpacer(10)
            forms.single_button(
                sizer=trace_box, parent=self,
                ps=parent, key=TRACE_STORE_KEY+trace,
                label='Store', style=wx.BU_EXACTFIT,
                )
            trace_box.AddSpacer(10)
        # end for all traces; now add a refresh display button
        loglinear_box = wx.BoxSizer(wx.HORIZONTAL)
        options_box.Add(loglinear_box, 0, wx.EXPAND)

#        parent.subscribe(USE_PERSISTENCE_KEY, self._update_layout)
#        widget.ShowItems(True) # (parent[AVERAGE_KEY])

        #radio buttons for div size
        control_box.AddStretchSpacer()
        y_ctrl_box = forms.static_box_sizer(
            parent=self, sizer=control_box, label='Axis Options',
            bold=True, orient=wx.VERTICAL,
        )
        forms.incr_decr_buttons(
            parent=self, sizer=y_ctrl_box, label='dB/Div',
            on_incr=self._on_incr_db_div, on_decr=self._on_decr_db_div,
        )
        #ref lvl buttons
        forms.incr_decr_buttons(
            parent=self, sizer=y_ctrl_box, label='Ref Level',
            on_incr=self._on_incr_ref_level,
            on_decr=self._on_decr_ref_level,
        )
        y_ctrl_box.AddSpacer(2)
        #autoscale
        forms.single_button(
            sizer=y_ctrl_box, parent=self, label='Autoscale',
            callback=self.parent.autoscale,
        )
        forms.single_button(
            sizer=y_ctrl_box, parent=self, label='Log/Linear/Kelvins',
            callback=self.parent.loglinear,
        )
        #run/stop
        control_box.AddStretchSpacer()
        forms.toggle_button(
            sizer=control_box, parent=self,
            true_label='Stop', false_label='Run',
            ps=parent, key=RUNNING_KEY,
            )
        #set sizer
        self.SetSizerAndFit(control_box)

        #mouse wheel event
        def on_mouse_wheel(event):
            """
            on mouse wheel zoom in and out on the spectrum
            """
            if event.GetWheelRotation() < 0:
                self._on_incr_ref_level(event)
            else:
                self._on_decr_ref_level(event)
        parent.plotter.Bind(wx.EVT_MOUSEWHEEL, on_mouse_wheel)

    ##################################################
    # Event handlers
    ##################################################
    def _on_incr_ref_level(self, event):
        self.parent[REF_LEVEL_KEY] = self.parent[REF_LEVEL_KEY] + self.parent[Y_PER_DIV_KEY]
    def _on_decr_ref_level(self, event):
        self.parent[REF_LEVEL_KEY] = self.parent[REF_LEVEL_KEY] - self.parent[Y_PER_DIV_KEY]
    def _on_incr_db_div(self, event):
        self.parent[Y_PER_DIV_KEY] = min(DB_DIV_MAX,
                                         common.get_clean_incr(self.parent[Y_PER_DIV_KEY]))
    def _on_decr_db_div(self, event):
        self.parent[Y_PER_DIV_KEY] = max(DB_DIV_MIN,
                                         common.get_clean_decr(self.parent[Y_PER_DIV_KEY]))
    ##################################################
    # subscriber handlers
    ##################################################
    def _update_layout(self, key):
        """
        Need to know that the visability or size of something has changed
        """
        self.parent.Layout()

class fft_astronomy_window(wx.Panel, pubsub.pubsub):
    """
    FFT window with plotter and control panel
    """
    def __init__(self,
                 parent,
                 controller,
                 size,
                 title,
                 real,
                 fft_size,
                 baseband_freq,
                 sample_rate_key,
                 y_per_div,
                 y_divs,
                 ref_level,
                 average_key,
                 avg_alpha_key,
                 peak_hold,
                 msg_key,
                 use_persistence,
                 persist_alpha):
        """
        init function defines many properties of the spectra
        """
        pubsub.pubsub.__init__(self)
        #setup
        self.once = False  # flag that no plot execution has yet occurred
#        self.once = True  # flag that no plot execution has yet occurred
        self.samples = EMPTY_TRACE
        self.real = real
        self.size = size                 # window size
        self.maxblock = 0
        self.fft_size = int(fft_size)
        print "fft size: %d" % self.fft_size
        # loop sampels processes all samples in a block
        self.loopSpectrum = numpy.zeros(self.fft_size+1)
        self.loopLinear = numpy.zeros(self.fft_size+1)
        self.loopCount = 0
        self.plotSamples = numpy.zeros(self.fft_size+1)
        self._reset_peak_vals()
#        self._traces = dict()
        self._tracesLOG = dict()
        self._tracesLIN = dict()
        self._tracesK = dict()
        self.aveCount = 0  # number of spectra averaged
        self.writecount = 0  # count files written in a row
#        self.minLoopCount = int(2500) # was 250
#        self.maxLoopCount = int(2500) # was 500
        self.minLoopCount = int(2500) # was 250
        self.nPerPlotUpdate = self.minLoopCount
        self.plottype = PLOTLOG
        self.lastplottype = PLOTLOG
        self.aveSpectrum = numpy.zeros(self.fft_size+1)
        self.aveLinear = numpy.zeros(self.fft_size+1)
        self.aveRecent = numpy.zeros(self.fft_size+1)
        self.linRecent = numpy.zeros(self.fft_size+1) # spectrum to keep for recording 
        self.ave = radioastronomy.Spectrum()   # define class to output
        self.temp = radioastronomy.Spectrum()   # define class to output
        self.tsys = tsys.Tsys()
        self.lastRecord = False
        self.lat = 38.4331
        self.lon = -79.8397
        self.Thot = 285.
        self.Tcold = 15.
        self.plotfactor = 1.0E7 # put counts in rough range of db
        self.sampleRate = 2.8e6
        self.az = 216.0
        self.el = 45.0
        self.gains = [1., 1., 1.]
        self.last_y_divs = 0
        self.last_y_per_div = 0
        self.last_ref_level = 0
        self.peakhold = peak_hold
        self.peak_vals = EMPTY_TRACE
        #
        self.integrations = datetime.timedelta(seconds=30)
        #setup for recording data at regular intervals
        self.lasttime = datetime.datetime.utcnow()
        self.lastPrintTime = self.lasttime
        #proxy the keys
        self.proxy(MSG_KEY, controller, msg_key)
        self.proxy(AVERAGE_KEY, controller, average_key)
        self.proxy(AVG_ALPHA_KEY, controller, avg_alpha_key)
        self.proxy(SAMPLE_RATE_KEY, controller, sample_rate_key)
        #initialize values
        self[PEAK_HOLD_KEY] = peak_hold
        self[NOTE_KEY] = ' '
        self[GAIN_KEY] = ' '
        self[RECORD_KEY] = False
        self[Y_PER_DIV_KEY] = y_per_div
        self[Y_DIVS_KEY] = y_divs
        self[X_DIVS_KEY] = 8 #approximate
        self[REF_LEVEL_KEY] = ref_level
        self[BASEBAND_FREQ_KEY] = baseband_freq
        self[RUNNING_KEY] = True
        self[USE_PERSISTENCE_KEY] = use_persistence
        self[PERSIST_ALPHA_KEY] = persist_alpha
        self.datadirectory = "../data/"
        self.tracedirectory = "./"
        self.last_trace = TRACES[0] # new

        for trace in TRACES:
            #a function that returns a function
            #so the function wont use local trace
            def new_store_trace(my_trace):
                """
                store new trace
                """
                def store_trace(*args):
                    """
                    Def to store the average  at trace in an file
                    """
                    self.compute_traces()
                    self.trace_save(my_trace)
                return store_trace

            def new_toggle_trace(my_trace):
                """
                turn trace on/off
                """
                def toggle_trace(toggle):
                    """
                    automatic store if toggled on and empty trace
                    """
                    if toggle:
                        self.show_trace( my_trace)
                return toggle_trace

#            self._traces[trace] = EMPTY_TRACE
            self._tracesLIN[trace] = EMPTY_TRACE
            self._tracesLOG[trace] = EMPTY_TRACE
            self._tracesK[trace] = EMPTY_TRACE
            self[TRACE_STORE_KEY+trace] = False
            self[TRACE_SHOW_KEY+trace] = False
            self.subscribe(TRACE_STORE_KEY+trace, new_store_trace(trace))
            self.subscribe(TRACE_SHOW_KEY+trace, new_toggle_trace(trace))

        #init panel and plot
        wx.Panel.__init__(self, parent, style=wx.SIMPLE_BORDER)
        self.plotter = plotter.channel_plotter(self)
        self.plotter.SetSize(wx.Size(*size))
        self.plotter.SetSizeHints(*size)
        self.plotter.set_title(title)
        self.plotter.enable_legend(True)
        self.plotter.enable_point_label(True)
        self.plotter.enable_grid_lines(True)
        self.plotter.set_use_persistence(use_persistence)
        self.plotter.set_persist_alpha(persist_alpha)
        #setup the box with plot and controls
        self.control_panel = control_panel(self)
        main_box = wx.BoxSizer(wx.HORIZONTAL)
        main_box.Add(self.plotter, 1, wx.EXPAND)
        main_box.Add(self.control_panel, 0, wx.EXPAND)
        self.SetSizerAndFit(main_box)
        #register events
        self.subscribe(AVERAGE_KEY, self._reset_peak_vals)
        self.subscribe(MSG_KEY, self.handle_msg)

        for key in (BASEBAND_FREQ_KEY, Y_PER_DIV_KEY, X_DIVS_KEY, Y_DIVS_KEY, REF_LEVEL_KEY):
            self.subscribe(key, self.update_grid)
        self.subscribe(USE_PERSISTENCE_KEY, self.plotter.set_use_persistence)
        self.subscribe(PERSIST_ALPHA_KEY, self.plotter.set_persist_alpha)
        #initial update; read previous values, the plot
        self.restore_traces()
        self.update_grid()

    def trace_save(self, trace):
        """
        show and store named traces
        """
        # create a spectrum structure
        self.last_trace = trace
        if self.el < 0:
            outname = trace + ".hot"
        elif self.el == 0:
            outname = trace + ".off"
        else:
            outname = trace + ".ast"

        if trace == 'Ave':
            self.ave.ydataA = copy.deepcopy(self.linRecent[:self.fft_size])
            self.ave.write_ascii_file(self.tracedirectory, outname)
        elif trace == 'Hot':
            self.tsys.hot = copy.deepcopy(self.ave)
            self.tsys.hot.ydataA = copy.deepcopy(self.linRecent[:self.fft_size])
            self.tsys.hot.write_ascii_file(self.tracedirectory, outname)
            print 'Hot: Min, Max: ', min(self.tsys.hot.ydataA), max(self.tsys.hot.ydataA)
            self.compute_hot()
        elif trace == 'Cold':
            self.tsys.cold = copy.deepcopy(self.ave)
            self.tsys.cold.ydataA = copy.deepcopy(self.linRecent[:self.fft_size])
            self.tsys.cold.write_ascii_file(self.tracedirectory, outname)
            print 'Cold: Min, Max: ', min(self.tsys.cold.ydataA), max(self.tsys.cold.ydataA)
            self.compute_cold()
        elif trace == 'Off':
            self.tsys.off = copy.deepcopy(self.ave)
            self.tsys.off.ydataA = copy.deepcopy(self.linRecent[:self.fft_size])
            self.tsys.off.write_ascii_file(self.tracedirectory, outname)
            self.compute_off()
        else:
            self.temp = copy.deepcopy(self.ave)
            self.temp.ydataA = copy.deepcopy(self.linRecent[:self.fft_size])
            self.temp.write_ascii_file(self.tracedirectory, outname)
            self.compute_temp()

        print 'Last Trace saved: ' + self.last_trace

    def show_trace(self, my_trace):
        """
        Extract the trace from the associated spectrum
        format for plot type and show
        """
        # copy the correct samples (linear scale)
        if my_trace == 'Hot':
            ssamples = self.tsys.hot.ydataA
        elif my_trace == 'Cold':
            ssamples = self.tsys.cold.ydataA
        elif my_trace == 'Off':
            ssamples = self.tsys.off.ydataA
        elif my_trace == 'Ave':
            if len(self.linRecent) < 1:
                return
            ssamples = self.linRecent[0:self.fft_size]
        else:
            ssamples = self.temp.ydataA

        self._tracesLIN[my_trace] = self.plotfactor * copy.deepcopy(ssamples)
        print '%s: Min %8.2f, Max: %8.2f ' % (my_trace, self.plotfactor*min(ssamples), self.plotfactor*max(ssamples))
        indexs = ssamples < EPSILON
        ssamples[indexs] = EPSILON
        dbsamples = 10. * numpy.log10(ssamples) # convert to  db
        self._tracesLOG[my_trace] = copy.deepcopy( dbsamples)
        self._tracesK[my_trace] = self.tsys.tsky(ssamples)

        self.plotter.update()

    def compute_ave(self):
        """
        Compute the log, linear and K plots from current hot, cold, off and temp traces
        """
        samples = copy.deepcopy(self.linRecent[:self.fft_size])
        indexs = samples < EPSILON
        samples[indexs] = EPSILON
        self.linRecent = copy.deepcopy(samples)
        self._tracesLIN['Ave'] = self.plotfactor*samples
        dbsamples = 10. * numpy.log10(samples)  # convert back to dB
        self._tracesLOG['Ave'] = copy.deepcopy(dbsamples)
        self.aveRecent = copy.deepcopy(dbsamples)
#        print "%s Spec: %8.3lf db %8.1f" % ('Ave', dbsamples[500], self.plotfactor*samples[500])
        print "%s Spec: Min, Max: %8.3lf,%8.3lf db" % ('Ave', min(dbsamples), max(dbsamples))
        self._tracesK['Ave'] = self.tsys.tsky(samples)

    def compute_hot(self):
        """
        Compute traces for Hot load spectrum.
        This proceduce is only run when the hot load spectrum is saved or restored.
        """
        samples = self.tsys.hot.ydataA[:self.fft_size]
        indexs = samples < EPSILON
        samples[indexs] = EPSILON
        self._tracesLIN['Hot'] = self.plotfactor*samples
        dbsamples = 10. * numpy.log10(samples)  # convert back to dB
        self._tracesLOG['Hot'] = copy.deepcopy(dbsamples)
        self._tracesK['Hot'] = self.tsys.tsky(samples)

    def compute_cold(self):
        """
        Compute traces for Cold load spectrum.
        This proceduce is only run when the Cold load spectrum is saved or restored.
        """
        samples = self.tsys.cold.ydataA[:self.fft_size]
        self._tracesLIN['Cold'] = self.plotfactor*samples
        indexs = samples < EPSILON
        samples[indexs] = EPSILON
        dbsamples = 10. * numpy.log10( samples)  # convert back to dB
        self._tracesLOG['Cold'] = copy.deepcopy(dbsamples)
        self._tracesK['Cold'] = self.tsys.tsky(samples)
        self.tsys.gaincalc()
        print 'Hot-Cold Load Tsys: %7.2f Kelvins' % (self.tsys.tmedian())

    def compute_off(self):
        samples = self.tsys.off.ydataA[:self.fft_size]
        self._tracesLIN['Off'] = self.plotfactor*samples
        indexs = samples < EPSILON
        samples[indexs] = EPSILON
        dbsamples = 10. * numpy.log10( samples)  # convert back to dB
        self._tracesLOG['Off'] = copy.deepcopy( dbsamples)
#        print "%s Spec: %8.3lf db %8.1f" % ('Off', dbsamples[500], self.plotfactor*samples[500])
        self._tracesK['Off'] = self.tsys.tsky(samples)

    def compute_temp(self):
        samples = self.temp.ydataA[:self.fft_size]
        self._tracesLIN['Temp'] = self.plotfactor*samples
        # find and remove illegal values
        indexs = samples < EPSILON
        samples[indexs] = EPSILON
        dbsamples = 10. * numpy.log10( samples)  # convert back to dB
        self._tracesLOG['Temp'] = copy.deepcopy(dbsamples)
#        print "%s Spec: %8.3lf db %8.1f" % ('Temp', dbsamples[500], self.plotfactor*samples[500])
        self._tracesK['Temp'] = self.tsys.tsky(samples)

    def compute_traces(self):
        """
        Compute the log, linear and K plots from current hot, cold, off and temp traces
        """
        self.compute_hot()
        self.compute_cold()
        self.compute_off()
        self.compute_temp()

    def restore_traces(self):
        """
        Read the last stored hot, cold, off and temp traces
        """
        avename = self.tracedirectory + "Ave.ast"
        self.ave.read_spec_ast(avename)
        if len( self.ave.ydataA) < self.fft_size:
            print "Error reading Average spectrum, len = ",len(self.ave.ydataA)
            self.ave.ydataA = numpy.zeros( self.fft_size) + EPSILON
        self.linRecent = copy.deepcopy(self.ave.ydataA[:self.fft_size])
        self.compute_ave()

        hotloadname = self.tracedirectory + "Hot.hot"
        self.tsys.readhot(hotloadname)
        if len( self.tsys.hot.ydataA) < self.fft_size:
            print "Error reading Hot spectrum, len = ",len(self.tsys.hot.ydataA)
            self.tsys.hot.ydataA = numpy.zeros( self.fft_size) + EPSILON

        coldname = self.tracedirectory + "Cold.ast"
        self.tsys.readcold(coldname)
        if len( self.tsys.cold.ydataA) < self.fft_size:
            print "Error reading Cold spectrum, len = ",len(self.tsys.cold.ydataA)
            self.tsys.cold.ydataA = numpy.zeros( self.fft_size) + EPSILON

        offname = self.tracedirectory + "Off.ast"
        self.tsys.readoff(offname)
        if len( self.tsys.off.ydataA) < self.fft_size:
            print "Error reading Off spectrum, len = ",len(self.tsys.off.ydataA)
            self.tsys.off.ydataA = numpy.zeros( self.fft_size) + EPSILON

        tempname = self.tracedirectory + "Temp.ast"
        self.temp.read_spec_ast(tempname)
        if len( self.temp.ydataA) < self.fft_size:
            print "Error reading Temp spectrum, len = ",len(self.temp.ydataA)
            self.temp.ydataA = numpy.zeros( self.fft_size) + EPSILON

        self.compute_traces()

    def set_callback(self, callb):
        """
        return from call
        """
        self.plotter.set_callback(callb)

    def autoscale(self, *args):
        """
        Autoscale the fft plot to the last frame.
        Set the dynamic range and reference level.
        """
        if not len(self.plotSamples):
            return

        min_level = min(self.plotSamples[2:(self.fft_size-2)])
        max_level = max(self.plotSamples[2:(self.fft_size-2)])
        self[Y_PER_DIV_KEY] = common.get_clean_num(1+(max_level - min_level)/self[Y_DIVS_KEY])
        print 'Autoscale: Min: %8.2f, Max: %8.2f ' % (min_level, max_level)

        # for unusually small ranges use smaller factors of two.
        if (max_level - min_level) < 0.1:
            self[Y_PER_DIV_KEY] = .125
        elif (max_level - min_level) < 1.:
            self[Y_PER_DIV_KEY] = .25
        elif (max_level - min_level) < 10.:
            self[Y_PER_DIV_KEY] = .5

        # the reference level is the top of the plot, move top up so there is headroom.
        self[REF_LEVEL_KEY] = max_level + (5.*self[Y_PER_DIV_KEY])

    def loglinear(self, *args):
        """
        Toggles the log/linear scale
        """
        self.plottype = self.plottype + 1
        if self.plottype >= NPLOTTYPES:
            self.plottype = 0

        self.compute_traces()
        print 'Plotting: ', PLOTTYPES[self.plottype]

    def _reset_peak_vals(self, *args):
        """
        Reset peak values by seting the trace to empty
        """
        self.peak_vals = EMPTY_TRACE

    def handle_msg(self, msg):
        """
        process one fft block of messages.  This is the main processing loop.
        """
        if not self[RUNNING_KEY]:
            return

#        allsamples = numpy.fromstring(msg, numpy.float32)
# only take the first message
#        allsamples = numpy.fromstring(msg, numpy.float32)[:self.fft_size]
        allsamples = numpy.fromstring(msg, numpy.float32)
        nsamples = len(allsamples)
        nblock = nsamples/self.fft_size
        if nblock > self.maxblock:
            print 'New Max number of blocks: ',nblock
            self.maxblock=nblock
        istep = self.fft_size
        istep2 = istep/2
        samples = allsamples[:istep]
        #convert to floating point numbers
        samples = numpy.concatenate((allsamples[istep2:istep], allsamples[0:istep2+1]))
#        samples = numpy.concatenate((allsamples[(istep+1)/2:], allsamples[:(istep+2)/2]))
        psamples = pow(10., 0.1*samples)        # compute the linear power

        if not self.once:
            print "msg size: %d compared to fft_size %d" % (nsamples, self.fft_size)
            print "samples in one block %d, after re-arange %d" % (istep, len(samples))

        # every time the record button changes, reset the averages
        if self.lastRecord != self[RECORD_KEY]:
            self.aveCount = 0                    # flag restart sum
            self.loopCount = 0
            # get the current date, time
            now = datetime.datetime.utcnow()
            self.lasttime = now                  # start now
            self.lastRecord = self[RECORD_KEY]
            if self[RECORD_KEY]:
                outline = 'Starting recording at %s' % (now.isoformat())
            else:
                outline = 'Recording stopped'
                self.writecount = 0
            print outline

        # determine how many more blocks are in the msg
#        nblock = min(nblock,1)
        if nblock > self.maxblock:
            print 'New Max number of blocks: ',nblock
            self.maxblock=nblock
        istep = self.fft_size
        sumsamples = samples
        istart = istep
        istop = istart + istep # length of fft
        # first block is already computed and swapped
        istart2 = istart + istep2
        istop2 = istart + istep2 + 1
        for iii in range(1, nblock):
            # This transfere works only for a complex FFT
            # order is move middle-end to beginning, followed by beginning-middle
#            middle = (allsamples[istart] + allsamples[istop-1])*.5
            samples = numpy.concatenate((allsamples[istart2:istop], allsamples[istart:istop2]))
#            samples[istep2] = middle
            sumsamples = sumsamples + samples
            if not self.once:
                print "start, 2: %d,%d stop, 2: %d,%d " % (istart, istart2, istop, istop2)
                print "sample size, sum: %d,%d: " % (len(samples), len(sumsamples))
                self.once = True
            istart = istart + istep
            istart2 = istart2 + istep
            istop = istop + istep
            istop2 = istop2 + istep
            # end of sample sum loop
        # if restarting the sump, init
        psamples = 0.1 * sumsamples/float(nblock)
        # compute the linear power for the average of the ave of the block
        psamples = pow(10., psamples)        # compute the linear power
        if self.loopCount == 0:
            self.loopLinear = copy.deepcopy(psamples*nblock) # linear average done, scale
        else:
            self.loopLinear = self.loopLinear + (psamples*nblock)
        self.loopCount = self.loopCount + nblock

        self.once = True
        #peak hold calculation
        if self[PEAK_HOLD_KEY]:
            if not self.peakhold:    # if just starting to keep peak hold data
                self.peak_vals = psamples
            self.peakhold = True
            self.peak_vals = numpy.maximum(psamples, self.peak_vals)
        else:   # if there was peak hold data, and now clearing; clear peak data once
            if self.peakhold:
                self._reset_peak_vals()
                self.plotter.clear_waveform(channel='Peak')
                self.peak_vals = EMPTY_TRACE
                self.peakhold = False

        # this loop reduces the display cpu usage
        if self.loopCount > self.nPerPlotUpdate:  #if time to plot and check for average
            # a complete block of spectra summed, add to accumulation
            if self.aveCount <= 0:                   # if restarting sum
                self.aveLinear = copy.deepcopy(self.loopLinear)
                self.aveCount = self.loopCount
#                print "Initializing ave sum ", self.aveCount
            else:                                    # else continuue sum
                self.aveLinear = self.aveLinear + self.loopLinear
                self.aveCount = self.aveCount + self.loopCount
            # get the current date, time; has enough time passed?
            now = datetime.datetime.utcnow()
            dt = now - self.lasttime                 # calc time past
            # time to produce new average plots and record (?)
            if dt > self.integrations:               # if more than required time
                self.aveLinear = self.aveLinear / float(self.aveCount)
                self.aveSpectrum = 10. * numpy.log10( self.aveLinear)
                self.aveRecent = copy.deepcopy(self.aveSpectrum)
                self.linRecent = copy.deepcopy(self.aveLinear) # save for writing
                # now the averages are complete; if writing write a file
                self.ave.writecount = self.writecount
                # compute duration
                self.ave.durationSec = dt.total_seconds()
                dtover2 = datetime.timedelta(seconds=self.ave.durationSec/2.)
                self.ave.utc = self.lasttime + dtover2 # ave time is start+half duration
                # always write the linear average, independent of plot type
                self.ave.ydataA = copy.deepcopy(self.aveLinear[:self.fft_size])
                self.ave.count = self.aveCount
                self.ave.centerFreqHz = float(self[BASEBAND_FREQ_KEY])
                self.ave.bandwidthHz = float(self[SAMPLE_RATE_KEY])
                self.ave.deltaFreq = float(self[SAMPLE_RATE_KEY])/float(self.ave.nChan)
                self.ave.noteA = str(self[NOTE_KEY])
                self.ave.gains = self.gains
                self.ave.telaz = float(self.az)
                self.ave.telel = float(self.el)
                self.ave.tellon = float(self.lon)
                self.ave.tellat = float(self.lat)
                self.ave.azel2radec()
#                print "Integration completed: ", self.writecount, self.aveCount, self.integrations
#                print "Integration completed: ", self.lasttime, now

                if self[RECORD_KEY]:
                    self.writecount = self.writecount + 1
                    self.ave.write_ascii_ast(self.datadirectory)
                else:                    # else not recording, compute ave power
                    if self.plottype == PLOTLOG:
                        asamples = self.aveRecent
                    elif self.plottype == PLOTLINEAR:
                        asamples = self.plotfactor * self.aveLinear
                    else:
                        asamples = self.tsys.tsky(self.aveLinear)
                    anave = 0.0
                    for iii in range(100):
                        anave = anave + asamples[iii+100]
                    for iii in range(100):
                        anave = anave + asamples[iii+900]
                    anave = anave/200.0
                    anmax = max(asamples[10:(self.fft_size-10)])
                    anmin = min(asamples[10:(self.fft_size-10)])
                    aform = "Not recording! Min: %7.2f, Ave: %7.2f, Max: %7.2f %s"
                    print aform % (anmin, anave, anmax, PLOTTYPES[self.plottype])
                    self.writecount = 0

                # update the plot in this section
                if self.plottype == PLOTLINEAR:
                    self._tracesLIN['Ave'] = self.plotfactor * self.linRecent
                elif self.plottype == PLOTTSYS:
                    self._tracesK['Ave'] = self.tsys.tsky(self.linRecent)
                else:
                    self._tracesLOG['Ave'] = 10. * numpy.log10( self.linRecent)

                self.aveCount = 0      # completed average, flag new sum and reset start timer.
                self.lasttime = self.lasttime + self.integrations

                # update the plot in this section            # time to update the plot
            # compute short term average plot
            self.loopLinear = self.loopLinear/float(self.loopCount)
            if self.plottype == PLOTLOG:
                self.loopSpectrum = 10. * numpy.log10( self.loopLinear)
                self.plotSamples = self.loopSpectrum
            elif self.plottype == PLOTLINEAR:
                self.plotSamples = self.plotfactor * self.loopLinear
            else:
                self.plotSamples = self.tsys.tsky(self.loopLinear)  # convert to Kelvins
            self.plotter.set_waveform(
                channel='FFT',
                samples=self.plotSamples,
                color_spec=FFT_PLOT_COLOR_SPEC,
                )

            # if plotting peak hold
            if self.peakhold:
                peaksamples = self.peak_vals
                if self.plottype == PLOTLINEAR:
                    self.plotter.set_waveform(
                        channel='Peak',
                        samples=self.plotfactor*peaksamples,
                        color_spec=PEAK_VALS_COLOR_SPEC,
                        )
                elif self.plottype == PLOTLOG:
                    dbsamples = 10. * numpy.log10( peaksamples)
                    self.plotter.set_waveform(
                        channel='Peak',
                        samples=dbsamples,
                        color_spec=PEAK_VALS_COLOR_SPEC,
                        )
                else:
                    peaktemp = self.tsys.tsky(peaksamples)
                    self.plotter.set_waveform(
                        channel='Peak',
                        samples=peaktemp,
                        color_spec=PEAK_VALS_COLOR_SPEC,
                        )
            # display the average as trace AVE
            if self.plottype != self.lastplottype:
                self.autoscale()
                self.lastplottype = self.plottype
            self.update_grid()
            self.plotter.update()
            # completed plotting of one set of integrations; start new sum
            self.loopCount = 0

    def set_note(self, msg):
        """
        transfer the note to the internal memory
        """
        print 'Setting Obs Note  = %s' % (msg)
        self[NOTE_KEY] = str(msg)

    def set_gain_note(self, gains):
        """
        transfer the note to the internal memory
        """
#        print 'Setting Gain  = %f' % gains[0]
        self.gains = gains

    def set_Longitude(self, longitude):
        """
        transfer geographic longitude of observer (degrees)
        """
        self.lon = float(longitude)
        print 'Setting Geographic Longitude = %f (d)' % (self.lon)

    def set_Latitude(self, latitude):
        """
        transfer geographic latitude of observer (degrees)
        """
        self.lat = float(latitude)
        print 'Setting Geographic Latitude = %f (d)' % (self.lat)

    def set_SampleRate(self, sampleRate):
        """
        transfer sample rate (bandwidth)
        """
        self.sampleRate = float(sampleRate)
        print 'Setting Sample Rate = %f (Hz)' % (self.sampleRate)

    def set_Integrations(self, integrations):
        """
        transfer integration time (seconds)
        """
        self.integrations = datetime.timedelta(seconds=float(integrations))
        print 'Setting Integrations= %s ' % self.integrations

    def set_Azimuth(self, azimuth):
        """
        transfer the azimuth to the internal memory
        """
        print 'Setting Azimuth   = %s' % str(azimuth)
        self.az = float(azimuth)

    def set_Elevation(self, elevation):
        """
        transfer the elevation to the internal memory
        """
        print 'Setting Elevation = %s' % str(elevation)
        self.el = float(elevation)

    def get_note(self, msg):
        """
        transfer the note to the internal memory
        """
        msg = str(self[NOTE_KEY])
        return msg

    def update_grid(self, *args):
        """
        Update the plotter grid.
        This update method is dependent on the variables below.
        Determine the x and y axis grid parameters.
        The x axis depends on sample rate, baseband freq, and x divs.
        The y axis depends on y per div, y divs, and ref level.
        """
        # first check for a plot type change, if so, update

        for trace in TRACES:
            channel = '%s'%trace.upper()
            if self[TRACE_SHOW_KEY+trace]:
                if self.plottype == PLOTLOG:
                    self.plotter.set_waveform(
                        channel=channel,
                        samples=self._tracesLOG[trace],
                        color_spec=TRACES_COLOR_SPEC[trace])
                    if trace == 'Ave':
                        self.plotter.set_waveform(
                            channel=channel,
                            marker=3,
                            samples=self._tracesLOG[trace],
                            color_spec=TRACES_COLOR_SPEC[trace])
                        
                elif self.plottype == PLOTLINEAR:
                    self.plotter.set_waveform(
                        channel=channel,
                        samples=self._tracesLIN[trace],
                        color_spec=TRACES_COLOR_SPEC[trace])
                    if trace == 'Ave':
                        self.plotter.set_waveform(
                            channel=channel,
                            marker=3,
                            samples=self._tracesLIN[trace],
                            color_spec=TRACES_COLOR_SPEC[trace])
                else:
                    self.plotter.set_waveform(
                        channel=channel,
                        samples=self._tracesK[trace],
                        color_spec=TRACES_COLOR_SPEC[trace])
                    if trace == 'Ave':
                        self.plotter.set_waveform(
                            channel=channel,
                            marker=3,
                            samples=self._tracesK[trace],
                            color_spec=TRACES_COLOR_SPEC[trace])
            else:
                self.plotter.clear_waveform(channel=channel)

        #grid parameters
        sample_rate = float(self[SAMPLE_RATE_KEY])
        baseband_freq = float(self[BASEBAND_FREQ_KEY])
        y_per_div = self[Y_PER_DIV_KEY]
        y_divs = self[Y_DIVS_KEY]
        x_divs = self[X_DIVS_KEY]
        ref_level = self[REF_LEVEL_KEY]
        newy = (y_per_div != self.last_y_per_div) or (y_divs != self.last_y_divs)
        if newy or (ref_level != self.last_ref_level):
        #determine best fitting x_per_div
            if self.real:
                x_width = sample_rate/2.0
            else:
                x_width = sample_rate
            x_per_div = common.get_clean_num(x_width/x_divs)
        #update the x grid
            if self.real:
                self.plotter.set_x_grid(
                    baseband_freq,
                    baseband_freq + sample_rate/2.0,
                    x_per_div, True)
            else:
                self.plotter.set_x_grid(
                    baseband_freq - sample_rate/2.0,
                    baseband_freq + sample_rate/2.0,
                    x_per_div, True)
        #update x units
            self.plotter.set_x_label('Frequency', 'Hz')
        #update y grid
            self.plotter.set_y_grid(ref_level-y_per_div*y_divs, ref_level, y_per_div)
        #update y units
            if self.plottype == 0:
                self.plotter.set_y_label('Power', 'dB')
            elif self.plottype == 1:
                self.plotter.set_y_label('Power', 'Counts')
            else:
                self.plotter.set_y_label('Temperature', 'Kelvins')

        #update plotter
        self.plotter.update()
        self.last_y_per_div = y_per_div
        self.last_ref_level = ref_level
        self.last_y_divs = y_divs

# HISTORY
# 16OCT14 GIL fix display of linear and Tsys profiles
# 16AUG23 GIL reorganized for efficiency
# 15JUN04 GIL recording working, but having trouble with display
# 15JUN02 GIL return coordinates so that the data can be understood
# 15MAY29 GIL get averaging functioning and also periodic updates
# 15MAY16 GIL start creating averages
# 15MAY15 GIL try to reduce the cpu load
# 15MAY05 GIL have recording working now.  still too much CPU usage.
# 15MAY04 GIL found that the program was taking too much CPU
#             performance was fine once sleep of 10ms was added
# 15MAY01 GIL Initial version
