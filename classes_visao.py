# imports
import cv2
import math
import numpy

tracker = cv2.TrackerMOSSE_create() # MOSSE for tracking

class ImageProcessor:
    def pre_process(frame): # returns the image before it gets filtered
        return frame 
    def process(frame): # applies HSV filters to images

        # lowest values for HSV array (values grabbed from GRIP)
        low_H = 53
        low_S = 177
        low_V = 62

        # highest values for HSV array (values grabbed from GRIP)
        high_H = 91
        high_S = 255
        high_V = 255

        # filtering
        frame_HSV = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV) # converts color scale to HSV
        frame_threshold = cv2.inRange(frame_HSV, (low_H, low_S, low_V), (high_H, high_S, high_V)) # applies filter
        cv2.imshow('hsv', frame_HSV) # shows the image for debugging

        return frame_threshold 

class FindObject:
    # fiter
    ratioFilter = [0.0, 1.0] # removes non-sense figures
    solidityFilter = [0.0, 1.0] # removes figures that have holes (are not solid)
    
    def _find_tracker(self, frame):
        if self.trackerON: # defined later, but is used to find tracker
            bbox = tracker.update(frame)
            x,y,w,h = bbox[1] # makes sure you can still get the image from the bounding box if it escapes
            w += 50
            h += 50 
            return (x,y,w,h)
        return False # we shouldn't find trackers if we don't have enabled trackers
    
    def _find_detection(self, frame, bbox = [0,0,640, 480]):
        x1, y1, w, h = bbox # gets the bounding box coordinates
        x2 = x1 + w
        y2 = y1 + h
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2) # makes sure you can do ROI operations
        roi = frame[y1:y2, x1:x2]
        object_list = []
        height, width = frame.shape
        _, contours, _ = cv2.findContours(roi, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE) # finds potential objects and their contours
        
        for contour in contours:
            contourArea = cv2.contourArea(contour)
            x,y,w,h = cv2.boundingRect(contour) # gets the coordinates from the objects bounding box
            ratio = w/h # used for filtering (we shouldn't process objects that don't meet our criteria)
            density = contourArea/(w*h) 
            if self.evaluate(ratio, density, contourArea): # if it meets our criteria, we'll process it for tracking
                rectangle = [x, y, w, h]
                object_list.append(TrackedObject(rectangle, width, height)) 
                drawn_frame = frame
                cv2.rectangle(roi, (x,y), (x+w, y+h), (255,255,255), 2)
                cv2.imshow('drawn', roi)
                
        return object_list # return objects ready to be tracked
    
    def evaluate(self, ratio, density, area): # function for simple filtering
        if ratio > 1.4 and ratio < 1.65:
            if density > 0.3 and density < 0.5:
                return True
        return False
    
    def find(self, frame):
        if self.i == 0: # if it's the first time we are going through this, we should detect something 
            result = self._find_detection(ImageProcessor.process(frame))
            if result: # if we find any object, we`ll track it
                x, y, w, h = result[0].rectangle
                rectangle = (x,y,w,h)
                tracker.init(frame, rectangle) 
                self.trackerON = True
            else:
                return [] # random workaround
        else:
            result = self._find_tracker(frame) # if we don't find any object, we should be looking for some
            result = self._find_detection(ImageProcessor.process(frame)) # if we don't find a tracker, we'll try detecting objects
        self.i += 1
        return result
    
    def __init__(self):
        self.i = 0
        self.trackerON = False
    
class TrackedObject:

    # calc constants
    width = 11 # object real width (cm)
    height = 7 # object real height (cm)
     
    F = 600 # camera focal point
    
    def __init__(self, rectangle, frameWidth, frameHeight):

        #retangulo
        self.rectangle = rectangle # rectangle bounding the contour
        
        x,y,w,h = self.rectangle # rectangle coordinates

        #frames
        self.frameWidth = frameWidth # image width
        
        self.frameHeight = frameHeight # image height
        print(str((w * 90)/11)) # used for debugging... should be approx. the distance. this allows you to tune focal length

        #calculo de distancia
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
