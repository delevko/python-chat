from socket import *
import threading, sys, queue, time

HOST = 'localhost'
PORT = 8880

usersConn = []
nicknames  = []
activeLogins = {}
msgQueue = queue.Queue()

class Server():
    def __init__(self):
        self.server = socket(AF_INET, SOCK_STREAM)
        self.buffer = 1024

        try:
            address = HOST, PORT
            self.server.bind(address)
            self.server.listen(5)
            self.server.setblocking(0)
        except Exception:
            print("Server error")
            return

        self.lock = threading.RLock()
        threading.Thread(target=self.clientConn, daemon=True).start()
        threading.Thread(target=self.mainReceiver, daemon=True).start()
        threading.Thread(target=self.mainSender, daemon=True).start()

        print("Server opened")

    def close(self):
        self.server.close()

    def clientConn(self):
        while True:
            try:
                #synchronizacja polaczen z serverem
                self.lock.acquire()
                #blocking
                conn, addr = self.server.accept()
                conn.setblocking(0)
                if conn not in usersConn:
                    usersConn.append(conn)
            except:
                pass
            finally:
                #unblocking
                self.lock.release()
            time.sleep(0.5)

    def mainReceiver(self):
        while True:
            for conn in usersConn:
                try:
                    #synchronizacja wiadomosci
                    self.lock.acquire()
                    #blocking
                    msg = conn.recv(self.buffer)
                except:
                    msg = None
                finally:
                    #unblocking
                    self.lock.release()

                if msg:
                    msg = msg.decode('UTF-8')
                    action = msg.split(">>", 1)[0]

                    msg = msg.split(">>", 3)
                    if action == "login":
                        #  login>>nickname
                        activeLogins[msg[1]] = conn


                        print(msg[1] + ' connected')
                        #self.msgQueue.put( ('all', 'login', msg[1]+' entered the chat room') )
                        msgQueue.put( ('all', 'login', msg[1]) )
                        nicknames.append(msg[1])
                    elif action == "logout":
                        #logout>>nickname
                        try:
                            #usuwam uzytkownika z polaczen i nicknamow
                            nicknames.remove(msg[1])
                            usersConn.remove(activeLogins[msg[1]])
                            activeLogins.pop(msg[1], None)
                        except:
                            pass
                        #mowie wszystkim kto sie wylogowal
                        msgQueue.put( ('all', 'logout', msg[1]+' left the chat room') )
                        print(msg[1] + ' disconnected')
                    else:
                        # message>>receiver>>sender>>msg
                        msgQueue.put( (msg[1], msg[2], msg[3]) )

    def mainSender(self):
        while True:
            if msgQueue.empty():
                time.sleep(1)
            else:
                (receiver, sender, msg) = msgQueue.get()
                if receiver == 'all':
                    self.groupMsg(sender, msg)
                else:
                    self.directMsg(receiver, sender, msg)
                msgQueue.task_done()

    def groupMsg(self, sender, msg):
        for conn in usersConn:
            try:
                #synchronizacja wiadomosci grupowej
                self.lock.acquire()
                data = bytes(sender+">>"+msg, 'UTF-8')
                conn.send(data)
            except:
                pass
            finally:
                self.lock.release()

        if sender == "login":
            temp = ""
            for i in nicknames:
                if msg != i:
                    temp += i + ">>"

            if temp != "":
                time.sleep(0.05)
                self.directMsg(msg, "insert", temp)

    def directMsg(self, receiver, sender, msg):
        address = activeLogins[receiver]
        try:
            #synchronizacja wiadomosci osobowej
            self.lock.acquire()
            data = bytes(sender + ">>" + msg, 'UTF-8')
            address.send(data)
        except:
            pass
        finally:
            self.lock.release()

if __name__ == '__main__':
    server = Server()
    while True:
        try:
            print("Ctrl+C to close")
            input()
        except:
            print("Shutting down the server")
            server.close()
            break
