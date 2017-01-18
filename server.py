#!/usr/bin/env python

from websocket_server import WebsocketServer

# Called for every client connecting (after handshake)
def new_client(client, server):
        print("New client connected and was given id %d" % client['id'])

# Called for every client disconnecting
def client_left(client, server):
        print("Client(%d) disconnected" % client['id'])

# Called when a client sends a message
def message_received(client, server, message):
        if message == 'PING':
                print "ping received from client %d" % (client['id'])
                server.send_message(client, "PONG")
                return
        for cli in server.clients:
                if cli == client:
                        continue
                server.send_message(cli, message.encode('utf-8'))

PORT=9001
server = WebsocketServer(PORT)
server.set_fn_new_client(new_client)
server.set_fn_client_left(client_left)
server.set_fn_message_received(message_received)
server.run_forever()
