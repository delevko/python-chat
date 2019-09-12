from _thread import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import *
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QMessageBox
from PyQt5.QtWidgets import *
from threading import *
from socket import *
import sys, socket, queue, re, select, time

HOST = 'localhost'
PORT = 8880

def message(title, data):
      w = QWidget()
      QMessageBox.information(w, title, data)

queue = queue.Queue()

class Main(QMainWindow):
    def __init__(self, otherClass):
        super().__init__()
        self.other = otherClass

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Message',
            "Logout?", QMessageBox.Yes, QMessageBox.No)

        if reply == QMessageBox.Yes:
            if self.other.logged:
                msg = "logout" + ">>" + self.other.Nickname
                global queue
                queue.put(bytes(msg, 'UTF-8'))
            event.accept()
        else:
            event.ignore()

class GUImainWindow(object):
    def __init__(self):
        self.nicks = ['all']
        self.logged = False
        self.Nickname = None
        self.MainWindow = None

    def GUIsetup(self, MainWindow):
        class textEditor(QTextEdit):
            def __init__(self, parent, outer):
                super().__init__(parent=parent)
                self.outer = outer

            def keyPressEvent(self, qKeyEvent):
                if qKeyEvent.key() == QtCore.Qt.Key_Return:
                    self.outer.mainSender()
                else:
                    super().keyPressEvent(qKeyEvent)

        self.MainWindow = MainWindow
        MainWindow.resize(660, 435)
        MainWindow.setFixedSize(660, 435)
        self.centralwidget = QWidget(MainWindow)
        self.frame = QFrame(self.centralwidget)
        self.frame.setGeometry(QRect(10, 10, 650, 40))
        self.label = QLabel(self.frame)
        self.label.setGeometry(QRect(10, 10, 130, 20))
        self.lineEdit = QLineEdit(self.frame)
        self.lineEdit.setGeometry(QRect(100, 10, 160, 20))
        self.label_2 = QLabel(self.frame)
        self.label_2.setGeometry(QRect(260, 10, 130, 20))
        self.pushButton_login = QPushButton(self.frame)
        self.pushButton_login.setGeometry(QRect(280, 10, 130, 20))

        self.pushButton_login.clicked.connect(self.login)

        self.frame_2 = QFrame(self.centralwidget)
        self.frame_2.setGeometry(QRect(10, 60, 300, 320))
        self.frame_2.setFrameShape(QFrame.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Raised)
        self.textEdit = textEditor(self.frame_2, self)
        self.textEdit.setGeometry(QRect(10, 10, 280, 260))
        self.pushButton_3 = QPushButton(self.frame_2)
        self.pushButton_3.setGeometry(QRect(10, 280, 170, 30))

        self.pushButton_3.clicked.connect(self.mainSender)

        self.combo = QComboBox(self.frame_2)
        self.combo.setGeometry(QRect(190, 280, 100, 30))
        self.combo.addItems(["all"])

        self.frame_3 = QFrame(self.centralwidget)
        self.frame_3.setGeometry(QRect(320, 60, 330, 320))
        self.listWidget = QListWidget(self.frame_3)
        self.listWidget.setGeometry(QRect(10, 10, 310, 300))
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QStatusBar(MainWindow)
        MainWindow.setStatusBar(self.statusbar)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setGeometry(QRect(0, 0, 660, 30))
        self.menuAction = QMenu(self.menubar)
        MainWindow.setMenuBar(self.menubar)

        self.actionExit_2 = QAction(MainWindow)
        self.actionExit_2.triggered.connect(self.logout)

        self.menuAction.addAction(self.actionExit_2)
        self.menubar.addAction(self.menuAction.menuAction())
        self.retranslateGUI(MainWindow)
        QMetaObject.connectSlotsByName(MainWindow)

    def retranslateGUI(self, MainWindow):
        MainWindow.setWindowTitle(QApplication.translate("MainWindow",
              "Local chat", None, 1))
        self.label.setText(QApplication.translate("MainWindow", "Nickname:",
              None, 1))
        self.pushButton_3.setText(QApplication.translate("MainWindow",
              "Send", None, 1))
        self.menuAction.setTitle(QApplication.translate("MainWindow",
              "Menu", None, 1))
        self.actionExit_2.setText(QApplication.translate("MainWindow",
              "Exit", None, 1))
        self.pushButton_login.setText(QApplication.translate("MainWindow", "Login",
            None, 1))

    #message>>receiver>>sender>>msg
    def mainSender(self):
        if not self.logged:
            message("", "Log in first")
        else:
            text = self.textEdit.toPlainText()
            if len(text) < 1:
                msg_box("", "Empty message")
                return
            else:
                target = str(self.combo.currentText())
                msg = "message" + ">>" + target + ">>" + self.Nickname + ">>" + text
                global queue
                queue.put(bytes(msg, 'UTF-8'))
                self.textEdit.clear()

    #login>>nickname
    def login(self):
        if not self.logged:
            nick = self.lineEdit.text()
            if len(nick) < 1:
                message(nick, "At least 1 character long")
            elif nick in self.nicks:
                message(nick, "Choose another nickname")
            else:
                msg = "login" + ">>" + nick
                global queue
                queue.put(bytes(msg, 'utf-8'))
                self.logged = True
                self.Nickname = nick
                message(nick, "You logged in")
        else:
            message("msg", "You are already logged in")

    def logout(self):
        self.MainWindow.close()


class Client(Thread):
    def __init__(self, gui):
        super().__init__(target = self.run, daemon=False)
        self.socket = socket.socket(AF_INET, SOCK_STREAM)

        address = HOST, PORT
        self.socket.connect(address)
        self.buffer = 1024
        self.gui = gui
        self.lock = RLock()
        self.start()

    def run(self):
        inputs = [self.socket]
        outputs = [self.socket]
        while inputs:
            try:
                read, write, exceptional = select.select(inputs, outputs, inputs)
            # if server unexpectedly quit, this will get ValueError (file descriptor < 0)
            except ValueError:
                self.socket.close()
                break

            if self.socket in read:
                with self.lock:
                    try:
                        data = self.socket.recv(self.buffer)
                    except socket.error:
                        self.socket.close()
                        break

                if data:
                    msg = data.decode('UTF-8')
                    msg_type = msg.split(">>", 1)

                    if(msg_type[0] == "logout"):
                        self.gui.nicks.remove(msg_type[1]);
                        self.gui.combo.clear()
                        self.gui.combo.addItems(self.gui.nicks)
                    elif(msg_type[0] == "login"):
                        self.gui.nicks.append(msg_type[1])
                        self.gui.combo.clear()
                        self.gui.combo.addItems(self.gui.nicks)
                    elif(msg_type[0] == "insert"):
                        listofnicks = msg_type[1].split(">>")

                        for i in listofnicks:
                            if i:
                                self.gui.nicks.append(i)
                        self.gui.combo.clear()
                        self.gui.combo.addItems(self.gui.nicks)
                    else:
                        self.gui.listWidget.addItem(msg+'\n')

            if self.socket in write:
                global queue
                if not queue.empty():
                    data = queue.get()
                    self.sender(data)
                else:
                    time.sleep(0.5)

            if self.socket in exceptional:
                self.socket.close()
                break

    def sender(self, data):
        with self.lock:
            try:
                self.socket.send(data)
            except socket.error:
                self.socket.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    GUI = GUImainWindow()
    MainWindow = Main(GUI)
    GUI.GUIsetup(MainWindow)

    MainWindow.show()

    client = Client(GUI)
    sys.exit(app.exec_())
