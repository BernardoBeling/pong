import sys
from socket import *
from pygame import *
import multiprocessing

def update_ball(x,y):
    # global speed_x, speed_y
    ball.center = (int(x),int(y))
    #print(x,y)
    
    if ball.colliderect(players[int(client_id)]):
        my_socket.sendto(f'COLI;X;{client_id}'.encode(), (server_ip,server_port))
    else:
        my_socket.sendto(f'RFSH;'.encode(),(server_ip,server_port))

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
    global width, height, players, ball, window, light, bg
    width, height = 1280, 960
    window = display.set_mode((width,height))
    display.set_caption('Pong')    

    players = [
        Rect(width - 20, height/2 - 70,10,140),
        Rect(10, height/2 - 70,10,140)
    ]

    ball = Rect(width/2 - 15, height/2 - 15,30,30)

    bg = Color('grey12')
    light = (200,200,200)

def run_gui(client_id, my_socket, op_ip, server_ip, server_port):
    #Pygame initial setup
    init()
    clock = time.Clock()

    init_gui()

    global player_speed
    player_speed = 0

    if get_init():
        my_socket.sendto(f'STRT;{client_id}'.encode(), (server_ip,server_port))
    start = False

    while True:
        msg = my_socket.recv(1500)
        res = msg.decode().split(';')

        if res[0] == 'STRT':
            start = True

        if res[0] == 'BALL': #BALL;X,Y
            update_ball(float(res[1]),float(res[2]))

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

            status, svname, client_id = msg.decode().split(';')
            if status == 'ACPT' and svname == name:
                print(f'Sucessfully joined server! Player id: {client_id}')
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
                opponent_name = res[1]
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