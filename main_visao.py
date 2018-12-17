# imports
import cv2
import math
import numpy
from classes_visao import *

# variáveis
ip = ImageProcessor()
fo = FindObject()
cap = cv2.VideoCapture(0)
cap.set(3,640); # altera width
cap.set(4,480); # altera height
distancias = []
i = 0
DS = 0

# loop infinito para análise da imagem
while True:
    ret, frame = cap.read()
    objetos = fo.find(frame)
        
    for objeto in objetos:
        tracked = objetos[0]
        distancias.append(tracked.distance*100)
        DS += tracked.distance*100
        print('Distancia: {:2.3}'.format(tracked.distance))
       #print('Distancia horizontal: {0}'.format(tracked.horizontalDistance))
        i += 1
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

erros = 0
med = DS/i

for distancia in distancias:
    erros += distancia-med

print('Media dos erros {:2.3}    media das distancias {}'.format(erros/i,med))
    
cap.release()
cv2.destroyAllWindows()
