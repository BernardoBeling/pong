'''
    - input fields para capturar o nome dos jogadores
    - input fields para informar o endereço ip e porta
    - tipo de conexão (TCP/UDP)
    - botão de conectar

    BELOJO protocol:
    JOIN;PLAYER_NAME (client-side)
    ACPT;PLAYER_NAME;PLAYER_ID;RESX;RESY (server-side)
    OPPN;IP;NAME (server-side)
    BALL;X;Y
    STRT;TYPE (server-side)
    SHOW;SCOREBOARD
    DROP;
    SHUT;
'''

from socket import *
from dataclasses import dataclass, field
from typing import TextIO
import multiprocessing
import time, random, sys

def get_external_ip() -> str:
    from requests import get
    ip = get('https://api.ipify.org').content.decode('utf8')
    return ip

def get_local_ip() -> str:
    s = socket(AF_INET, SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

def listen_collision(s,p_queue) -> None:
    res = ''
    while True:                    
        if not p_queue.empty():                 
            p_queue.get()
     
        try: #fix BlockingIO Winerror 10035 
            msg = s.recv(1500)
            res = msg.decode().split(';')
            
            if res[0] == 'COLI':
                if p_queue.empty():
                    p_queue.put(res)
                    time.sleep(1)
            elif res[0] == 'SHUT':
                s.close()
                break

        except OSError:
            pass

@dataclass
class server:
    ip: str
    port: int
    log: TextIO  
    res_x: int = 1024
    res_y: int = 600
    ball_x_dir: int = None
    ball_y_dir: int = None
    max_players: int = 2
    state: int = 0 #0: lobby, 1: Game started, 2:Game finished!
    players_count: int = 0
    players: list = field(default_factory=list) #queue (name,ip) player 1: right / player2: left
    scoreboard: list = field(default_factory=list)
    ball_pos: list = field(default_factory=list) #X,Y

    def set_ball(self) -> None:
        self.ball_pos = [self.res_x/2,self.res_y/2]
        self.ball_x_dir = random.choice((-7,7))
        self.ball_y_dir = random.choice((-1,1))
    
    def update_ball(self,s) -> bool:
        self.ball_pos[0] += self.ball_x_dir
        self.ball_pos[1] += self.ball_y_dir
    
        if int(self.ball_pos[0]) < -100:
            self.update_scoreboard(1)
            return True
        elif int(self.ball_pos[0]) > self.res_x + 100: #gol
            self.update_scoreboard(0)
            return True
            
        elif int(self.ball_pos[1]) <= 0 or int(self.ball_pos[1]) >= self.res_y:
            self.ball_y_dir *= -1
            return False

        #print(f'BALL;{self.ball_pos[0]};{self.ball_pos[1]}')

        time.sleep(0.01666) #60 fps 1/60
        
        s.sendto(f'BALL;{self.ball_pos[0]};{self.ball_pos[1]}'.encode(), self.players[0][1])
        s.sendto(f'BALL;{self.ball_pos[0]};{self.ball_pos[1]}'.encode(), self.players[1][1])

    def listen_moves(self,s) -> None:
        while True:        
            msg = s.recv(1500)
            res = msg.decode().split(';')

            if res[0] == 'OPMV':
                self.players[int(res[1])][2] = int(res[2])

    def set_scoreboard(self) -> None:
        for i in range(len(self.players)):
            self.scoreboard.append([self.players[i][0],0])
    
    def update_scoreboard(self, pos) -> None:      
        self.scoreboard[pos][1] += 1
        self.print_scoreboard()
    
    def print_scoreboard(self) -> str:
        scoreboard_str = '='*5 + ' Scoreboard ' + '='*5 +'\n'\
            + f'{self.scoreboard[0][0]}: {self.scoreboard[0][1]}, \
        {self.scoreboard[1][0]}: {self.scoreboard[1][1]}' + '\n'\
                + '='*22
        self.printl(scoreboard_str)
        return scoreboard_str
    
    def printl(self,string) -> None:
        print(string)
        log.write(string + '\n')
    
    def start(self,s,p_queue,max_goals) -> None:
            
        self.printl(f'Server online on {self.ip}:{self.port} with UDP connection!')

        players_ready = 0
        games_opened = 0
        goal = False
        timeout_time = 60 #s

        while 1:

            player0_local, player1_local = False, False

            if self.state == 0: #lobby
                s.settimeout(timeout_time)
                try:
                    if self.players_count == self.max_players:

                        if self.players[0][1][0].split('.')[0] == get_local_ip().split('.')[0]:
                            player0_local = True
                        if self.players[1][1][0].split('.')[0] == get_local_ip().split('.')[0]:
                            player1_local = True

                        if (player0_local and player1_local) or (not player0_local and not player1_local):
                                s.sendto(f'OPPN;{self.players[0][1][0]}:{self.players[0][1][1]};{self.players[0][0]}'.encode(), self.players[1][1])
                                s.sendto(f'OPPN;{self.players[1][1][0]}:{self.players[1][1][1]};{self.players[1][0]}'.encode(), self.players[0][1])
                        elif player0_local:                                
                                s.sendto(f'OPPN;{get_external_ip()}:{self.players[0][1][1]};{self.players[0][0]}'.encode(),self.players[1][1])
                                s.sendto(f'OPPN;{self.players[1][1][0]}:{self.players[1][1][1]};{self.players[1][0]}'.encode(),self.players[0][1])
                        elif player1_local:                            
                                s.sendto(f'OPPN;{get_external_ip()}:{self.players[1][1][1]};{self.players[1][0]}'.encode(),self.players[0][1])
                                s.sendto(f'OPPN;{self.players[0][1][0]}:{self.players[0][1][1]};{self.players[0][0]}'.encode(),self.players[1][1])                                                    
                                
                        self.state = 1  
                                                       
                    else:
                        msg, clientIP = s.recvfrom(1500)                        
                        res = msg.decode().split(';') 
                        
                        if res[0] == 'JOIN' and self.players_count < self.max_players:            
                            name = res[1]
                            self.players_count += 1
                            self.players.append([name,clientIP]) #create player
                            print(f'{name} joined server! {clientIP}')     
                                           
                            s.sendto(f'ACPT;{name};{self.players_count-1};{self.res_x};{self.res_y}'.encode(), clientIP)                        

                    self.printl(f'Total players: {self.players_count}/{self.max_players}')

                except timeout as err:
                    self.printl(f'No connection attempts after {timeout_time}s...\nError: {err}, exiting...')
                    s.close()
                    break

            elif self.state == 1: #wait both players to be ready
                msg, clientIP = s.recvfrom(1500)
                res = msg.decode().split(';')

                if res[0] == 'STRT' and players_ready < 2:
                    players_ready += 1

                if players_ready == 2:                    
                    s.sendto(f'STRT;'.encode(),self.players[0][1])
                    s.sendto(f'STRT;'.encode(),self.players[1][1])
                
                if res[0] == 'GAME' and games_opened < 2:
                    games_opened += 1
                
                if games_opened == 2:
                    self.set_ball()
                    self.set_scoreboard()
                    s.sendto(f'GAME;'.encode(),self.players[0][1])
                    s.sendto(f'GAME;'.encode(),self.players[1][1])
                    col_process.start()
                    self.state = 2
                    time.sleep(2)

            elif self.state == 2: #game started

                if not p_queue.empty():
                    collision = p_queue.get()                                          
                    self.ball_x_dir *= -1  
                    self.ball_y_dir *= random.choice((-1,1))                                                            
                else:
                    goal = self.update_ball(s)
                    if goal:
                        if p_queue.empty():
                            p_queue.put('GOAL')                            
                            if self.scoreboard[0][1] == max_goals or self.scoreboard[1][1] == max_goals:
                                self.state = 3
                            self.set_ball()
                            time.sleep(1)                       

            elif self.state == 3: #game finished
                s.sendto(f'SHUT;{self.print_scoreboard()}'.encode(), (self.players[0][1]))
                s.sendto(f'SHUT;{self.print_scoreboard()}'.encode(), (self.players[1][1]))
                print('Terminou o jogo')
                p_queue.put('end')                 
                self.state = 4

            elif self.state == 4:
                s.close()
                col_process.join()               
                exit()
        return

    def __del__(self) -> None:
        print('Server closed!')

if __name__ == '__main__':
    
    ip = get_local_ip()
    max_goals = 10

    if len(sys.argv) > 1 and sys.argv[1] == 'l': 
        ip = 'localhost'
    elif len(sys.argv) > 1:
        max_goals = int(sys.argv[1])
            

    port = int(input('Server port (default 50000): ') or 50000)
    log = open('server_log.txt', 'w')

    s = socket(AF_INET,SOCK_DGRAM)
    try:
        s.bind((ip,port))
    except socket.error as err:
        print(f'Error binding server to IP:PORT\n Error: {err}')
        exit()

    if sys.platform == 'win32':
        multiprocessing.set_start_method('spawn')

    p_queue = multiprocessing.Queue()
    col_process = multiprocessing.Process(target=listen_collision,args=(s,p_queue)) 

    server = server(ip,port,log)
    server.start(s,p_queue,max_goals)
    log.close()
    exit()