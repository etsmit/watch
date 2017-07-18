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
# 16DEC21 GIL separate out read and write notes

import os
import datetime

###
### iplatlon() is not a part of the class so that it is not required.
### These values may be manually entered into the notes file
###
def iplatlon():
    """
    iplatlon() uses the ip address to get the latitude and longitude
    The latitude and longitude are only rough, but usually 
    better han 100 km accuracy.  This is good enough for small antennas.
    """
    import re
    import json
    from urllib2 import urlopen

    data = str(urlopen('http://checkip.dyndns.com/').read())
    IP = re.compile(r'(\d+.\d+.\d+.\d+)').search(data).group(1)
    url = 'http://ipinfo.io/' + IP + '/json'
    response = urlopen(url)
    data = json.load(response)

    org=data['org']
    City = data['city']
    country=data['country']
    Region=data['region']

    loc = data['loc']
    locs = loc.split(',')
    lat = float( locs[0])
    lon = float( locs[1])

    print '\nYour IP details: '
    print 'IP : {0} \nRegion : {1} \nCountry : {2}'.format(IP, Region, country)
    print 'City : {0} \nOrg : {1}'.format(City, org)
    print 'Latitude: ',lat,'Longitude: ',lon
    return City, Region, country, lat, lon

class observing_notes(object):
    """
    Class for storing/reading oberving notes
    """
    def __init__(self):
        noteA = "Configuration for Observations"
        noteB = "Gain setting summary"
        gains = [1., 1., 1.]
        noteutc = datetime.datetime.utcnow()
        telType = "Pyramid Horn"
        observer = "Glen Langston"
        site = "Moumau House"

        #now fill out the notes structure.
        self.NoteName = "Watch.not"
        self.noteA = str(noteA)      # observing note A
        self.noteB = str(noteB)      # observing note B
        self.Observer = str(observer)   # name of the observer
        self.Site = str("Moumau House") # name of the observing site
        self.City = "Green Bank"
        self.Region = "West Virginia"
        self.Country = "US"
        self.noteUTC = str(noteutc)  # time the notes were created/updated
        self.gains = gains           # one or more gain parameters
        self.gain1 = gains[0]        # one or more gain parameters
        self.gain2 = gains[1]        # one or more gain parameters
        self.gain3 = gains[2]        # one or more gain parameters
        self.Azimuth = 0.            # telescope azimuth (degrees)
        self.Elevation = 0.           # telescope elevation (degrees)
        self.tellon = 0.   # geographic longitude negative = West (degrees)
        self.tellat = 0.   # geopgraphic latitude (degrees)
        self.telelev = 0.  # geographic elevation above sea-level (meteres)
        self.telType = str(telType) # "Horn, Parabola  Yagi, Sphere"
        # define size of horn or antenna (for parabola usuall A = B)
        self.telSizeAm = float(1.)  # A size parameter in meters
        self.telSizeBm = float(1.)  # B size parameter in meters
        self.etaA = .8 # antenna efficiency (range 0 to 1)
        self.etaB = .99 # efficiency main beam (range 0 to 1)
        self.polA = str("X")        # polariation of A ydata: X, Y, R, L,
        self.polB = str("Y")        # polariation of B ydata: X, Y, R, L,
        self.polAngle = float(0.0)  # orientation of polariation of A
        self.frame = str("TOPO")    # reference frame (LSR, BARY, TOPO)
        self.FrequencyHz = float(1420.405E6)
        self.FrequencyStr = str(self.FrequencyHz*1.E-6)
        self.SampleRate = float(10.E6)
        self.Integrations = 60.     # Integration time seconds
        self.fft_rate = int(2000)   # FFTs per second. This can be increased
                                    # to over 20,000 per second
                                    # if your computer is fast enough
        self.version = str("0.0.1") # Notes file version number

    def read_notes(self):
        """
        function to read a note file and set class values
        """
    
        notefilename = self.NoteName
        if os.path.isfile(notefilename):
            noteFile = open(notefilename, 'r')
            notelines = noteFile.readlines()
            noteFile.close()
        else:
            print "Can not Read Note file: ",notefilename

        # reread the last note file
        for line in notelines:
            parts = line.split("# ") # Split out Comments
            parts = parts[0].split(": ")
        #            print parts
            parts[0] = parts[0].upper()
            if parts[0] == "NOTEA":
                self.noteA = parts[1].strip()
            if parts[0] == "NOTEB":
                self.noteB = parts[1].strip()
            if parts[0] == "NOTEUTC":
                self.noteUTC = parts[1].strip()
            if parts[0] == "GAIN1":
                self.gain1 = float(parts[1].strip())
            if parts[0] == "GAIN2":
                self.gain2 = float(parts[1].strip())
            if parts[0] == "GAIN3":
                self.gain3 = float(parts[1].strip())
            if parts[0] == "OBSERVER": # ascii
                self.Observer = parts[1].strip()
            if parts[0] == "SITEe":   # ascii
                self.Site = parts[1].strip()
            if parts[0] == "AZ":
                self.Azimuth = float(parts[1].strip())
            if parts[0] == "EL":
                self.Elevation = float(parts[1].strip())
            if parts[0] == "TELLON":  # Geographics Longitude
                self.tellon = float(parts[1].strip())
            if parts[0] == "TELLAT":  # Geographic Latitude
                self.tellat = float(parts[1].strip())
            if parts[0] == "FREQ":
                self.FrequencyHz = float(parts[1].strip())
                self.FrequencyStr = str(self.FrequencyHz*1.E-6)
            if parts[0] == "RATE":
                self.SampleRate = float(parts[1].strip())
            if parts[0] == "FFTRATE":
                self.fft_rate = int(parts[1].strip())
            if parts[0] == "INT":
                self.Integrations = float(parts[1])
            if parts[0] == "CITY":
                self.City = str(parts[1].strip())
            if parts[0] == "REGION":
                self.Region = str(parts[1].strip())
            if parts[0] == "COUNTRY":
                self.Country = str(parts[1].strip())
            if parts[0] == "TELTYPE":
                self.telType = str(parts[1].strip())
            if parts[0] == "TELSIZEAM":
                self.telSizeAm = float(parts[1])
            if parts[0] == "TELSIZEBM":
                self.telSizeBm = float(parts[1])
            if parts[0] == "VERSION":
                self.version = str(parts[1].strip())
            if parts[0] == "POLA":
                self.polA = str(parts[1].strip())  # polariation of A ydata: X, Y, R, L,
            if parts[0] == "POLB":
                self.polB = str(parts[1].strip())  # polariation of B ydata: X, Y, R, L,
            if parts[0] == "POLANGLE":
                self.polAngle = float(parts[1])    # orientation of polariation of A
            if parts[0] == "FRAME":
                self.frame = str(parts[1].strip()) # reference frame (LSR, BARY, TOPO)
            if parts[0] == "ETAA":
                self.etaA = float(parts[1])        # Antenna efficiency, range 0 to 1
            if parts[0] == "ETAB":
                self.etaB = float(parts[1])        # Main Beam efficiency, range 0 to 1
