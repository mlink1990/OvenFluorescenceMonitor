import os, sys
import datetime
import time
from time import sleep
import traceback

#import matplotlib.pyplot as plt
import scipy.misc as sm
import numpy as np
# import code
import csv
import influxdb

from picamera import PiCamera
import spidev
import RPi.GPIO

from getExperimentPaths import humphryNASFolder

dataFolder = os.path.join(humphryNASFolder,"Lab Monitoring","Logs","OvenFluorescence")

influxdbHost = "192.168.16.75"
influxdbPort = 8086
influxdbUser = "humphry"
influxdbPassword = "h2VndPd6jZXdZVQN"
influxdbName = "OvenFluorescence" # db name
influxdbMeasurement = "Counts"

class OvenFluorescenceAction():
    
    def __init__(self):
        self.ROI = (328, 416, 114, 301) # this is a tight area around the signal to determine a measure for the signal itself
        self.ROICoarse = (200, 500, 50, 350) # this is a coarse area around the signal to determine the background
        self.species = "Na"
        self.pictureNumber = 60 # every pictureNumber'th picture is saved. 
        self.logname = None
        
        if os.name == 'posix':
            print "RPi detected. Loading camera functionality.."

            RPi.GPIO.setmode(RPi.GPIO.BOARD)
            self.spi = spidev.SpiDev()
            self.spi.open(0,0)
            self.spi.max_speed_hz = 1000000  #1MHz
            self.spi.bits_per_word = 8
            
            self.TRIG = 11
            RPi.GPIO.setup(self.TRIG, RPi.GPIO.IN)
            self.camera = PiCamera()
            self.camera.framerate = 1
            #self.camera.zoom = (0.25, 0.5, 0.5, 0.5)
            self.camera.iso=800
#            self.camera.led = False
            sleep(2)
            self.camera.shutter_speed = 2000000000#self.camera.exposure_speed
            #self.camera.exposure_mode = 'off' # ""
            #g = self.camera.awb_gains
            self.camera.awb_mode = 'off'
            self.camera.awb_gains = 1
            #self.camera.awb_gains = 1
        else:
            print "No camera functionality.." 
        self.currentLocalTime = time.localtime()
        # self.currentMonth = self.currentLocalTime.tm_mon
        self.currentMonth = -1 # is set at first checkDateForFileName()

        self.lightPicture = np.load("lightPicture.npy")
    
    def setPictureNumber(self, pn):
        self.pictureNumber = int(pn)
        print "pictureNumber is set to %i" %self.pictureNumber
    
    def takePicture(self, path):
        try:
            self.camera.capture(path)
        except IOError:
            print( "IOError while taking picture. Check access to group folder.")
    
    def takePictureWithTrigger(self, path):
        signal = RPi.GPIO.wait_for_edge(self.TRIG, RPi.GPIO.RISING)
        self.camera.capture(path)
        
    def setSpecies(self, speciesSet):
        self.species = speciesSet
        print "Species is set to " + self.species
    
    def setROI(self, xmin, xmax, ymin, ymax):
        self.ROI = (xmin, xmax, ymin, ymax)
        return self.ROI
        
    def loadPicture(self, path):
        pic = sm.imread(path, flatten = True)
        return pic
        
    def savePicture(self, path, pic):
        sm.imsave(path, pic)
        
    def logSequence(self, t):
        i = 0
        fluorescences = []
        while i < t:
            now = time.time()
            fluorescences += [self.getFluorescence(True),]
            after = time.time()
            sleep(0.5)
            i += after-now
            print i
        return fluorescences            
        
    def integratePicture(self, pic):
        # result = np.sum(pic)
        res = np.mean( pic-self.lightPicture, axis = 2 )
        background = np.copy(res)
        background[self.ROICoarse[2]:self.ROICoarse[3],self.ROICoarse[0]:self.ROICoarse[1]] = np.nan
        background = np.nanmean(background)
        res -= background
        # print "background", background
        signal = np.mean( res[self.ROI[2]:self.ROI[3],self.ROI[0]:self.ROI[1]] )
        return signal
        
    def listen(self):
#        f = open( datetime.datetime.now().strftime("%Y%m%d_%H%M%S")+ "_" + self.species + "_OvenFluorescenceLog.csv", 'a')
        # self.logname = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")+ "_" + self.species + "_OvenFluorescenceLog.csv"        
        self.checkDateForFileName() # creates self.logname     
        print "Saving log as " + self.logname
#        f.write("epoch time , fluorescence \n")
        print "Starting to listen for trigger.. "
        i = 0
        try:                
            while True:
                # signal = RPi.GPIO.wait_for_edge(self.TRIG, RPi.GPIO.RISING)
                self.checkDateForFileName()
                if not os.path.exists(self.logname):
                    with open(self.logname, 'a+') as csvfile:
                        spamwriter = csv.writer(csvfile, delimiter=',', quotechar='#', quoting=csv.QUOTE_MINIMAL)
                        spamwriter.writerow(["time [epoch seconds]","fluorescence"])
                # #signal = 1                
                # if signal == None:
                #     print "No signal"
                # else:
                if i % self.pictureNumber == 0:
                    print "Taking picture!"
                    fluorescence = self.getFluorescence(True)
                else:
                    fluorescence = self.getFluorescence(False)
                print str(time.time()) + " , " + str(fluorescence)
