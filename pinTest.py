import spidev
import RPi.GPIO as GPIO
import time
import threading

GPIO.setmode(GPIO.BOARD)
spi = spidev.SpiDev()
spi.open(0,0)
spi.max_speed_hz = 1000000  #1MHz
spi.bits_per_word = 8

#setup LDAC and SYNC pins
TRIG = 11

GPIO.setup(TRIG, GPIO.IN) #Trigger

def my_callback(channel):
    print "hi! on channel %i" %channel
    time.sleep(3)

GPIO.add_event_detect(TRIG, GPIO.RISING, callback = my_callback)

                      
