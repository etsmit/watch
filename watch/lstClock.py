#!/usr/bin/env python
# coding: UTF-8
# license: GPL
#
## @package _08c_clock
#
#  A very simple analog clock.
#
#  The program transforms worldcoordinates into screencoordinates 
#  and vice versa according to an algorithm found in: 
#  "Programming principles in computer graphics" by Leendert Ammeraal.
#
#  Based on the code of Anton Vredegoor (anton.vredegoor@gmail.com) 
#
#  @author Paulo Roma
#  @since 01/05/2014
#  @see https://code.activestate.com/recipes/578875-analog-clock
#  @see http://orion.lcg.ufrj.br/python/figuras/fluminense.png

import sys, types, os
from time import localtime
from datetime import timedelta,datetime
from math import sin, cos, pi
import ephem
import observing_notes
import calendar

def utc_to_local(utc_dt):
    # get integer timestamp to avoid precision lost
    timestamp = calendar.timegm(utc_dt.timetuple())
    local_dt = datetime.fromtimestamp(timestamp)
    assert utc_dt.resolution >= timedelta(microseconds=1)
    return local_dt.replace(microsecond=utc_dt.microsecond)

from threading import Thread
try:
    from tkinter import *       # python 3
except ImportError:
    try:
       from mtTkinter import *  # for thread safe
    except ImportError:
       from Tkinter import *    # python 2

hasPIL = True
# we need PIL for resizing the background image
# in Fedora do: yum install python-pillow-tk
# or yum install python3-pillow-tk
try:
    from PIL import Image, ImageTk
except ImportError:
    hasPIL = False

## Class for handling the mapping from window coordinates
#  to viewport coordinates.
#
class mapper:
    ## Constructor.
    #
    #  @param world window rectangle.
    #  @param viewport screen rectangle.
    #
    def __init__(self, world, viewport):
        self.world = world 
        self.viewport = viewport
        x_min, y_min, x_max, y_max = self.world
        X_min, Y_min, X_max, Y_max = self.viewport
        f_x = float(X_max-X_min) / float(x_max-x_min) 
        f_y = float(Y_max-Y_min) / float(y_max-y_min) 
        self.f = min(f_x,f_y)
        x_c = 0.5 * (x_min + x_max)
        y_c = 0.5 * (y_min + y_max)
        X_c = 0.5 * (X_min + X_max)
        Y_c = 0.5 * (Y_min + Y_max)
        self.c_1 = X_c - self.f * x_c
        self.c_2 = Y_c - self.f * y_c

    ## Maps a single point from world coordinates to viewport (screen) coordinates.
    #
    #  @param x, y given point.
    #  @return a new point in screen coordinates.
    #
    def __windowToViewport(self, x, y):
        X = self.f *  x + self.c_1
        Y = self.f * -y + self.c_2      # Y axis is upside down 
        return X , Y

    ## Maps two points from world coordinates to viewport (screen) coordinates.
    #
    #  @param x1, y1 first point.
    #  @param x2, y2 second point.
    #  @return two new points in screen coordinates.
    #
    def windowToViewport(self,x1,y1,x2,y2):
        return self.__windowToViewport(x1,y1),self.__windowToViewport(x2,y2)

## Class for creating a new thread.
#
class makeThread (Thread):
      """Creates a thread."""

      ## Constructor.
      #  @param func function to run on this thread.
      #
      def __init__ (self,func):
          Thread.__init__(self)
          self.__action = func
          self.debug = False

      ## Destructor.
      #
      def __del__ (self):
          if ( self.debug ): print ("Thread end")

      ## Starts this thread.
      #
      def run (self):
          if ( self.debug ): print ("Thread begin")
          self.__action()

