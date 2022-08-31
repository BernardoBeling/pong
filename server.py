'''
    - input fields para capturar o nome dos jogadores
    - input fields para informar o endereço ip e porta
    - tipo de conexão (TCP/UDP)
    - botão de conectar

    BJL protocol:
    JOIN;PLAYER_NAME (client-side)
    ACPT;PLAYER_NAME;PLAYER_ID (server-side)
    OPPN;NAME;IP (server-side) servidor deve especificar o tipo de erro
    BALL;X;Y
    STRT;TYPE (server-side)
    SHOW;SCOREBOARD
    DROP;
    SHUT;
'''

from socket import *
import multiprocessing
import time, random

class server:
    def __init__(self,ip,port,log,max_players = 2):
        self.ip = ip
        self.port = port
        self.players_count = 0
        self.ball_pos = [1280/2,960/2] #X,Y
        self.ball_x_dir = None
        self.ball_y_dir = None
        self.max_players = max_players
        self.state = 0 #0: lobby, 1: Game started, 2:Game finished!
        self.players = [] #queue (name,ip,position) player 1: right / player2: left
        self.refresh = False
        self.scoreboard = {}
        self.turn = None
        self.log = log

    def set_turn(self):
        self.turn = 1 if self.ball_x_dir <= 0 else 0

    def set_ball(self):
        self.ball_pos = [1280/2,960/2]
        self.ball_x_dir = random.choice((-7,7))
        self.ball_y_dir = random.choice((-1,1))
        self.set_turn()
    
    def update_ball(self,s):
        self.ball_pos[0] += self.ball_x_dir
        self.ball_pos[1] += self.ball_y_dir
        
        if int(self.ball_pos[0]) <= 0 or int(self.ball_pos[0]) >= 1280: #gol
            print('gol')
            return True

        elif int(self.ball_pos[1]) <= 0 or int(self.ball_pos[1]) >= 960:
            self.ball_y_dir *= -1
            return False

        #print(f'BALL;{self.ball_pos[0]};{self.ball_pos[1]}')

        time.sleep(0.01666) #60 fps 1/60
        s.sendto(f'BALL;{self.ball_pos[0]};{self.ball_pos[1]}'.encode(), self.players[0][1])
        s.sendto(f'BALL;{self.ball_pos[0]};{self.ball_pos[1]}'.encode(), self.players[1][1])
    
    def listen_collision(self,s,p_queue):
        last_collision = None
        while True:                    
            if not p_queue.empty():              
                last_collision = None
                p_queue.get()
                print('esvaziou a fila')

            msg = s.recv(1500)
            res = msg.decode().split(';')

            if res[0] == 'COLI' and (last_collision == None or last_collision != res[2]): #colision
                if p_queue.empty():
                    p_queue.put(res)
                    last_collision = res[2]
                    time.sleep(1)

    def listen_moves(self,s):
        while True:        
            msg = s.recv(1500)
            res = msg.decode().split(';')

            if res[0] == 'OPMV':
                self.players[int(res[1])][2] = int(res[2])

    def set_scoreboard(self):
        p1_name = self.players[0][1]
        p2_name = self.players[1][1]

        self.scoreboard[p1_name] = 0
        self.scoreboard[p2_name] = 0
    
    def update_scoreboard(self, name):       
        self.scoreboard[name] += 1
    
    def print_scoreboard(self):
        scoreboard_str = '='*5 + ' Scoreboard ' + '='*5 +'\n'\
             + str(self.scoreboard).replace("'","").replace("{","").replace("}","") + '\n'\
                + '='*22
        print(scoreboard_str)
        return scoreboard_str
    
    def printl(self,string):
        print(string)
        log.write(string + '\n')
    
    def start(self):
        s = socket(AF_INET,SOCK_DGRAM)
        try:
            s.bind((self.ip,self.port))
        except socket.error as err:
            print(f'Error binding server to IP:PORT\n Error: {err}')
            return False
            
        self.printl(f'Server online on {self.ip}:{self.port} with UDP connection!')

        players_ready = []

        p_queue = multiprocessing.Queue()
        col_process = multiprocessing.Process(target=self.listen_collision,args=(s,p_queue))
        goal = False
        while 1:
            if self.state == 0: #lobby
                s.settimeout(60)
                try:
                    if self.players_count == self.max_players:
                        for i in range(2): #2 first players from queue
                            oppn = 1 if i == 0 else 0                            
                            s.sendto(f'OPPN;{self.players[oppn][0]};{self.players[oppn][1]}'.encode(), self.players[i][1])
                            self.state = 1                             
                    else:
                        msg, clientIP = s.recvfrom(1500)
                        res = msg.decode().split(';')

                        if res[0] == 'JOIN' and self.players_count < self.max_players:
                            name = res[1]
                            self.players_count += 1
                            self.players.append([name,clientIP,960/2]) #create player
                            print(f'{name} joined server!')                    
                            s.sendto(f'ACPT;{name};{self.players_count-1}'.encode(), clientIP)
                        
                    self.printl(f'Total players: {self.players_count}/{self.max_players}')

                except timeout as err:
                    self.printl(f'No connection attempts after 15s...\nError: {err}, exiting...')
                    s.close()
                    break

            elif self.state == 1: #wait both players to be ready
                msg, clientIP = s.recvfrom(1500)
                res = msg.decode().split(';')

                if res[0] == 'STRT':
                    players_ready.append(res[1])
                    if len(set(players_ready)) == 2:
                        s.sendto(f'STRT;'.encode(),self.players[0][1])
                        s.sendto(f'STRT;'.encode(),self.players[1][1])
                        self.set_scoreboard()
                        self.set_ball()
                        s.sendto(f'BALL;{self.ball_pos[0]};{self.ball_pos[1]}'.encode(), self.players[0][1])
                        s.sendto(f'BALL;{self.ball_pos[0]};{self.ball_pos[1]}'.encode(), self.players[1][1])
                        self.state = 2
                        col_process.start()

            elif self.state == 2: #game started

                if not p_queue.empty():
                    collision = p_queue.get()
                    if collision[1] == 'X':                        
                        self.ball_x_dir *= -1                        
                    elif collision[1] == 'Y':
                        self.ball_y_dir *= -1
                    self.set_turn()
                else:
                    goal = self.update_ball(s)
                    if goal:
                        if p_queue.empty():
                            p_queue.put('GOAL')                            
                            self.set_ball()
                        #self.update_scoreboard()

            elif self.state == 3: #game finished
                scoreboard_str = self.print_scoreboard()
                self.clear_moves()
                for p in self.players:
                    show_msg = f'SHOW;{scoreboard_str}'.encode()
                    s.sendto(show_msg,p.ip)
                    s.sendto('SHUT;'.encode(),(p.ip))
                break
        return

    def __del__(self):
        print('Server closed!')

ip = input('Server ip (default localhost): ') or 'localhost'
port = int(input('Server port (default 50000): ') or 50000)
log = open('server_log.txt', 'w')
server = server(ip,port,log)
server.start()
log.close()