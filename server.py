#!/usr/bin/env python3

import os, pwd, grp, asyncio, websockets

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

async def notify_num_players(websocket, game):
        retry = True
        while retry:
                retry = False
                disconnected_players = set()
                for player in game['players']:
                        try:
                                await player.send("PLAYERS;%u" % (len(game['players'])))
                        except(websockets.exceptions.ConnectionClosed):
                                disconnected_players.add(player)
                                retry = True

                game['players'] -= disconnected_players

# Called for every client disconnecting
async def client_left(websocket):
        global games
        for game in games:
                num_players = len(games[game]['players'])
                games[game]['players'].discard(websocket)
                if (len(games[game]['players']) != num_players):
                        print("Client left from game %s" % game)
                        await notify_num_players(websocket, games[game])

async def handle_ping(websocket):
        await websocket.send("PONG")
        return

async def notify_players(websocket, game):
        disconnected_players = set()
        for player in game['players']:
                if player == websocket:
                        continue
                try:
                        await player.send("WIN;%u;%s" % (game['gameid'], game['last_winner']))
                except(websockets.exceptions.ConnectionClosed):
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
                print("Invalid group name %s" % groupname)
                raise

        if expected_game_id != game['gameid']:
                print("Invalid game id %u (should be %u)" % (int(gameid), game['gameid']))
                raise KeyError

        return game

async def handle_win(websocket, params):
        groupname, gameid, winner = params.split(";", 2)

        try:
                game = find_game(groupname, int(gameid))
        except(KeyError):
                return

        print("Client %s wins game %u" % (winner, game['gameid']))

        update_game_state(game, winner[:100])

        await notify_players(websocket, game)

async def handle_signin(websocket, groupname):
        global current_game_id

        print ("Signin to game id %s" % groupname)

        try:
                game = games[groupname]
                print("Found group name %s" % (groupname))
        except(KeyError):
                print("New group name %s" % (groupname))
                game = {"gameid": current_game_id, "last_winner": "", "players" : set()}
                games[groupname] = game

        game['players'].add(websocket)
        await websocket.send("SIGNIN;%u;%s" % (game['gameid'], game['last_winner']))
        await notify_num_players(websocket, game)

def handle_unknown_opcode(message):
        print("Opcode not recognized. Message was: %s" % message)

# Called when a client sends a message
async def message_received(websocket, message):
        if message == 'PING':
                await handle_ping(websocket)

        opcode, params = message.split(";", 1)
        if opcode == "WIN":
                await handle_win(websocket, params)
        elif opcode == "SIGNIN":
                await handle_signin(websocket, params)
        else:
                handle_unknown_opcode(message)

async def client_loop(websocket, path):
        print("Client connected")
        try:
                while True:
                        message = await websocket.recv()
                        await message_received(websocket, message)
        except(websockets.exceptions.ConnectionClosed):
                await client_left(websocket)

# def main():
PORT=9001
drop_privileges()

start_server = websockets.serve(client_loop, 'localhost', PORT)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
