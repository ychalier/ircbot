#!/usr/bin/python3

"""Module for an IRC bot that will keep some channels alive"""
import sys
import json
import codecs
import random
import logging
from collections import namedtuple
from ssl import wrap_socket as ssl_wrap_socket
from blinker import signal
import irc.bot


class Signals:
    """Stores multiple IRC signals"""
    irc_channel_joined = signal("irc-channel-joined")
    shutdown_requested = signal("shutdown-requested")


class Channel(namedtuple("Channel", "name password")):
    """An IRC channel with optional password."""

    def __new__(cls, name, password=None):
        return super(Channel, cls).__new__(cls, name, password)


class Bot(irc.bot.SingleServerIRCBot):
    """An IRC bot general interface."""

    version = "PyBotv0.1"

    def __init__(self, server_spec, nickname, realname, channels, ssl=False,
                 shutdown_predicate=None):
        logging.info(
            "Connecting to IRC server %s:%d",
            server_spec.host,
            server_spec.port
        )
        connect_params = {}
        if ssl:
            ssl_factory = irc.connection.Factory(wrapper=ssl_wrap_socket)
            connect_params["connect_factory"] = ssl_factory
        irc.bot.SingleServerIRCBot.__init__(
            self,
            [server_spec],
            nickname,
            realname,
            **connect_params
        )
        # Note: `self.channels` already exists in super class.
        self.channels_to_join = channels
        self.shutdown_predicate = shutdown_predicate

    def _handle_message(self, event, public):
        raise NotImplementedError

    def on_pubmsg(self, _, event):
        """React to message being published by a user"""
        self._handle_message(event, True)

    def get_version(self):
        """Return this on CTCP VERSION requests."""
        return self.version

    def on_welcome(self, conn, _):
        """Join channels after connect."""
        logging.info("Connected to %s.", conn.socket.getpeername())
        channel_names = sorted(c.name for c in self.channels_to_join)
        logging.info("Channels to join: %s", ", ".join(channel_names))
        for channel in self.channels_to_join:
            conn.join(channel.name, channel.password or "")

    def on_nicknameinuse(self, conn, _):
        """Choose another nickname if conflicting."""
        self._nickname += "_"
        conn.nick(self._nickname)

    def on_join(self, _, event):
        """Successfully joined channel."""
        joined_nick = event.source.nick
        channel_name = event.target
        if joined_nick == self._nickname:
            logging.info("Joined IRC channel: %s", channel_name)
            Signals.irc_channel_joined.send(channel=channel_name)

    def on_badchannelkey(self, _, event):
        """Channel could not be joined due to wrong password."""
        channel_name = event.arguments[0]
        logging.info("Cannot join channel %s (bad key).", channel_name)

    def on_privmsg(self, _, event):
        """React on private messages."""
        self._handle_message(event, False)

    def shutdown(self, nickmask):
        """Shut the bot down."""
        logging.info("Shutdown requested by %s.", nickmask)
        Signals.shutdown_requested.send()
        self.die("Shutting down.")  # Joins IRC bot thread.

    def say(self, channel, message):
        """Say message on channel."""
        self.connection.privmsg(channel, message)


class PyBot(Bot):
    """High level bot class"""

    def __init__(self, configuration, commands):
        server_spec = irc.bot.ServerSpec(
            configuration["host"],
            configuration["port"],
            configuration["password"]
        )
        Bot.__init__(
            self,
            server_spec,
            configuration["nickname"],
            configuration["realname"],
            [Channel(name) for name in configuration["channels"]]
        )
        self.commands = commands

    def _handle_message(self, event, public):
        if event.arguments[0].startswith("!"):
            command = event.arguments[0].split(" ")[0]
            if command == "!help":
                for command in sorted(self.commands.values(), key=lambda x: x.name):
                    self.say(event.target, "%s: %s" %
                             (command.name, command.help))
            elif command in self.commands:
                output = self.commands[command].execute(event)
                if output is not None:
                    self.say(event.target, str(output))


class ChatCommand:
    """Wrapper for a chat command"""

    def __init__(self, name, helptext):
        self.name = name
        self.help = helptext

    def execute(self, event):
        """Respond to command call"""
        raise NotImplementedError


class HelloCommand(ChatCommand):
    """Prints a welcoming message"""

    def __init__(self):
        ChatCommand.__init__(self, "!hello", "Prints a welcoming message")

    def execute(self, event):
        return "Hello %s!" % event.source.nick


class InfoCommand(ChatCommand):
    """Prints bot information"""

    def __init__(self):
        ChatCommand.__init__(self, "!info", "Prints bot information")

    def execute(self, event):
        return "I am a bot! Check out my code at https://github.com/ychalier/ircbot."


class GuessNumberCommand(ChatCommand):
    """More or less game"""

    def __init__(self):
        ChatCommand.__init__(self, "!guess", "Play a \"more or less\" game")
        self._init_game()

    def _init_game(self):
        self.target = random.randint(1, 100)
        self.steps = 0

    def execute(self, event):
        try:
            guess = int(event.arguments[0].split(" ")[1])
            self.steps += 1
            if guess < self.target:
                return "It is more!"
            if guess > self.target:
                return "It is less!"
            message = "%s guessed the correct answer! (it took %d guesses)" % (
                event.source.nick,
                self.steps
            )
            self._init_game()
            return message
        except (ValueError, IndexError):
            return "Syntax is: \"!guess <number>\""


def main():
    """Main function"""
    configuration_file = "config.json"
    if "-c" in sys.argv:
        configuration_file = sys.argv[-1]
    logging.warning("Loading configuration from %s", configuration_file)
    with codecs.open(configuration_file, "r", "utf8") as file:
        configuration = json.load(file)
    commands = [
        HelloCommand(),
        InfoCommand(),
        GuessNumberCommand(),
    ]
    PyBot(configuration, {cmd.name: cmd for cmd in commands}).start()


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s\t%(levelname)s\t%(message)s",
        level=logging.INFO
    )
    main()
