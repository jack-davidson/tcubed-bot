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
    return [
        [deserialize_turn(x) for x in board[i:i + int(math.sqrt(len(board)))]]
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

    def __init__(self, board_string, guest="unkown", owner="unkown",
                 bot=False):

        global session_id

        self.board_matrix = deserialize_board(board_string)
        self.player = Player.X
        self.owner = owner
        self.guest = guest
        self.bot = bot

        sessions.append(self)
        session_id = len(sessions) - 1

    def next_player(self):
        self.player = -self.player

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
        i = 1
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

    # THIS IS HORRIBLE CODE
    def evaluate(self) -> bool:
        # Checking for Rows for X or O victory.
        for row in range(3):
            if self.board_matrix[row][0] == self.board_matrix[row][1] and self.board_matrix[row][1] == self.board_matrix[row][2]:
                if self.board_matrix[row][0] == Player.X:
                    return 1

                elif self.board_matrix[row][0] == Player.O:
                    return -1

        # Checking for Columns for X or O victory.
        for col in range(3):
            if self.board_matrix[0][col] == self.board_matrix[1][col] and self.board_matrix[1][col] == self.board_matrix[2][col]:
                if self.board_matrix[0][col] == Player.X:
                    return 1

                elif self.board_matrix[0][col] == Player.O:
                    return -1

        # Checking for Diagonals for X or O victory.
        if self.board_matrix[0][0] == self.board_matrix[1][1] and self.board_matrix[1][1] == self.board_matrix[2][2]:
            if self.board_matrix[0][0] == Player.X:
                return 1

            elif self.board_matrix[0][0] == Player.O:
                return -1

        if self.board_matrix[0][2] == self.board_matrix[1][1] and self.board_matrix[1][1] == self.board_matrix[2][0]:
            if self.board_matrix[0][2] == Player.X:
                return 1

            elif self.board_matrix[0][2] == Player.O:
                return -1

        # Else if none of them have won then return 0
        return 0


async def message_log(message, msg, err=False):
    await message.channel.send("```diff\n" + "-" if err else "+" + " " + msg
                               + "```")


async def new(message, args, bot=False):
    board = Session("E" * 9, owner=str(message.author))
    if bot is not False:
        board.guest = client.user
        board.bot = bot
    else:
        board.guest = str(message.mentions[0])
    await message.channel.send(str(board))


async def move(message, args):
    global session_id
    k = 1
    board = sessions[session_id]

    if str(message.author) not in [board.owner, board.guest]:
        await message_log(message,
                          f"allowed users of session {session_id} "
                          f"are: {board.owner} and {board.guest}```",
                          err=True)
        return

    if not board.moves_left():
        await message.channel.send("there are no moves left")
        sessions.pop(session_id)
        return

    for i in range(3):
        for j in range(3):
            if k == int(args[2]):
                try:
                    board.move(i, j)
                    win = board.evaluate()
                    if win is not Player.E:
                        await message.channel.send(str(board))
                        await message.channel.send(f"```diff\n+{message.author} wins!```")
                        await message_log(message, f"{message.author} wins!")
                        sessions.pop(session_id)
                        return

                except Session.MoveAlreadyTakenError:
                    await message.channel.send(
                        "```diff\n-move already taken by "
                        f"{serialize_turn(board.board_matrix[i][j])}```"
                    )
                    return
            k += 1

    if board.bot is not False:
        await message.channel.send(str(board))
        if not board.moves_left():
            await message.channel.send("there are no moves left")
            return

        await message.channel.send("I'm thinking gimme a sec")
        board.move(*best_move(serialize_board(board.board_matrix),
                              serialize_turn(board.player)))
        win = board.evaluate()
        if win is not Player.E:
            await message.channel.send(str(board))
            await message.channel.send(f"```diff\n+{board.guest} wins!```")
            await message.channel.send("gg")
            sessions.pop(session_id)
            return

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
            board_message += f"\t[session_id: {i}] [player 1 (X): " \
                f"{sessions[i].owner}] [player 2 (O): {sessions[i].guest}]\n"
        else:
            board_message += f"\t session_id: {i} | player 1 (X): " \
                f"{sessions[i].owner} | player 2 (O): {sessions[i].guest}\n"
    board_message += "```"
    await message.channel.send(board_message)


async def ttt_help(message):
    with open("README.md", "r") as f:
        await message.channel.send("```md\nREADME.md\n\n" + f.read() + "```")
        f.close()


async def usage(message):
    await message.channel.send("```Usage: ttt COMMAND [ARGS] ..."
                               "\nTry 'ttt help' for more information."
                               "\nTry 'ttt license' for license information."
                               "```")


async def license(message):
    with open("LICENSE", "r") as f:
        await message.channel.send("```\n" + f.read() + "```")
        f.close()


# ttt main function (process args etc)
async def ttt(message, args):
    if args[1] == "help":
        await ttt_help(message)
        return

    if args[1] == "license":
        await license(message)
        return

    if args[1] == "move":
        await move(message, args)
        return

    if args[1] == "select":
        await select(message, args)
        return

    if args[1] == "new":
        if len(args) == 3:
            if message.mentions[0] == client.user:
                await new(message, args, bot=Player.O)
            else:
                await new(message, args)
        else:
            await message.channel.send("```diff\n-please mention your "
                                       "opponent after your command: 'ttt new "
                                       "@user'```")
        return

    if args[1] == "list":
        await list_sessions(message)
        return

    if args[1] == "remove":
        sessions.pop(int(args[2]))
        await message.channel.send("```diff\n+successfully removed session 0 "
                                   f"{int(args[2])}```")
        return

    if args[1] == "print":
        await message.channel.send(str(sessions[session_id]))
        return


@client.event
async def on_ready():
    print(f"[Connected]: ({client.user})")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content == "ttt":
        await usage(message)
        return

    args = message.content.split()

    if args[0] == "ttt":
        print(f"[New Connection] {message.author}")
        await ttt(message, args)


client.run(token)
