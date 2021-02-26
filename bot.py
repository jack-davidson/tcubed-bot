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
    board_string = ""
    for row in board_matrix:
        for cell in row:
            board_string += serialize_turn(cell)
    return board_string


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
def best_move(board, player):
    return api_request(
        format_uri(API_HOST, API_PORT) + "/board/" + board + "/player/"
        + player
    )


class Session:
    class MoveAlreadyTakenError(Exception):
        pass

    def __init__(self, board_string, owner="unkown", bot=False):
        global session_id

        self.board_matrix = deserialize_board(board_string)
        self.player = Player.X
        self.owner = owner
        self.bot = bot

        sessions.append(self)
        session_id = len(sessions) - 1

    def next_player(self):
        self.player = -self.player

    def declare_win(self, player):
        self.game_over = True
        self.winning_player = player

    def move(self, row, col):
        if self.board_matrix[row][col] == Player.E:
            self.board_matrix[row][col] = self.player
            self.next_player()
        else:
            raise Session.MoveAlreadyTakenError

    def moves_left(self):
        for row in self.board_matrix:
            for cell in row:
                if cell == Player.E:
                    return True
        return False

    def __str__(self):
        board_string = ""
        i = 0
        for row in self.board_matrix:
            for cell in row:
                board_string += " "
                if cell != Player.E:
                    board_string += serialize_turn(cell)
                else:
                    board_string += str(i)
                i += 1
            board_string += "\n"

        return "```toml\n" \
               f"[session id: {str(session_id)}] [player: " \
               f"{serialize_turn(self.player)}]\n\n" \
               f"{board_string}```"


async def new(message, bot=False):
    board = Session("E" * 9, owner=message.author)
    if bot is not False:
        board.bot = bot
    await message.channel.send(str(board))


async def move(message, args):
    global session_id
    k = 0
    board = sessions[session_id]
    if not board.moves_left():
        await message.channel.send("there are no moves left")
        return

    if board.bot is not False:
        for i in range(3):
            for j in range(3):
                if k == int(args[2]):
                    try:
                        board.move(i, j)
                    except Session.MoveAlreadyTakenError:
                        await message.channel.send(
                            "```diff\n-move already taken by "
                            f"{serialize_turn(board.board_matrix[i][j])}```"
                        )
                        return
                k += 1

        await message.channel.send(f"```toml\n[Player {serialize_turn(board.player)} is thinking ...]```")
        if not board.moves_left():
            await message.channel.send("there are no moves left")
            return
        board.move(*best_move(serialize_board(board.board_matrix), serialize_turn(board.player)))
    else:
        for i in range(3):
            for j in range(3):
                if k == int(args[2]):
                    try:
                        board.move(i, j)
                    except Session.MoveAlreadyTakenError:
                        await message.channel.send(
                            "```diff\n-move already taken by "
                            f"{serialize_turn(board.board_matrix[i][j])}```"
                        )
                        return
                k += 1

    await message.channel.send(str(board))


async def select(message, args):
    global session_id
    if int(args[2]) <= len(sessions) - 1:
        session_id = int(args[2])

    await list_sessions(message)


async def list_sessions(message):
    board_message = "```toml\n[boards]:\n"
    for i in range(len(sessions)):
        if i == session_id:
            board_message += f"\t[session_id: {i}] [owner: " \
                f"{sessions[i].owner}]\n"
        else:
            board_message += f"\t session_id: {i} | owner: " \
                f"{sessions[i].owner}\n"
    board_message += "```"
    await message.channel.send(board_message)


# ttt main function (process args etc)
async def ttt(message, args):
    if args[1] == "move":
        await move(message, args)

    if args[1] == "select":
        await select(message, args)

    if args[1] == "new":
        if len(args) == 3:
            if args[2] == "bot":
                await new(message, bot=Player.O)
        else:
            await new(message)

    if args[1] == "list":
        await list_sessions(message)

    if args[1] == "print":
        await message.channel.send(str(sessions[session_id]))


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
