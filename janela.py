"""
Lembrar de atualizar as opções de botões da interface de acordo com as necessidades de regras novas, é importante avisar que
nem todas as regras estão funcionando perfeitamente para o VSSS.

Também, esse código foi desenvolvido tendo em mente comunição por protobuff, porém, a última versão do github será com tudo relacionado
ao protobuff comentado, caso for mantido o uso do mesmo, descomentar. Foram usados apenas comentários por "#"

Alguns problemas identificados:

    - Delay entre recebimento de informação e geração da imagem

    - Não foi possível escrever os números de cada robô

    - Possível problema: Quando estava gerando essa interface, foi solicitado que o dicionário à ser enviado para o Controle só fosse
    atualizado ao ser apertado um dos botões de fouls, isso pode gerar problema caso o botão de foul seja apertado antes do quadrante,
    por exemplo. Verificar se isso vai causar problemas mesmo, como não foi possível testar com outros usuários, não foi confirmado 
    esse possível problema


Ideia de soluções:

Ideia para o problema de delay
    -   Arrumar outra maneira para gerar os quadrados de robôs, suposição que talvez seja esse o problema no delay.
        Algo tipo usar a função cv2.drawContours() para gerar todos os quadrados de um time e uma vez só.
        Sem ideia de como realizar isso.
        Lembrar de verificar se é realmente o cv2.drawContours() que está gerando delay, é só uma suposição que deveria ter sido
        testada por um membro, mas até o momento do comentário, não foi confirmada
    
    -   Outra possibilidade que o problema de delay seja inerente do python na geração dos quadrados, assim, foi levantada a ideia
        migrar para C++, além dele ser mais completo para QtDesigner, é uma linguagem mais rápida que python.


Ideia para o problema de não estar sendo possível escrever os números de cada robô:
Pode também solucionar o problema de delay:
    -   Gerar um Qlabel que "anda" ao invés de gerar o quadrado no campo, algo tipo:
        # Girar o QLabel 90 graus
        transform = QTransform()
        transform.rotate(90)
        lbl_robot_blue_0.setTransform(transform)

        #NÃO FOI TESTADO
        #NÃO FOI CRIADO O "lbl_robot_blue_0", CRIAR ANTES DE TESTAR
        #Tive essa ideia quando já no fim da área da Visão Computacional, simplesmente não quis testar <3

Talvez solucione o problema de delay pois não será mais necessário gerar o frame com todas novas informações (Tipo robôs, ângulos e bola).
Apenas seria andado o Qlabel representando cada robô. Vai haver a necessidade de achar uma solução para caso seja perdido um robô.
"""

from PyQt5.QtWidgets import QDialog, QLabel
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.uic import loadUi
import threading
import cv2
import numpy as np
import math
#from vss_communication import StrategyControl, Referee

