# imports
import cv2
import math
import numpy

tracker = cv2.TrackerMOSSE_create() # criando o mosse para o trackeamento

class ImageProcessor:
    def pre_process(frame):
        return frame
    def process(frame): # método pra processar as imagens

        # Menores valores possiveis pra Threshold HSV (peguei do GRIP)
        low_H = 45
        low_S = 126
        low_V = 119

        # Maiores valores possiveis para Threshold HSV (peguei do GRIP)
        high_H = 117
        high_S = 255
        high_V = 253

        # filtro
        frame_HSV = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV) # converte o frame pra HSV
        frame_threshold = cv2.inRange(frame_HSV, (low_H, low_S, low_V), (high_H, high_S, high_V)) # troca os frames que nao batem com os valores pra preto
        cv2.imshow('hsv', frame_HSV)
        cv2.imshow('padrao', frame)
 
        return frame_threshold # retorna o frame processado

class FindObject:
    # filtro
    ratioFilter = [0.0, 1.0] # remove figuras sem sentido
    solidityFilter = [0.0, 1.0] # remove buracos
    def _find_detection(self, frame, bbox = [0,0,640, 480]):
        x1, y1, w, h = bbox
        x2 = x1 + w
        y2 = y1 + h
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        roi = frame[y1:y2, x1:x2]
        object_list = []
        height, width = frame.shape
        _, contours, _ = cv2.findContours(roi, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            contourArea = cv2.contourArea(contour)
            x,y,w,h = cv2.boundingRect(contour) # pega um retangulo baseado no contorno
            ratio = w/h
            density = contourArea/(w*h)
            if self.evaluate(ratio, density, contourArea):
                rectangle = [x, y, w, h]
                object_list.append(TrackedObject(rectangle, width, height))
                drawn_frame = frame
                cv2.rectangle(roi, (x,y), (x+w, y+h), (255,255,255), 2)
        return object_list
    def evaluate(self, ratio, density, area):
        if ratio > 1.4 and ratio < 1.65:
            if density > 0.3 and density < 0.5:
                return True
        return False
    def find(self, frame):
        if self.i == 0:
            result = self._find_detection(ImageProcessor.process(frame))
            if result:
                x, y, w, h = result[0].rectangle
                rectangle = (x,y,w,h)
            else:
                return []
        else:
            result = self._find_detection(ImageProcessor.process(frame))
        self.i += 1
        return result
    def __init__(self):
        self.i = 0
    
class TrackedObject:

    # constantes para serem utiizadas em mais de uma função
    width = 11 #largura real do objeto
    
    height = 7 #altura real do objeto
    
    F = 600 #relacao entre largura em pixels e distancia
    
    def __init__(self, rectangle, frameWidth, frameHeight):

        #retangulo
        self.rectangle = rectangle #retangulo que circunda o contorno
        
        x,y,w,h = self.rectangle #pontos x e y do ponto inferior esquerdo do retangulo, sua altura e sua largura

        #frames
        self.frameWidth = frameWidth #largura da imagem
        
        self.frameHeight = frameHeight #altura da imagem
        print(str((w * 90)/11))

        #calculo de distancia
        self.distance = (self.width * self.F)/ w #distância, julgada pela diminuicao ou aumento do tamanho em pixels com relacao a uma distancia inicial
        #,542 sendo obtido por meio da relação entre largura real do objeto, largura do objeto em pixels a uma distância inicial de 30cm
        
        centerX = x + w/2 #topo esquerdo + metade da largura = centro do objeto, horizontalmente
        
        horizontalPX = frameWidth/2 - centerX #distância entre o centro da imagem e o centro do objeto, lado A do triângulo em pixels
        
        self.horizontalDistance = (horizontalPX * self.width)/w #estimativa da distancia para centralizar o objeto, usando regra de três com a largura em pixels do objeto e a sua largura real

        # calculo do angulo do robö
        angulo = math.atan2(self.horizontalDistance, self.distance) #angulo formado pelo triângulo entre distância da câmera para o objeto
        #e distância do ângulo reto da câmera e o centro do objeto, calculada via arcotangente

        self.angulograu = (180 * angulo)/math.pi #Converte radianos em graus

        # calculo da maneira mais curta até o alvo        
        self.straightDistance = ((self.distance**2) + (self.horizontalDistance**2)) ** (1/2) #Pitagoras para achar o caminho reto para o objeto


def __main__(self):    
    # variáveis
    ip = ImageProcessor()
    fo = FindObject()
    cap = cv2.VideoCapture(0)
    cap.set(3,640); # altera width
    cap.set(4,480); # altera height
    distancias = []
    angulos = []
    i = 0 # total de iterações de identificação de objetos
    DS = 0 # total de distâncias

    # loop infinito para análise da imagem
    while True:
        ret, frame = cap.read()
        objetos = fo.find(frame) # essa função retorna os objetos encontrados

        for objeto in objetos:
            tracked = objetos[0]
            distancias.append(tracked.distance)
            DS += tracked.distance
            angulos.append(tracked.angulograu)
            print('Distancia: {:2.3}'.format(tracked.distance))
           #print('Distancia horizontal: {0}'.format(tracked.horizontalDistance))
            i += 1

    erros = 0
    if i != 0:
        med = DS/i

    for distancia in distancias:
        erros += distancia-med

    cap.release()