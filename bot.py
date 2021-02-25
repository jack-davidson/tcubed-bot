#!/usr/bin/python3
import discord
import json
import requests
import math

client = discord.Client()
sessions = []
session_id = 0

API_HOST = "99.189.77.224"
API_PORT = "8000"

with open("discord_token", "r") as f:
    token = f.read()
    f.close


class Player:
    O = -1
    E = 0
    X = 1


turns = {'O': Player.O, 'E': Player.E, 'X': Player.X}
reverse_turns = {value: key for (key, value) in turns.items()}


# convert string to Player
def deserialize_turn(player: str) -> int:
    return turns[player]


# convert Player to string
def serialize_turn(player: 'Player') -> str:
    return reverse_turns[player]


def deserialize_board(board: str) -> list[list[Player]]:
    return [[deserialize_turn(x) for x in board[i:i + int(math.sqrt(len(board)))]]
            for i in range(0, len(board), int(math.sqrt(len(board))))]


def serialize_board(board_matrix):
    pass


# format http uri with host and port
def format_uri(host, port):
    return "http://" + host + ":" + port


# make json get request
def api_request(uri):
    return json.loads(
        requests.get(
            uri
        ).content
    )


# make an api request to tcubed api and return best move given board and player
def best_move(message, board, player):
    return api_request(
        format_uri(API_HOST, API_PORT) + "/board/" + board + "/player/"
        + player
    )


class GameState:
    def __init__(self):
        self.board_matrix = [[Player.E] * 3] * 3
        self.player = Player.X

    def set_owner(self, author):
        self.owner = author

    def set(self, board_string):
        self.board_matrix = deserialize_board(board_string)

    def toggle(self):
        self.player = -self.player

    def declare_win(self, player):
        self.game_over = True
        self.winning_player = player


async def new(message):
    board = GameState()
    board.set_owner(message.author)
    board.set("E" * 9)
    sessions.append(board)
    global session_id
    session_id = len(sessions) - 1
    board_message = f"```toml\n[session id: {session_id}] [player: " \
                    f"{serialize_turn(sessions[session_id].player)}]\n\n"

    i = 0
    for row in board.board_matrix:
        for cell in row:
            board_message += " "
            if cell != Player.E:
                board_message += serialize_turn(cell)
            else:
                board_message += str(i)
            i += 1
        board_message += "\n"
    board_message += "```"

    await message.channel.send(board_message)


async def move(message, args):
    k = 0
    global session_id
    for i in range(3):
        for j in range(3):
            if k == int(args[2]):
                if sessions[session_id].board_matrix[i][j] == Player.E:
                    sessions[session_id].board_matrix[i][j] = sessions[session_id].player
                    sessions[session_id].toggle()
                else:
                    await message.channel.send(f"```diff\n-move already taken by {serialize_turn(sessions[session_id].board_matrix[i][j])}```")
                    return
            k += 1

    board_message = "```toml\n" \
                    f"[session id: {str(session_id)}] [player: " \
                    f"{serialize_turn(sessions[session_id].player)}]\n\n"
    i = 0
    for row in sessions[session_id].board_matrix:
        for cell in row:
            board_message += " "
            if cell != Player.E:
                board_message += serialize_turn(cell)
            else:
                board_message += str(i)
            i += 1
        board_message += "\n"
    board_message += "```"
    await message.channel.send(board_message)


# ttt main function (process args etc)
async def ttt(message, args):
    if args[1] == "move":
        await move(message, args)

    if args[1] == "select":
        global session_id
        if int(args[2]) <= len(sessions) - 1:
            session_id = int(args[2])
            await message.channel.send("```diff\n+switched to game with "
                                       f"session_id: {int(args[2])}```")
        else:
            await message.channel.send("```diff\n-game with session_id: "
                                       f"{int(args[2])} is nonexistent. You "
                                       "can create a game with ttt new.```")

    if args[1] == "new":
        await new(message)

    if args[1] == "list":
        board_message = "```toml\n[boards]:\n"
        for i in range(len(sessions)):
            board_message += f"\t[session_id: {i}] [owner: {sessions[i].owner}]\n"
        board_message += "```"
        await message.channel.send(board_message)

    if args[1] == "print":
        board_message = "```toml\n" \
                        f"[session id: {str(session_id)}] [player:" \
                        f"{serialize_turn(sessions[session_id].player)}]\n\n"
        i = 0
        for row in sessions[session_id].board_matrix:
            for cell in row:
                board_message += " "
                if cell != Player.E:
                    board_message += serialize_turn(cell)
                else:
                    board_message += str(i)
                i += 1
            board_message += "\n"
        board_message += "```"
        await message.channel.send(board_message)


@client.event
async def on_ready():
    print(f"[Connected]: ({client.user})")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    args = message.content.split()

    if args[0] == "ttt":
        await ttt(message, args)


client.run(token)