class GUI_main_window(QDialog):
    def __init__(self, app):
        super(GUI_main_window, self).__init__()
        loadUi("main_window.ui",self)
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
        
        global img
        global cache
        img = cv2.imread('Field.jpg')   

        #self.mray = False
        #self.referee = Referee()
        #self.vision = StrategyControl(ip='224.5.23.2', port=10015, yellowTeam=self.mray, logger=False, pattern='ssl', convert_coordinates=True)  # Criação do objeto do controle e estratégia

        self.draw_all()
        self.get_vision_data()


    def rotate(self,points, angle):

        """
        Rotação dos robôs

        --------------------

        Ângulo tá recebendo em radianos, como o Y cresce para baixo, tem que inverter para rotação correta
        """

        ANGLE = -angle
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

        return novo_x, novo_y

    def edges_robot(self,x,y):
        """
        O tamanho dos robôs no VSSS era de 7,5 cm, para tanto, foi feito o cálculo de conversão, por isso o 7,5/2
        nas definições de X,Y

        O 850 se refere aos pixels em X do pixmap
        O 170 se refere aos cms em X do campo
        Convertendo assim de cm para pixels
        """
        x1 = x-(7.5/2)*850/170
        x2 = x+(7.5/2)*850/170
        y1 = y-(7.5/2)*850/170
        y2 = y+(7.5/2)*850/170
        return (x1,y1),(x1,y2),(x2,y2),(x2,y1)


    def draw_robot(self):
        cache = img.copy()

        for i in range(0,3):
            try:
                """
                Protobuff tá passando as informações de maneira diferente às necessáris para gerar o desenho do robô, então
                antes de desenhar, é necessário várias etapas de conversão de dados
                """
                novo_x, novo_y= self.cm_to_pxl(self.robots_blue[i]['x'],self.robots_blue[i]['y'])
                p1,p2,p3,p4 = self.edges_robot(novo_x, novo_y)
                p1_draw,p2_draw,p3_draw,p4_draw = self.rotate((p1,p2,p3,p4),self.robots_blue[i]['orientation'])
                pp = np.array([p1_draw,p2_draw,p3_draw,p4_draw])
                cv2.drawContours(cache, [pp], -1, (0, 0, 255), -1)
                """
                Corrigir indexição caso necessário
                """
                #cache.setText(str(self.robots_blue[i]['id']),(novo_x,novo_y))
            except IndexError:
                pass
            except AttributeError:
                pass

        for i in range(0,3):
            try:
                novo_x, novo_y = self.cm_to_pxl(self.robots_yellow[i]['x'], self.robots_yellow[i]['y'])
                p1,p2,p3,p4 = self.edges_robot(novo_x, novo_y)
                p1_draw,p2_draw,p3_draw,p4_draw = self.rotate((p1,p2,p3,p4),self.robots_yellow[i]['orientation'])
                pp = np.array([p1_draw,p2_draw,p3_draw,p4_draw])
                cv2.drawContours(cache, [pp], -1, (255, 255, 0), -1)
                #cache.setText(str(self.robots_blue[i]['id']),(novo_x, novo_y))
            except IndexError:
                pass
            except AttributeError:
                pass
        

        try:
            coordenadas_cm_x, coordenadas_cm_y = self.cm_to_pxl(self.ball['x'], self.ball['y'])
            coordenadas_pxl = (int(coordenadas_cm_x),int(coordenadas_cm_y))
            """
            O tamanho da bolinha do VSSS era de 2,1 cms, diferente dos robôs eu calculei o valor de cms para pixels e coloquei direto,
            sendo essa conversão os 10.5 visto abaixo
            """
            cv2.circle(cache, coordenadas_pxl, int(10.5), (255,165,0), -1)
        except IndexError:
            pass
        except AttributeError:
            pass

        """
        Corrigir ângulo da imagem

        Não sei o pq precisa ser assim, mas sempre que tentei gerar a imagem de outra forma deu erro, duvida?
        Fica alterando os valores de pixmap.shape/pixmap.stride
        """
        _q_image = QImage(cache, cache.shape[1], cache.shape[0], cache.strides[0], QImage.Format_RGB888)
        _q_pixmap = QPixmap.fromImage(_q_image)
        self.QT_jogar.setPixmap(_q_pixmap)


    def get_vision_data(self):


        #self.vision.update(self.mray)
        #self.field = self.vision.get_data()

        #self.robots_blue = self.field[0]["robots_blue"]
        #self.robots_yellow = self.field[0]["robots_yellow"]
        #self.ball = self.field[0]["ball"]

        
        self.looping_data = threading.Timer(0.009, self.get_vision_data)
        self.looping_data.start()




    def draw_all(self):
        """
        Talvez essa função possa ser deletada, só tá aqui porque eu supus que separar aquisição de dados (função acima) e desenho
        não só pudesse reduzir o delay caso separados, como não era necessário gerar 100 fps de imagem para notebooks de 60fps
        enquanto a aquisição rola em aproximademente 100 fps
        """
        self.draw_robot()

        self.looping_img = threading.Timer(0.015, self.draw_all)
        self.looping_img.start()


        

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

        Só atualiza o dicionário quando aperta uma das fouls possíveis (self.RegistraFalta() atualiza o dicionário)
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
            #self.cria_dic()
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
            #self.cria_dic()
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
            #self.cria_dic()
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
            #self.cria_dic()
            
        elif enum == 5:
                self.QT_btStop.setStyleSheet("background-color:green")
                
                self.qt_Label.setText("Stop")
                self.qt_Label.setStyleSheet("background-color:red")

                self.QT_btHalt.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.QT_btStart.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                #self.cria_dic()
        elif enum == 6:
                self.QT_btStart.setStyleSheet("background-color:green")
                
                self.qt_Label.setText("Start")
                self.qt_Label.setStyleSheet("background-color:green")

                self.QT_btHalt.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.QT_btStop.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                #self.cria_dic()
        elif enum == 7:
                self.QT_btHalt.setStyleSheet("background-color:green")
                
                self.qt_Label.setText("Halt")
                self.qt_Label.setStyleSheet("background-color:red")

                self.QT_btStop.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                self.QT_btStart.setStyleSheet("QPushButton{color: rgb(255, 255, 255); background-color: #9F1823;}QPushButton:hover{color: rgb(255, 255, 255);background-color: #ff0000;}")
                #self.cria_dic()

    def mudanca_teamcolor(self, enum):
        """
        Não atualiza o dicionário enviado para a estratégia
        """

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

        """
        Enviando para a interface o texto de foul enviado para a estratégia
        """

        textoAtual = "Caso atual:" +str(self.FaltaTextoAtual) +str(self.CorTextoAtual) +str(self.QuadranteTextoAtual)
        textoAntigo = "Caso Anterior:" +str(self.FaltaTextoAnterior) +str(self.CorTextoAnterior) +str(self.QuadranteTextoAnterior)


        self.qt_FaltaAtual.setText(textoAtual)
        self.qt_UltimaFalta.setText(textoAntigo)

    def iniciarTransmissao(self):
        """
        Looping dos dados de foul
        """
        self.looping = threading.Timer(0.1, self.iniciarTransmissao)
        #self.cria_dic()
        self.looping.start()

    def terminarTransmissao(self):
        self.looping.cancel()
    
    def closeEvent(self,event):
        try:
            self.looping.cancel()
            self.looping_img.cancel()
            self.looping_data.cancel()
            event.accept()
        except:
            self.looping_data.cancel()
            self.looping_img.cancel()
            event.accept()