#                    f.write(str(time.time()) + " , " + str(fluorescence) + '\n')
                with open(self.logname, 'a+') as csvfile:
                    spamwriter = csv.writer(csvfile, delimiter=',', quotechar='#', quoting=csv.QUOTE_MINIMAL)
                    spamwriter.writerow([time.time(), fluorescence])
#                    f.flush()
                self.logFluorescenceToDB(fluorescence)
                i+=1
                sleep(2.5)
                # self.takePicture("_dump.png") # workaround "every second picture is black"
                sleep(2.5)
        finally:
#            f.close()
            print "Returning ... "
                
    def getFluorescence(self, savePicture):
        subfolder = datetime.datetime.now().strftime("%Y%m")
        path1 = os.path.join(dataFolder, "Pictures", subfolder)
        if not os.path.exists(path1):
            os.mkdir(path1)
        path = os.path.join(path1, self.species) + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".png"
        
        while True:
            self.takePictureWithTrigger(path)
            pic = sm.imread(path)
            print "New picture with mean", np.mean(pic)
            if np.mean(pic) <= 80:
                print "Bad picture.. (low mean, probably Na beam off.. timing issue??) repeat!!"
            else:
                print "Good picture"
                break
        
        #y, x = np.shape(pic)
        # picROI = pic[np.arange(self.ROI[2], self.ROI[3]),:][:,np.arange(self.ROI[0], self.ROI[1])]
        
        #y2, x2 = np.shape(pic)
        if savePicture == True:        
            # self.savePicture(path.replace(".png","")+"ROI.png", picROI) # save ROI picture
            # picture is already at given path, don t delete it
            print "Saved as " + path
            # g = self.camera.awb_gains
            # with open(path.replace(".png","")+"params.txt", "w") as f:
            #     f.write("awbGain0 awbGain1 digitalGain analogGain\n")
            #     f.write("{} {} {} {}\n".format(float(g[0]),float(g[1]),float(self.camera.digital_gain),float(self.camera.analog_gain)))
        else:
            print "removed", path
            os.remove(path)
        fluorescence = self.integratePicture(pic)
        return fluorescence
    
    def logFluorescenceToDB(self, fluorescence):
        try:
            client = influxdb.InfluxDBClient(influxdbHost, influxdbPort, influxdbUser, influxdbPassword, influxdbName, ssl=True)
            client.write_points([{
                'measurement':influxdbMeasurement,
                'fields':{"Na SZ Fluorescence":fluorescence}
                }])
        except influxdb.exceptions.InfluxDBServerError:
            print "ERROR: Server Error"
            traceback.print_exc()
        except influxdb.exceptions.InfluxDBClientError:
            print "ERROR: Client Error"
            traceback.print_exc()
        except Exception:
            # catch all other DB related exceptions, e.g. ConnectionError .. :(
            traceback.print_exc()
        
        
    def checkDateForFileName(self):
        """gets current date and time and checks if we should change file name
        if we should it creates the new file and the name"""
        #self.currentLocalTime was already changed in log Temperatures
        comparison = time.localtime().tm_mon
        if comparison != self.currentMonth:
            #the month has changed we should start a new log file!
            print "New Month. Setting up new log!"
            filename = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")+ "_" + self.species + "_OvenFluorescenceLog.csv"
            self.logname = os.path.join(dataFolder, "Data", filename)
            if not os.path.exists(self.logname):#add column headers to file if it is new
               with open(self.logname, 'a+') as csvfile:
                   writer = csv.writer(csvfile, delimiter=',', quotechar='#', quoting=csv.QUOTE_MINIMAL)
                   writer.writerow(["time [epoch seconds]","fluorescence"])
            self.currentMonth = time.localtime().tm_mon
        #otherwise continue with no changes
        
            
        
if __name__ == "__main__":
    
    print """
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~    
|        ---------------------------------               |
|        ~~  OVEN FLUORESCENCE MONITOR  ~~               |
|        ---------------------------------               |
|        ~~     EXPERIMENT HUMPHRY      ~~               |
|        ---------------------------------               |
|        !!! START IN INTERACTIVE MODE !!!               |
|        ---------------------------------               |
|                                                        |
| if on RPi: all functionality available                 |
| if on something else: no camera functionality          |
|                                                        |
| Type of.listen() to start listening for trigger signal.|
| of.setSpecies(species) -- default is Na!               |
| of.setPictureNumber(pictureNumber) -- default is 10    |
! of.setROI((xmin, xmax, ymin, ymax)) -- default is      |   
|            a working ROI for Cam 66.                   |
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    """    
    
    print "Initializing..."   
    of = OvenFluorescenceAction()
    of.listen()
    print "Entering interactive mode .. \n "
  #  code.interact()


    
    
    
