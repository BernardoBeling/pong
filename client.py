import sys
from time import sleep
from socket import *
from pygame import *

def get_local_ip():
    s = socket(AF_INET, SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

def printl(string):
    log.write(string + '\n')

def update_ball(x,y,colision):
    ball.center = (int(x),int(y))

    if ball.colliderect(players[int(client_id)]) and colision == True:
        my_socket.sendto(f'COLI;'.encode(), (server_ip,server_port))
        colision = False
    elif not colision:
        if x == width/2:
            colision = True

    return colision

def update_player(player, id, top=None):    
    if int(client_id) == int(id):
        player.y += player_speed
    else:
        if top != None:
            player.top = int(top)

    if player.top <= 0:
        player.top = 0
    if player.bottom >= height:
        player.bottom = height

def check_moves(event):
    global player_speed
    if event.type == KEYDOWN:
            if event.key == K_DOWN:                
                player_speed += 7
            if event.key == K_UP:                
                player_speed -= 7
    if event.type == KEYUP:
        if event.key == K_DOWN:               
            player_speed -= 7
        if event.key == K_UP:              
            player_speed += 7

def init_gui():
    global players, ball, window, light, bg
    window = display.set_mode((width,height))
    display.set_caption('Pong')
    ball_ratio = int(width/42)
    player_height_ratio = int(height/7)

    players = [
        Rect(10, height/2 - 70,10,player_height_ratio), #x_pos,y_pos,thickness,height
        Rect(width - 20, height/2 - 70,10,player_height_ratio) #x_pos,y_pos,thickness,height
    ]

    ball = Rect(width/2 - ball_ratio/2, height/2 - ball_ratio/2,ball_ratio,ball_ratio)

    bg = Color('grey12')
    light = (200,200,200)

def run_gui(client_id, my_socket, op_ip, server_ip, server_port):
    #Pygame initial setup
    init()
    clock = time.Clock()
    
    init_gui()

    global player_speed
    player_speed = 0

    allow_colision = True

    my_socket.sendto(f'GAME;{client_id}'.encode(), (server_ip,server_port))
    start = False

    while True:
        msg = my_socket.recv(1500)
        printl(msg.decode())
        res = msg.decode().split(';')

        if res[0] == 'GAME':
            start = True

        if res[0] == 'BALL': #BALL;X,Y
        
            allow_colision = update_ball(float(res[1]),float(res[2]), allow_colision)

        if res[0] == 'OPMV': #OPMV;OP_ID;MOVE
            update_player(players[int(res[1])],int(res[1]),res[2])

        if res[0] == 'SHUT':
            my_socket.sendto(f'SHUT;'.encode(), (server_ip,server_port))
            print(res[1])
            sys.exit()

        #inputs
        for events in event.get():
            if events.type == QUIT:
                quit()
                sys.exit()
            elif events.type == KEYDOWN or events.type == KEYUP:
                check_moves(events)
                my_socket.sendto(f'OPMV;{client_id};{players[int(client_id)].top}'.encode(),(op_ip[0],int(op_ip[1])))
                #my_socket.sendto(f'OPMV;{client_id};{players[int(client_id)].top}'.encode(),(server_ip,server_port))                    

        update_player(players[int(client_id)],int(client_id))

        #drawing
        window.fill(bg)
        draw.rect(window,light,players[0])
        draw.rect(window,light,players[1])
        draw.aaline(window,light,(width/2,0),(width/2,height))
        
        if start: #if window is opened
            draw.ellipse(window,light,ball)

        #Update window
        display.flip()
        clock.tick(60) #60 fps

if __name__ == '__main__':
    global width, height, log

    log = open('client_log.txt','w')
    name = input('Player name: ')

    if len(sys.argv) > 1 and sys.argv[1] == 'l':
        server_ip = 'localhost'
    else:
        server_ip = input('Server ip (default LAN IP): ') or get_local_ip()

    server_port = int(input('Server port (default 50000): ') or 50000)
    attempts = 0
    client_id = 0
    my_socket = socket(AF_INET,SOCK_DGRAM)
    my_socket.settimeout(5)

    while attempts <= 3:
        try:
            print('Attempting to connect...')            
            my_socket.sendto(f'JOIN;{name}'.encode(), (server_ip,server_port))            

            msg = my_socket.recv(1500) #ACPT;NAME;ID
            printl(msg.decode())

            status, svname, client_id, width, height = msg.decode().split(';')
            if status == 'ACPT' and svname == name:
                print(f'Sucessfully joined server! Player id: {client_id}')
                width, height = int(width), int(height)
                break

        except timeout as err:
            attempts += 1
    else:
        print('No response from the server after 15s (3 attempts)...')
        exit()

    my_socket.settimeout(60)
    print('Waiting for opponent to connect...')

    opponent_ip = [None,None]
    opponent_name = ''
    has_opponent = False
    state = 0 #0: wait opponent info from server, 1: wait hello from opponent, 2: wait start from server

    try:
        while True: #Wait for communication between clients
            msg, ip = my_socket.recvfrom(1500) #OPPN;NAME;IP 
            printl(msg.decode())
            res = msg.decode().split(';')
                                            
            if res[0] == 'OPPN' and state == 0:
                opponent_ip = res[1].split(':')
                opponent_name = res[2]
                has_opponent = True
                state = 1
                printl('Received opponent info from server')
                print(f'tentando enviar para {opponent_ip[0]}:{int(opponent_ip[1])}')

            elif res[0] == 'HELO' and state == 1:
                print(res[1])
                my_socket.sendto(f'STRT;'.encode(), (server_ip,server_port))
                state = 2 
                printl('Received hello from opponent')

            elif res[0] == 'STRT' and state == 2:
                printl('Received start from server')
                break

            if has_opponent:
                my_socket.sendto(f'HELO;HELLO FROM {name}'.encode(), (opponent_ip[0],int(opponent_ip[1])))

        
    except timeout as err:
        print('No response from opponent.')
        exit()

    status = ''
    type = ''
    
    print(f'Client id: {client_id}')
    run_gui(client_id, my_socket, opponent_ip, server_ip, server_port)