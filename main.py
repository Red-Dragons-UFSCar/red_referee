from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QApplication
import sys
import janela

class Janela(QtWidgets.QMainWindow, janela.GUI_main_window):
    def __init__(self, parent=None):
        super(Janela, self).__init__(parent)

def main():
    app = QApplication(sys.argv)
    form = Janela()
    form.show()
    app.exec_()

if __name__ == '__main__':
    main()