# end of readnotes()

    def write_notes(self):
        """
        function to write out all note values
        """
        outFile = open(self.NoteName, 'w')
        outFile.write('File: ' + self.NoteName + '\n')
        outFile.write('Date: ' + str(self.noteUTC) + '\n')
        outFile.write('NoteA: ' + self.noteA + '\n')
        outFile.write('NoteB: ' + self.noteB + '\n')
        outFile.write('Observer: ' + self.Observer + '\n')
        outFile.write('Site: ' + self.Site + '\n')
        outFile.write('City: ' + self.City + '\n')
        outFile.write('Region: ' + self.Region + '\n')
        outFile.write('Country: ' + self.Country + '\n')
        outFile.write('Gain1: ' + str(self.gain1) + '\n')
        outFile.write('Gain2: ' + str(self.gain2) + '\n')
        outFile.write('Gain3: ' + str(self.gain3) + '\n')
        outFile.write('Freq: ' + str(self.FrequencyHz) + '\n')
        outFile.write('Rate: ' + str(self.SampleRate) + '\n')
        outFile.write('Az:   ' + str(self.Azimuth) + '\n')
        outFile.write('El:   ' + str(self.Elevation) + '\n')
        outFile.write('Int:  ' + str(self.Integrations) + '\n')
        outFile.write('TelLon: ' + str(self.tellon) + '\n')
        outFile.write('TelLat: ' +  str(self.tellat) + '\n')
        outFile.write('FFTrate: ' + str(self.fft_rate) + '\n')
        outFile.write('TelType: ' + str(self.telType) + '\n')
        outFile.write('TelSizeAm: ' + str(self.telSizeAm) + '\n')
        outFile.write('TelSizeBm: ' + str(self.telSizeAm) + '\n')
        outFile.write('Version: ' + str(self.version) + '\n')
        outFile.write('PolA: ' + str(self.polA) + '\n')
        outFile.write('PolB: ' + str(self.polB) + '\n')
        outFile.write('PolAngle: ' + str(self.polAngle) + '\n')
        outFile.write('Frame: ' + str(self.frame) + '\n')
        outFile.write('EtaA: ' + str(self.etaA) + '\n')
        outFile.write('EtaB: ' + str(self.etaB) + '\n')
        outFile.close()
# end of write_notes()

