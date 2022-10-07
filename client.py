import sys
from socket import *
from pygame import *
import multiprocessing

def update_ball(x,y,colision):
    ball.center = (int(x),int(y))

    if ball.colliderect(players[int(client_id)]) and colision == True:
        my_socket.sendto(f'COLI;'.encode(), (server_ip,server_port))
        colision = False
    elif not colision:
        if x == width/2:
            colision = True
    else:
        my_socket.sendto(f'RFSH;'.encode(),(server_ip,server_port))

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
        Rect(width - 20, height/2 - 70,10,player_height_ratio),
        Rect(10, height/2 - 70,10,player_height_ratio)
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

    if get_init():
        my_socket.sendto(f'STRT;{client_id}'.encode(), (server_ip,server_port))
    start = False

    while True:
        msg = my_socket.recv(1500)
        res = msg.decode().split(';')

        if res[0] == 'STRT':
            start = True

        if res[0] == 'BALL': #BALL;X,Y
        
            allow_colision = update_ball(float(res[1]),float(res[2]), allow_colision)

        if res[0] == 'OPMV': #OPMV;OP_ID;MOVE
            update_player(players[int(res[1])],int(res[1]),res[2])

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
    global width, height
    name = input('Player name: ')
    server_ip = input('Server ip (default localhost): ') or 'localhost'
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

            status, svname, client_id, width, height = msg.decode().split(';')
            if status == 'ACPT' and svname == name:
                print(f'Sucessfully joined server! Player id: {client_id}')
                width, height = int(width), int(height)
                break

        except timeout as err:
            attempts += 1
    else:
        print('No response from the server after 15s (3 attempts)...')

    my_socket.settimeout(60)
    print('Waiting for opponent to connect...')
    opponent_ip = ''
    opponent_name = ''
    try:
        while True: #Wait for communication between clients
            msg = my_socket.recv(1500) #OPPN;NAME;IP
            res = msg.decode().split(';')
        
            if res[0] == 'OPPN':
                opponent_ip = res[2].replace('(','').replace(')','').replace("'",'').replace(' ','').split(',')
                if opponent_ip.split('.')[0] == '192': #tratando caso em que um player esta na mesma rede que o servidor
                    opponent_ip[0] = server_ip
                opponent_name = res[1]
                print(f'tentando enviar para {opponent_ip[0]}:{int(opponent_ip[1])}')
                my_socket.sendto(f'HELO;HELLO FROM {name}'.encode(), (opponent_ip[0],int(opponent_ip[1])))

            elif res[0] == 'HELO':
                print(res[1])
                break
        
    except timeout as err:
        print('No response from opponent.')

    status = ''
    type = ''
    log = open('client_log.txt','w')
    print(f'Client id: {client_id}')
    run_gui(client_id, my_socket, opponent_ip, server_ip, server_port)