#!/usr/bin/env python2
"""
This script initializes the Watch.not file with the 
Latitude, longitude info, based on the computer IP address
This function is only used once, just before observations
"""
##################################################
# GNU Radio Python Flow Graph
# Title: Nsf Watch
##################################################
# HISTORY
# 16DEC21 GIL test the new readnotes code
import os
import time
import datetime
import observing_notes

notes = observing_notes.observing_notes()

notes.read_notes()

notes.NoteName = "Watch-new.not"

City, Region, Country, Lat, Lon = observing_notes.iplatlon()

notes.City = City
notes.Region = Region
notes.Country = Country
notes.tellon = Lon
notes.tellat = Lat
notes.write_notes()

print ""
print "----------------------------------------------------------------"
print ""
print "Please examine your new Note File: ", notes.NoteName
print "Update with your Telescope Azimuth and Elevation"
print "Check your telescope site Latitude and Longitude"
print "Good Luck with your Obsevations!"
print "   --- Glen Langston "
print "   glen.i.langston@gmail.com "
print "----------------------------------------------------------------"

