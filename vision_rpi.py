#!/usr/bin/env python3
# This code is based on FRCVision RPi image examples and hasn't been tested.
# Deploy with caution.
import json
import time
import sys
import numpy as np
import cv2

from cscore import CameraServer, VideoSource, CvSource, VideoMode, CvSink, UsbCamera
from networktables import NetworkTablesInstance

#   JSON format:
#   {
#       "team": <team number>,
#       "ntmode": <"client" or "server", "client" if unspecified>
#       "cameras": [
#           {
#               "name": <camera name>
#               "path": <path, e.g. "/dev/video0">
#               "pixel format": <"MJPEG", "YUYV", etc>   // optional
#               "width": <video mode width>              // optional
#               "height": <video mode height>            // optional
#               "fps": <video mode fps>                  // optional
#               "brightness": <percentage brightness>    // optional
#               "white balance": <"auto", "hold", value> // optional
#               "exposure": <"auto", "hold", value>      // optional
#               "properties": [                          // optional
#                   {
#                       "name": <property name>
#                       "value": <property value>
#                   }
#               ]
#           }
#       ]
#   }

configFile = "/boot/frc.json"

class CameraConfig: pass

team = None
server = False
cameraConfigs = []

"""Report parse error."""
def parseError(str):
    print("config error in '" + configFile + "': " + str, file=sys.stderr)

"""Read single camera configuration."""
def readCameraConfig(config):
    cam = CameraConfig()

    # name
    try:
        cam.name = config["name"]
    except KeyError:
        parseError("could not read camera name")
        return False

    # path
    try:
        cam.path = config["path"]
    except KeyError:
        parseError("camera '{}': could not read path".format(cam.name))
        return False

    cam.config = config

    cameraConfigs.append(cam)
    return True

"""Read configuration file."""
def readConfig():
    global team
    global server

    # parse file
    try:
        with open(configFile, "rt") as f:
            j = json.load(f)
    except OSError as err:
        print("could not open '{}': {}".format(configFile, err), file=sys.stderr)
        return False

    # top level must be an object
    if not isinstance(j, dict):
        parseError("must be JSON object")
        return False

    # team number
    try:
        team = j["team"]
    except KeyError:
        parseError("could not read team number")
        return False

    # ntmode (optional)
    if "ntmode" in j:
        str = j["ntmode"]
        if str.lower() == "client":
            server = False
        elif str.lower() == "server":
            server = True
        else:
            parseError("could not understand ntmode value '{}'".format(str))

    # cameras
    try:
        cameras = j["cameras"]
    except KeyError:
        parseError("could not read cameras")
        return False
    for camera in cameras:
        if not readCameraConfig(camera):
            return False

    return True

class TrackedObject:

    # calc constants
    width = 5 # object real width (cm)
    height = 14 # object real height (cm)
     
    F = 600 # camera focal point
    
    def __init__(self, rectangle, frameWidth, frameHeight, sd):
        #retangulo
        self.rectangle = rectangle # rectangle bounding the contour
        x,y,w,h = self.rectangle # rectangle coordinates

        #frames
        self.frameWidth = frameWidth # image width
        self.frameHeight = frameHeight # image height
        print(str((w * 90)/11)) # used for debugging... should be approx. the distance. this allows you to tune focal length

        # distance calcs
        self.distance = (self.width * self.F)/ w # distance, based on focal length calcs
        centerX = x + w/2 # in theory, it's top left coordinate + half it's width is X center
        horizontalPX = frameWidth/2 - centerX # distance between real and image centers
        self.horizontalDistance = (horizontalPX * self.width)/w # distance for alignment of the object

        # robot angle calcs
        angulo = math.atan2(self.horizontalDistance, self.distance) # angle formed by the camera's distance to the object and
        # and the camera's right angle (calc via arctan)

        self.angulograu = (180 * angulo)/math.pi # radians to degrees (makes calcs easier)
        
        # shortest distance to the tracked object       
        self.straightDistance = ((self.distance**2) + (self.horizontalDistance**2)) ** (1/2) # pythagorean theorem for
        # finding the straight distance to the object

        # passing values. this class structure is true spaghetti and this shouldn't happen, but it probably works.
        sd.putNumber('AngleRadians', self.angulo)
        sd.putNumber('AngleDegrees', self.angulograu)
        sd.putNumber('Distance', self.distance)
        
