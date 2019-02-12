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

def alternative_align(frame, sd):
    h, w, d = frame.shape
    angle = sd.getNumber('Angle', 0.0)
    difference_w = int(angle * ((w / 2) + 5) / 90)
    difference_h = int(angle * ((h / 2) + 5) / 90)
    cv2.rectangle(frame, (int((w / 2) - 10), int((h / 2) - 10)), (int(((w / 2) + 10)), int((h / 2) + 10)), (0, 255, 0), -1)
    cv2.rectangle(frame, (0, (int((h/2)) - 5)), (w, (int((h / 2) + 5))), (0, 255, 0), -1)
    if angle > -5 and angle < 5:
        cv2.rectangle(frame, (int(((w / 2) - 5) - difference_w), 0), (int(((w / 2) + 5) - difference_w), h), (0, 255, 0), -1)
    else:
        cv2.rectangle(frame, (int(((w / 2) - 5) - difference_w), 0), (int(((w / 2) + 5) - difference_w), h), (0, 255, 255), -1)
    return frame
    
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
        img = alternative_align(img, sd)
    
        outputStream.putFrame(img)
