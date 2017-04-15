#!/usr/bin/env python

from websocket_server import WebsocketServer
import os, pwd, grp

current_game_id = 0
games = dict()

def drop_privileges(uid_name='nobody', gid_name='nogroup'):
        if os.getuid() != 0:
        # We're not root so, like, whatever dude
                return

        # Get the uid/gid from the name
        running_uid = pwd.getpwnam(uid_name).pw_uid
        running_gid = grp.getgrnam(gid_name).gr_gid

        # Remove group privileges
        os.setgroups([])

        # Try setting the new uid/gid
        os.setgid(running_gid)
        os.setuid(running_uid)

        # Ensure a very conservative umask
        old_umask = os.umask(077)

# Called for every client connecting (after handshake)
def new_client(client, server):
        global current_game_id
        print("New client connected and was given id %d" % client['id'])

# Called for every client disconnecting
def client_left(client, server):
        try:
                client_id = client['id']
                for game in games:
                        game['players'].discard(client_id)
                print("Client(%d) disconnected" % client_id)
        except TypeError:
                pass

def handle_ping(client, server):
        print "ping received from client %d" % (client['id'])
        server.send_message(client, "PONG")
        return

def find_client(server, player):
        for cli in server.clients:
                if cli['id'] == player:
                        return cli

        raise IndexError

def notify_players(server, game, winner):
        disconnected_players = set()
        for player in game['players']:
                if player == winner:
                        print "Ignoring client %u" % player
                        continue
                try:
                        server.send_message(find_client(server, player), "WIN;%u;%s" % (game['gameid'], game['last_winner'].decode('utf-8')))
                except(IndexError):
                        print "Player %u appears to have disconnected, discarding" % player
                        disconnected_players.add(player)

        game['players'] -= disconnected_players

def update_game_state(game, winner):
        global current_game_id

        current_game_id += 1
        game['gameid'] = current_game_id # TODO: Possible race condition. Shouldn't matter though
        game['last_winner'] = winner

def find_game(groupname, expected_game_id):
        try:
                game = games[groupname]
        except(KeyError):
                print "Invalid group name %s" % groupname
                raise

        if expected_game_id != game['gameid']:
                print "Invalid game id %u (should be %u)" % (int(gameid), game['gameid'])
                raise KeyError

        return game

def handle_win(client, server, params):
        groupname, gameid, winner = params.split(";", 2)

        try:
                game = find_game(groupname, int(gameid))
        except(KeyError):
                return

        print "Client %u (%s) wins game %u" % (client['id'], winner, game['gameid'])

        update_game_state(game, winner[:100])

        notify_players(server, game, client['id'])

def handle_signin(client, server, groupname):
        global current_game_id

        try:
                game = games[groupname]
                print "Found group name %s for client %u" % (groupname, client['id'])
        except(KeyError):
                print "New group name %s for client %u" % (groupname, client['id'])
                game = {"gameid": current_game_id, "last_winner": "", "players" : set()}
                games[groupname] = game

        game['players'].add(client['id'])
        server.send_message(client, "SIGNIN;%u;%s" % (game['gameid'], game['last_winner']))

def handle_unknown_opcode(message):
        print "Opcode not recognized. Message was: %s" % message

# Called when a client sends a message
def message_received(client, server, message):
        if message == 'PING':
                handle_ping(client, server)

        opcode, params = message.split(";", 1)
        if opcode == "WIN":
                handle_win(client, server, params)
        elif opcode == "SIGNIN":
                handle_signin(client, server, params)
        else:
                handle_unknown_opcode(message)


# def main():
PORT=9001
drop_privileges()
server = WebsocketServer(PORT)
server.set_fn_new_client(new_client)
server.set_fn_client_left(client_left)
server.set_fn_message_received(message_received)
server.run_forever()