def evaluate(ratio, density, area): # function for simple filtering
        if ratio > 0.2 and ratio < 0.5:
            if density > 0.3 and density < 0.5:
                return True
        return False

# it should be a class, however that would be hard to mantain (we did it on other code and it didn't quite work)
def TrackRocket(frame, sd):
    # tries to get SD values, if it can't it'll reset to default code
    HL = sd.getNumber('HL', 0)
    HU = sd.getNumber('HU', 0)
    SL = sd.getNumber('SL', 0)
    SU = sd.getNumber('SU', 0)
    VL = sd.getNumber('VL', 0)
    VU = sd.getNumber('VU', 0)
    RocketLower = (HL,SL,VL)
    RocketUpper = (HU,SU,VU)
    print("Lower HSV:%s Upper HSV:%s" % (RocketLower, RocketUpper))
        
    # if no frame arrives, the vid is over or camera is unavailable
    if frame is None:
        sd.putNumber('PegandoFrames',False)
    else:
        sd.putNumber('PegandoFrames',True)

    height, width = frame.shape[:2]
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # creates a mask for thresholding and then removes inconsistencies
    mask = cv2.inRange(hsv, RocketLower, RocketUpper)
    mask = cv2.erode(mask, None, iterations = 2)
    mask= cv2.dilate(mask, None, iterations = 2)
    
    _, contours , _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    # if it doesn't find contours, there's no reason for passing here
    # tracking would be useful for saving resources, but there's no way to compile OpenCV 4.0 in FIRST's RPi image
    if len(contours) > 0:
        for ctn in contours:
            area_ctn = cv2.contourArea(ctn)
            x, y, w, h = cv2.boundingRect(ctn)
            ratio = w/h
            density = area_ctn/w*h
            # evaluating by ratio and density is useful for discarding useless contours. th
            if evaluate(ratio, density, area_ctn):
                rect = [x, y, w, h]
                rect_drawn = frame
                cv2.rectangle(rect_drawn, (x, y), (x + w, y + h), (255, 255, 255), 2)
                to = TrackedObject(rect, width, height) # this class is a huuuuge workaround... 
    return mask
    
    
if __name__ == "__main__":
    if len(sys.argv) >= 2:
        configFile = sys.argv[1]

    # read configuration
    if not readConfig():
        sys.exit(1)

    # start NetworkTables to send to smartDashboard
    ntinst = NetworkTablesInstance.getDefault()

    print("Setting up NetworkTables client for team {}".format(team))
    ntinst.startClientTeam(team)

    shuffle = ntinst.getTable('Shuffleboard')
    sd = shuffle.getSubTable('Vision')
    
    # set up camera server
    print("Connecting to camera")
    cs = CameraServer.getInstance()
    cs.enableLogging()
    camera = cs.startAutomaticCapture()
    camera.setResolution(160,120)
    
    print("connected")

    # CvSink objects allows you to apply OpenCV magic to CameraServer frames 
    cv_sink = cs.getVideo()
    
    # CvSource objects allows you to pass OpenCV frames to your CameraServer
    outputStream = cs.putVideo("Processed Frames", 160,120)

    # numpy buffer to store image data
    # if you don't do this, the CvSink glitches out and gives you something that's not a np array
    # I haven't really played with this, so feel free to play around and save processing power
    img = np.zeros(shape=(160,120,3), dtype=np.uint8)
    # loop forever
    while True:
        frame_time, img = cv_sink.grabFrame(img)
        if frame_time == 0:
            outputStream.notifyError(cv_sink.getError())
            continue
        img = TrackRocket(img, sd)
    
        outputStream.putFrame(img)