## Class for drawing a simple analog clock.
#  The backgroung image may be changed by pressing key 'i'.
#  The image path is hardcoded. It should be available in directory 'images'.
#
class clock:
    ## Constructor.
    #
    #  @param deltahours time zone.
    #  @param sImage whether to use a background image.
    #  @param w canvas width.
    #  @param h canvas height.
    #  @param useThread whether to use a separate thread for running the clock.
    #
    def __init__(self,root,deltahours = 0,sImage = True,w = 200,h = 200,useThread = False):
        self.world       = [-1,-1,1,1]
        self.imgPath     = './images/fluminense.png'  # image path
        if hasPIL and os.path.exists (self.imgPath):
           self.showImage = sImage
        else:
           self.showImage = False
        
        self.setColors()
        self.circlesize  = 0.15
        self._ALL        = 'handles'
        self.root        = root
        width, height    = w, h
        self.pad         = width/16
        self.me = ephem.Observer()
        self.notes = observing_notes.observing_notes()
        self.now = datetime.utcnow()
        self.notes.read_notes()
        self.me.lon = str(self.notes.tellon)
        self.me.lat= str(self.notes.tellat)
        self.me.elevation=self.notes.telelev   # height in meters
        self.notecount = 1000 # init so that read notes happens early
        print 'Site: ', self.notes.Site
        print ' Lon: ', self.notes.tellon
        print ' Lat: ', self.notes.tellat

        strnow = self.now.isoformat()
        dates = strnow.split('T')
        datestr = dates[0] + ' ' + dates[1]

        if self.showImage:
           self.fluImg = Image.open(self.imgPath)

        self.root.bind("<Escape>", lambda _ : root.destroy())
        self.delta = timedelta(hours = deltahours)  
        self.canvas = Canvas(root, width = width, height = height, background = self.bgcolor)
        viewport = (self.pad,self.pad,width-self.pad,height-self.pad)
        self.T = mapper(self.world,viewport)
        self.root.title('Clock')
        self.canvas.bind("<Configure>",self.resize)
        self.root.bind("<KeyPress-i>", self.toggleImage)
        self.canvas.pack(fill=BOTH, expand=YES)

        self.b = Button(self.root, text="Refresh", justify=LEFT, command=self.callback())
        self.b.pack()
        
        if useThread:
           st=makeThread(self.poll)
           st.debug = True
           st.start()
        else:
           self.poll()

    def callback( self):
        self.notes.read_notes()
        print "Coordinates Updated"
        
    ## Called when the window changes, by means of a user input.
    #
    def resize(self,event):
        sc = self.canvas
        sc.delete(ALL)            # erase the whole canvas
        width  = sc.winfo_width()
        height = sc.winfo_height()

        imgSize = min(width, height)
        self.pad = imgSize/16
        viewport = (self.pad,self.pad,width-self.pad,height-self.pad)
        self.T = mapper(self.world,viewport)

        if self.showImage:
           flu = self.fluImg.resize((int(0.8*0.8*imgSize), int(0.8*imgSize)), Image.ANTIALIAS) 
           self.flu = ImageTk.PhotoImage(flu)
           sc.create_image(width/2,height/2,image=self.flu)
        else:
           self.canvas.create_rectangle([[0,0],[width,height]], fill = self.bgcolor)

        self.redraw()             # redraw the clock	
        
 
    ## Sets the clock colors.
    #
    def setColors(self):
        if self.showImage:
           self.bgcolor     = 'antique white'
           self.timecolor   = 'dark orange'
           self.circlecolor = 'dark green'
        else:
           self.bgcolor     = '#000000'
           self.timecolor   = '#ffffff'
           self.circlecolor = '#f04040'

    ## Toggles the displaying of a background image.
    #
    def toggleImage(self,event):
        if hasPIL and os.path.exists (self.imgPath):
           self.showImage = not self.showImage
           self.setColors()
           self.resize(event)

    ## Redraws the whole clock.
    # 
    def redraw(self):
        start = pi/2              # 12h is at pi/2
        step = pi/6
        for i in range(12):       # draw the minute ticks as circles
            angle =  start-i*step
            x, y = cos(angle),sin(angle)
            self.paintcircle(x,y)
        self.painthms()           # draw the handles
        if not self.showImage:
           self.paintcircle(0,0)  # draw a circle at the centre of the clock
   
    ## Draws the handles.
    # 
    def painthms(self):
        self.canvas.delete(self._ALL)  # delete the handles
        self.now = datetime.utcnow()
