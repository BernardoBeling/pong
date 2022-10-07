'''
    - input fields para capturar o nome dos jogadores
    - input fields para informar o endereço ip e porta
    - tipo de conexão (TCP/UDP)
    - botão de conectar

    BJL protocol:
    JOIN;PLAYER_NAME (client-side)
    ACPT;PLAYER_NAME;PLAYER_ID;RESX;RESY (server-side)
    OPPN;NAME;IP (server-side) servidor deve especificar o tipo de erro
    BALL;X;Y
    STRT;TYPE (server-side)
    SHOW;SCOREBOARD
    DROP;
    SHUT;
'''

from socket import *
import multiprocessing
import time, random, sys

def get_external_ip():
    from requests import get
    ip = get('https://api.ipify.org').content.decode('utf8')
    return ip

def get_local_ip():
    s = socket(AF_INET, SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]

def listen_collision(s,p_queue):
    res = ''
    while True:                    
        if not p_queue.empty():                 
            p_queue.get()
            print('esvaziou a fila')

        try: #fix BlockingIO Winerror 10035 
            msg = s.recv(1500)
            res = msg.decode().split(';')
        except error:
            time.sleep(1)

        if res[0] == 'COLI':
            if p_queue.empty():
                p_queue.put(res)
                time.sleep(1)

class server:
    def __init__(self,ip,port,log,max_players = 2, res_x = 800, res_y = 600):
        self.ip = ip
        self.port = port
        self.players_count = 0
        self.res_x = res_x
        self.res_y = res_y
        self.ball_pos = [None,None] #X,Y
        self.ball_x_dir = None
        self.ball_y_dir = None
        self.max_players = max_players
        self.state = 0 #0: lobby, 1: Game started, 2:Game finished!
        self.players = [] #queue (name,ip,position) player 1: right / player2: left
        self.refresh = False
        self.scoreboard = []
        self.log = log

    def set_ball(self):
        self.ball_pos = [self.res_x/2,self.res_y/2]
        self.ball_x_dir = random.choice((-7,7))
        self.ball_y_dir = random.choice((-1,1))
    
    def update_ball(self,s):
        self.ball_pos[0] += self.ball_x_dir
        self.ball_pos[1] += self.ball_y_dir
        
        if int(self.ball_pos[0]) <= 0:
            self.update_scoreboard(0)
            return True
        elif int(self.ball_pos[0]) >= self.res_x: #gol
            self.update_scoreboard(1)
            return True
        elif int(self.ball_pos[1]) <= 0 or int(self.ball_pos[1]) >= self.res_y:
            self.ball_y_dir *= -1
            return False

        #print(f'BALL;{self.ball_pos[0]};{self.ball_pos[1]}')

        time.sleep(0.01666) #60 fps 1/60
        s.sendto(f'BALL;{self.ball_pos[0]};{self.ball_pos[1]}'.encode(), self.players[0][1])
        s.sendto(f'BALL;{self.ball_pos[0]};{self.ball_pos[1]}'.encode(), self.players[1][1])
    
    '''
    Fazer com que ambos players enviem suas posicoes e as colisoes serem calculadas no server, 
    de modo que ball x == player x -> inverte ball xdir
    '''
    #def collision(self):
        #if 

    def listen_moves(self,s):
        while True:        
            msg = s.recv(1500)
            res = msg.decode().split(';')

            if res[0] == 'OPMV':
                self.players[int(res[1])][2] = int(res[2])

    def set_scoreboard(self):
        for i in range(len(self.players)):
            self.scoreboard.append([self.players[i][0],0])
    
    def update_scoreboard(self, pos):      
        self.scoreboard[pos][1] += 1
        print(f'PLACAR - {self.scoreboard[0][0]}: {self.scoreboard[0][1]}, \
        {self.scoreboard[1][0]}: {self.scoreboard[1][1]}') 
    
    def print_scoreboard(self):
        scoreboard_str = '='*5 + ' Scoreboard ' + '='*5 +'\n'\
            + str(self.scoreboard).replace("'","").replace("{","").replace("}","") + '\n'\
                + '='*22
        print(scoreboard_str)
        return scoreboard_str
    
    def printl(self,string):
        print(string)
        log.write(string + '\n')
    
    def start(self,s,p_queue):
            
        self.printl(f'Server online on {self.ip}:{self.port} with UDP connection!')

        players_ready = []
        goal = False
        timeout_time = 60 #s
        while 1:
            if self.state == 0: #lobby
                s.settimeout(timeout_time)
                try:
                    if self.players_count == self.max_players:
                        if any("192" in x for x in self.players[0][1][0].split('.')) and not any("192" in x for x in self.players[1][1][0].split('.')):                    
                            s.sendto(f'OPIP;{get_external_ip()}:{self.players[0][1][1]}'.encode(),self.players[1][1])
                        elif any("192" in x for x in self.players[1][1][0].split('.')) and not any("192" in x for x in self.players[0][1][0].split('.')):                        
                            s.sendto(f'OPIP;{get_external_ip()}:{self.players[1][1][1]}'.encode(),self.players[0][1])

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
                            self.players.append([name,clientIP,self.res_y/2]) #create player
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

                if res[0] == 'STRT':
                    # players_ready.append(res[1])
                    # print(players_ready)
                    # if len(set(players_ready)) == 2:
                        s.sendto(f'STRT;'.encode(),self.players[0][1])
                        s.sendto(f'STRT;'.encode(),self.players[1][1])
                        self.set_scoreboard()
                        self.set_ball()
                        time.sleep(2)
                        s.sendto(f'BALL;{self.ball_pos[0]};{self.ball_pos[1]}'.encode(), self.players[0][1])
                        s.sendto(f'BALL;{self.ball_pos[0]};{self.ball_pos[1]}'.encode(), self.players[1][1])
                        self.state = 2
                        col_process.start()

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
                            self.set_ball()
                            time.sleep(1)
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

if __name__ == '__main__':
    
    if len(sys.argv) > 1 and sys.argv[1] == 'l':
        ip = 'localhost'
    else:
        ip = get_local_ip()

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
    server.start(s,p_queue)
    log.close()