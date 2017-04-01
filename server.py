#!/usr/bin/env python

from websocket_server import WebsocketServer

current_game_id = 0
last_winner = ""

# Called for every client connecting (after handshake)
def new_client(client, server):
        global current_game_id
        print("New client connected and was given id %d" % client['id'])
        server.send_message(client, "SIGNIN;%u;%s" % (current_game_id, last_winner))

# Called for every client disconnecting
def client_left(client, server):
        try:
                print("Client(%d) disconnected" % client['id'])
        except TypeError:
                pass

def handle_ping(client, server):
        print "ping received from client %d" % (client['id'])
        server.send_message(client, "PONG")
        return

def handle_win(client, server, params):
        global current_game_id, last_winner
        gameid, winner = params.split(";", 1)

        if int(gameid) != current_game_id:
                print "Invalid game id %u (should be %u)" % (int(gameid), current_game_id)
                return

        print "%s wins game %u" % (winner, current_game_id)

        current_game_id += 1
        last_winner = winner[:100]

        for cli in server.clients:
                if cli == client:
                        continue
                server.send_message(cli, "WIN;%u;%s" % (current_game_id, last_winner.decode('utf-8')))

def handle_unknown_opcode(message):
        print "Opcode not recognized. Message was: %s" % message

# Called when a client sends a message
def message_received(client, server, message):
        if message == 'PING':
                handle_ping(client, server)

        opcode, params = message.split(";", 1)
        if opcode == "WIN":
                handle_win(client, server, params)
        else:
                handle_unknown_opcode(message)


# def main():
PORT=9001
server = WebsocketServer(PORT)
server.set_fn_new_client(new_client)
server.set_fn_client_left(client_left)
server.set_fn_message_received(message_received)
server.run_forever()