#        T = datetime.timetuple(self.now-self.delta)
        local = utc_to_local( self.now)
        T = datetime.timetuple(local)
        x,x,x,h,m,s,x,x,x = T
        self.root.title('%02i:%02i:%02i' %(h,m,s))
        angle = pi/2 - pi/6 * (h + m/60.0)
        x, y = cos(angle)*0.40,sin(angle)*0.40   
        scl = self.canvas.create_line
        # draw the hour handle
        scl(self.T.windowToViewport(0,0,x,y), fill = self.timecolor, tag=self._ALL, width = self.pad/3)
        angle = pi/2 - pi/30 * (m + s/60.0)
        x, y = cos(angle)*0.60,sin(angle)*0.60
        # draw the minute handle
        scl(self.T.windowToViewport(0,0,x,y), fill = self.timecolor, tag=self._ALL, width = self.pad/5)
        angle = pi/2 - pi/30 * s
        x, y = cos(angle)*0.95,sin(angle)*0.95   
        # draw the second handle
        scl(self.T.windowToViewport(0,0,x,y), fill = self.timecolor, tag=self._ALL, arrow = 'last')

    ## Draws a circle at a given point.
    # 
    #  @param x,y given point.
    # 
    def paintcircle(self,x,y):
        ss = self.circlesize / 2.0
        sco = self.canvas.create_oval
        sco(self.T.windowToViewport(-ss+x,-ss+y,ss+x,ss+y), fill = self.circlecolor)
  
    ## Animates the clock, by redrawing everything after a certain time interval. 
    #
    def poll(self):
        sc = self.canvas
        sc.delete(ALL)            # erase the whole canvas
        width  = sc.winfo_width()
        height = sc.winfo_height()

        strnow = self.now.isoformat()
        dates = strnow.split('T')
        datestr = dates[0] + ' ' + dates[1]

        self.me.date = datestr
        if self.notecount > 20:
            self.notes.read_notes()
            self.notecount = 0

        self.notecount = self.notecount + 1
        # now compute apparent RA, dec from az,el
        ra_a,dec_a = self.me.radec_of( str(self.notes.Azimuth),str(self.notes.Elevation))

        strnow = self.now.isoformat()
        dates = strnow.split('T')
        datestr = dates[0] + ' ' + dates[1]

        self.me.date = datestr
        radec = ephem.Equatorial( ra_a, dec_a, epoch=datestr)
        # compute ra, dec strings without decimal points
        ra = str(radec.ra).split('.')
        ra = ra[0]
        dec = str(radec.dec).split('.')
        dec = dec[0]
        gal = ephem.Galactic( radec)
        lon = str(gal.lon).split('.')
        lon = lon[0]
        lat = str(gal.lat).split('.')
        lat = lat[0]

            
        lst = str(self.me.sidereal_time())
        lst = lst.split('.')
        lsthms = lst[0]
        dh = height/16.
        timestr = dates[1]
        timehms = timestr.split('.')
        timehms = timehms[0]
        az = str(self.notes.Azimuth)
        el = str(self.notes.Elevation)
        self.canvas.create_text( width/2, 3*dh, text="UTC: "+timehms, fill=self.timecolor, font=("", 16))
        self.canvas.create_text( width/2, 4*dh, text="LST: "+lsthms, fill=self.timecolor, font=("", 16))
        self.canvas.create_text( width/2, 5*dh, text=" AZ: "+az+"  EL: "+el, fill=self.timecolor, font=("", 16))
        self.canvas.create_text( width/2,11*dh, text=" RA: "+ra, fill=self.timecolor, font=("", 16))
        self.canvas.create_text( width/2,12*dh, text="DEC: "+dec, fill=self.timecolor, font=("", 16))
        self.canvas.create_text( width/2,13*dh, text="LON: "+lon, fill=self.timecolor, font=("", 16))
        self.canvas.create_text( width/2,14*dh, text="LAT: "+lat, fill=self.timecolor, font=("", 16))
        self.redraw()
        self.root.after(3000,self.poll)

## Main program for testing.
#
#  @param argv time zone, image background flag,
#         clock width, clock height, create thread flag.
#
def main(argv=None):
    if argv is None:
       argv = sys.argv
    if len(argv) > 2:
       try:
           deltahours = int(argv[1])
           sImage = (argv[2] == 'True')
           w = int(argv[3])
           h = int(argv[4])
           t = (argv[5] == 'True')
       except ValueError:
           print ("A timezone is expected.")
           return 1
    else:
       deltahours = 3
       sImage = True  
       w = h = 300
       t = False

    root = Tk()
    root.geometry ('+0+0')
  
    # deltahours: how far are you from utc?
    # Sometimes the clock may be run from another timezone ...
    clock(root,deltahours,sImage,w,h,t)

    root.mainloop()

if __name__=='__main__':
    sys.exit(main())
