#!/usr/bin/python3
import discord
import json
import requests
import math

client = discord.Client()
sessions = []

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


async def new(message):
    board_matrix = deserialize_board("E" * 9)
    board_message = "```toml\n"
    sessions.append(board_matrix)
    board_message += "[session id: " + str(len(sessions) - 1) + "]\n\n"

    for row in board_matrix:
        for cell in row:
            board_message += " " + serialize_turn(cell)
        board_message += "\n"
    board_message += "```"

    await message.channel.send(board_message)


# ttt main function (process args etc)
async def ttt(message, args):
    if args[1] == "new":
        await new(message)


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
