from PyQt5.QtWidgets import QDialog, QLabel
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.uic import loadUi
import threading
import cv2
import numpy as np
import math


class GUI_main_window(QDialog):
    def __init__(self, app):
        super(GUI_main_window, self).__init__()
        loadUi("main_window.ui", self)
        self.show()

        """
        Juíz
        """
        self.btPararTransmissao.clicked.connect(self.terminarTransmissao)
        self.btJogar.clicked.connect(self.iniciarTransmissao)

        self.QT_btFreeBall.clicked.connect(lambda: self.mudanca_foul(3))
        self.QT_btPenaltyKick.clicked.connect(lambda: self.mudanca_foul(1))
        self.QT_btGoalKick.clicked.connect(lambda: self.mudanca_foul(2))
        self.QT_btKickOff.clicked.connect(lambda: self.mudanca_foul(4))
        
        self.QT_btHalt.clicked.connect(lambda: self.mudanca_foul(7))
        self.QT_btStop.clicked.connect(lambda: self.mudanca_foul(5))
        self.QT_btStart.clicked.connect(lambda: self.mudanca_foul(6))
        
        self.QT_btQ1.clicked.connect(lambda: self.mudanca_quadrante(1))
        self.QT_btQ2.clicked.connect(lambda: self.mudanca_quadrante(2))
        self.QT_btQ3.clicked.connect(lambda: self.mudanca_quadrante(3))
        self.QT_btQ4.clicked.connect(lambda: self.mudanca_quadrante(4))

        self.QT_btYellow.clicked.connect(lambda: self.mudanca_teamcolor(1))
        self.QT_btBlue.clicked.connect(lambda: self.mudanca_teamcolor(0))

        self.qt_Label.setText("Esperando iniciar")
        self.qt_Label.setStyleSheet("background-color:yellow")
        self.qt_FaltaAtual.setText("Juiz acabou de ser iniciado")
        self.qt_UltimaFalta.setText("Juiz acabou de ser iniciado")

        self.Color = 2
        self.quadrante = 0
        self.foul = 4

        self.QuadranteAtual = 0
        self.FaltaAtual = 4
        self.QT_btKickOff.setStyleSheet("background-color:green")
        self.CorAtual = 2

        self.QuadranteAnterior = 0
        self.FaltaAnterior = 4
        self.CorAnterior = 2

        """
        Visão do campo
        """

        #self.referee = Referee()
        
        field = vision.get_field_data()

        self.our_bots = field["our_bots"]
        self.their_bots = field["their_bots"]
        self.ball= field["ball"]

        self.draw_all()


    def rotate(self,points, angle):

        """
        Rotação dos robôs
        """

        ANGLE = np.deg2rad(angle)
        SIN = math.sin(ANGLE)
        COS = math.cos(ANGLE)
        
        
        c_x, c_y = np.mean(points, axis=0)

        return np.array(
            [
                [
                    c_x + COS * (px - c_x) - SIN * (py - c_y),
                    c_y + SIN * (px - c_x) + COS * (py - c_y),
                ]
                for px, py in points
            ]
        ).astype(int)
        
    def cm_to_pxl(self,x,y):
        #Cm 170x130
        #pxl 850x650
        #Origem dos cm, canto inferior esquerdo, cresce para cima
        #Origem dos pxl, canto superior esquerdo, cresce para baixo
        novo_x = (x*850/170)
        novo_y = (650-y*650/130 + 100)
        """
        pos_bolax = (imagem.centroids[0][0][0][0])*170/640
        pos_bolay = ((480 - imagem.centroids[0][0][0][1])*130/480)
        """

        return novo_x, novo_y

    def edges_robot(self,x,y):
        x1 = x-850/170
        x2 = x+850/170
        y1 = y-850/170
        y2 = y+850/170
        return (x1,y1),(x1,y2),(x2,y2),(x2,y1)


    def draw_robot(self,p1,p2,p3,p4,angle,team):
        if team == "blue":
            p1_draw,p2_draw,p3_draw,p4_draw = self.rotate((p1,p2,p3,p4),angle)
            pp = np.array([p1_draw,p2_draw,p3_draw,p4_draw])
            cv2.drawContours(self.pixmap, [pp], -1, (0, 0, 255), -1)
        else:
            p1_draw,p2_draw,p3_draw,p4_draw = self.rotate((p1,p2,p3,p4),angle)
            pp = np.array([p1_draw,p2_draw,p3_draw,p4_draw])
            cv2.drawContours(self.pixmap, [pp], -1, (255, 255, 0), -1)
                


    def draw_all(self):
        self.looping_img = threading.Timer(1, self.draw_all)

        self.looping_img.start()
        self.pixmap = cv2.imread('Field.jpg')
        for i in range(0,3):
            try:
                novo_x, novo_y= self.cm_to_pxl(self.our_bots[i].x,self.our_bots[i].y)
                p1,p2,p3,p4 = self.edges_robot(novo_x, novo_y)
                team = "blue"
                self.draw_robot(p1,p2,p3,p4,self.our_bots[i].a, team)
                print(i)
                print(self.their_bots[i].x)
            except IndexError:
                pass
                
        for i in range(0,3):
            try:
                novo_x, novo_y = self.cm_to_pxl(self.their_bots[i], self.their_bots[i].y)
                p1,p2,p3,p4 = self.edges_robot(novo_x, novo_y)
                team = "Yellow"
                self.draw_robot(p1,p2,p3,p4,self.their_bots[i].a, team)
            except IndexError:
                pass


        """
        Corrigir ângulo da imagem

        Não sei o pq precisa ser assim, mas sempre que tentei gerar a imagem de outra forma deu erro, duvida? Fica alterando os valores de pixmap.shape/pixmap.stride
        """
        _q_image = QImage(self.pixmap, self.pixmap.shape[1], self.pixmap.shape[0], self.pixmap.strides[0], QImage.Format_RGB888)
        _q_pixmap = QPixmap.fromImage(_q_image)
        self.QT_jogar.setPixmap(_q_pixmap)
       

        

    def mudanca_quadrante(self,enum):
        """
        Funcionalidade das trocas de quadrantes no referee
        """


        if enum == 1:
            if self.quadrante == 1:
                self.quadrante = 0
                self.QT_btQ1.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
            else:
                self.quadrante = enum
                self.QT_btQ1.setStyleSheet("background-color:green")
                self.QT_btQ2.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.QT_btQ3.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.QT_btQ4.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
        elif enum == 2:
            if self.quadrante == 2:
                self.quadrante = 0
                self.QT_btQ2.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
            else:
                self.quadrante = enum
                self.QT_btQ2.setStyleSheet("background-color:green")
                self.QT_btQ1.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.QT_btQ3.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.QT_btQ4.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
        elif enum == 3:
            if self.quadrante == 3:
                self.quadrante = 0
                self.QT_btQ3.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
            else:
                self.quadrante = enum
                self.QT_btQ3.setStyleSheet("background-color:green")
                self.QT_btQ2.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.QT_btQ1.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.QT_btQ4.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
        elif enum == 4:
            if self.quadrante == 4:
                self.quadrante = 0
                self.QT_btQ4.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
            else:
                self.quadrante = enum
                self.QT_btQ4.setStyleSheet("background-color:green")
                self.QT_btQ2.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.QT_btQ3.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.QT_btQ1.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")


            

    def mudanca_foul(self,enum):
        """
        Funcionalidade da troca de fouls no juíz
        """
        if enum == 1:
            if self.FaltaAtual == 1:
                self.QT_btPenaltyKick.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.foul = 0
                self.RegistraFalta()
            else:
                self.foul = enum
                self.QT_btPenaltyKick.setStyleSheet("background-color:green")
                self.QT_btKickOff.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.QT_btFreeBall.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.QT_btGoalKick.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.RegistraFalta()
            self.cria_dic()
            self.quadrante = 0
        elif enum == 2:
            if self.FaltaAtual == 2:
                self.QT_btGoalKick.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.foul = 0
                self.RegistraFalta()
            else:
                self.foul = enum
                self.QT_btGoalKick.setStyleSheet("background-color:green")
                self.QT_btKickOff.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.QT_btFreeBall.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.QT_btPenaltyKick.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.color = 2
                self.RegistraFalta()
            self.cria_dic()
            self.quadrante = 0

        elif enum == 4:
            if self.FaltaAtual == 4:
                self.QT_btKickOff.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.foul = 0
                self.RegistraFalta()
            else:
                self.foul = enum
                self.QT_btKickOff.setStyleSheet("background-color:green")
                self.QT_btGoalKick.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.QT_btFreeBall.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.QT_btPenaltyKick.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.RegistraFalta()
            self.cria_dic()
            self.quadrante = 0
        elif enum == 3:
            self.color = 2
            if self.FaltaAtual == 3:
                self.QT_btFreeBall.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.foul = 0
                self.quadrante = 0
                self.RegistraFalta()
            else:
                self.foul = enum
                self.QT_btFreeBall.setStyleSheet("background-color:green")
                self.QT_btGoalKick.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.QT_btKickOff.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.QT_btPenaltyKick.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.RegistraFalta()
            self.cria_dic()
            
        elif enum == 5:
                self.QT_btStop.setStyleSheet("background-color:green")
                
                self.qt_Label.setText("Stop")
                self.qt_Label.setStyleSheet("background-color:red")

                self.QT_btHalt.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.QT_btStart.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.cria_dic()
        elif enum == 6:
                self.QT_btStart.setStyleSheet("background-color:green")
                
                self.qt_Label.setText("Start")
                self.qt_Label.setStyleSheet("background-color:green")

                self.QT_btHalt.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.QT_btStop.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.cria_dic()
        elif enum == 7:
                self.QT_btHalt.setStyleSheet("background-color:green")
                
                self.qt_Label.setText("Halt")
                self.qt_Label.setStyleSheet("background-color:red")

                self.QT_btStop.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.QT_btStart.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.cria_dic()

    def mudanca_teamcolor(self, enum):
        if enum == 0:
            if self.Color == 0:
                self.Colorolor = 2
                self.QT_btBlue.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
            else:
                self.Color = enum
                self.QT_btBlue.setStyleSheet("background-color:green")
                self.QT_btYellow.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}") 
        elif enum == 1:
            if self.Color == 1:
                self.Color = 2
                self.QT_btYellow.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
            else:
                self.Color = enum
                self.QT_btYellow.setStyleSheet("background-color:green")
                self.QT_btBlue.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")

    def RegistraFalta(self):
        self.FaltaAnterior = self.FaltaAtual
        self.FaltaAtual = self.foul
        self.QuadranteAnterior = self.QuadranteAtual
        self.QuadranteAtual = self.quadrante
        self.CorAnterior = self.CorAtual
        self.CorAtual = self.Color


        #Parte dos valores atuais
        if self.FaltaAtual == 0:
            self.FaltaTextoAtual = "Free Kick"
        elif self.FaltaAtual == 1:
            self.FaltaTextoAtual = "Penalty Kick"
        elif self.FaltaAtual == 2:
            self.FaltaTextoAtual = "Goal Kick"
        elif self.FaltaAtual == 3:
            self.FaltaTextoAtual = "Free Ball"
        elif self.FaltaAtual == 4:
            self.FaltaTextoAtual = "KickOff"
            


        if self.QuadranteAtual == 0:
            self.QuadranteTextoAtual = ", Sem Quadrante"
        elif self.QuadranteAtual == 1:
            self.QuadranteTextoAtual = ", Quadrante 1"
        elif self.QuadranteAtual == 2:
            self.QuadranteTextoAtual = ", Quadrante 2"
        elif self.QuadranteAtual == 3:
            self.QuadranteTextoAtual = ", Quadrante 3"
        elif self.QuadranteAtual == 4:
            self.QuadranteTextoAtual = ", Quadrante 4"

        if self.CorAtual == 0:
            self.CorTextoAtual = ", Blue"
        elif self.CorAtual == 1:
            self.CorTextoAtual = ", Yellow"
        elif self.CorAtual == 2:
            self.CorTextoAtual = ", No color"
        
        #Parte dos valores anteriores
        if self.FaltaAnterior == 0:
            self.FaltaTextoAnterior = "Free Kick"
        elif self.FaltaAnterior == 1:
            self.FaltaTextoAnterior = "Penalty Kick"
        elif self.FaltaAnterior == 2:
            self.FaltaTextoAnterior = "Goal Kick"
        elif self.FaltaAnterior == 3:
            self.FaltaTextoAnterior = "Free Ball"
        elif self.FaltaAnterior == 4:
            self.FaltaTextoAnterior = "KickOff"

        if self.QuadranteAnterior == 0:
            self.QuadranteTextoAnterior = ", Sem Quadrante"
        elif self.QuadranteAnterior == 1:
            self.QuadranteTextoAnterior = ", Quadrante 1"
        elif self.QuadranteAnterior == 2:
            self.QuadranteTextoAnterior = ", Quadrante 2"
        elif self.QuadranteAnterior == 3:
            self.QuadranteTextoAnterior = ", Quadrante 3"
        elif self.QuadranteAnterior == 4:
            self.QuadranteTextoAnterior = ", Quadrante 4"

        if self.CorAnterior == 0:
            self.CorTextoAnterior = ", Blue"
        elif self.CorAnterior == 1:
            self.CorTextoAnterior = ", Yellow"
        elif self.CorAnterior == 2:
            self.CorTextoAnterior = ", No color"

        textoAtual = "Caso atual:" +str(self.FaltaTextoAtual) +str(self.CorTextoAtual) +str(self.QuadranteTextoAtual)
        textoAntigo = "Caso Anterior:" +str(self.FaltaTextoAnterior) +str(self.CorTextoAnterior) +str(self.QuadranteTextoAnterior)


        self.qt_FaltaAtual.setText(textoAtual)
        self.qt_UltimaFalta.setText(textoAntigo)

    def iniciarTransmissao(self):
        self.looping = threading.Timer(0.02, self.iniciarTransmissao)
        self.cria_dic()
        self.looping.start()

    def terminarTransmissao(self):
        self.looping.cancel()
    
    def closeEvent(self,event):
        try:
            self.looping.cancel()
            self.looping_img.cancel()
            event.accept()
        except:
            self.looping_img.cancel()
            event.accept()

    