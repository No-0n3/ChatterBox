# -*- coding: utf-8 -*-

from twisted.words.protocols import irc
from twisted.internet import protocol, threads
from cobe.brain import Brain


class Bot(irc.IRCClient):
    """ChatBot class"""

    nickname = ""
    password = ""
    username = ""
    realname = ""
    learn = True
    brain = None

    def connectionMade(self):
        """Is run when the connection is successful."""
        irc.IRCClient.connectionMade(self)

    def connectionLost(self, reason):
        """Is run if the connection is lost."""
        irc.IRCClient.connectionLost(self, reason)

    # callbacks for events
    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        self.join(self.factory.channel)
        self.brain = Brain("brain.db")

    def kickedFrom(self, channel, kicker, message):
        """Called when I am kicked from a channel."""
        self.join(self.factory.channel)

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        self.notice("", "I joined {}".format(channel))

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        user = user.split('!', 1)[0]

        if msg.startswith("@"):
            cmd = msg.split()[0].strip("@")
            args = msg.split()[1:] or [None, ]

            func = getattr(self, 'cmd_' + cmd, None)

            if func is not None:
                threads.deferToThread(func, user, *args)
            else:
                self.notice("", "Unknown command!")
        else:
            if self.brain:
                if self.learn:
                    self.brain.learn(msg)

                if channel == self.nickname:
                    self.msg(user, self.brain.reply(msg).encode('utf8'))

    # User-defined commands
    def cmd_join(self, user, channel, password=None):
        """Join a channel. @join <channel> [<password>]"""
        self.join(channel, password)

    def cmd_part(self, user, channel, password=None):
        """Leave a channel. @part <channel>"""
        self.part(channel)

    def irc_ERR_BADCHANNELKEY(self, prefix, params):
        """Send a notice to a user when an incorrect channel key is used."""
        self.notice("", "Bad key: {} ({})".format(params[2], params[1]))

    def cmd_help(self, user, cmd=None):
        """Lists help about commands. @help [<cmd>]"""
        if cmd is None:
            self.notice(user, "Commands:")

            for func in dir(self):
                if func.startswith("cmd_"):
                    self.notice(user, "@" + func[4:] + " - " +
                                getattr(self, func).__doc__)
        else:
            func = getattr(self, "cmd_" + cmd)
            self.notice(user, "@" + func.__name__[4:] + " - " + func.__doc__)

    def cmd_learn(self, user, *args):
        """Toggle learning on/off"""
        self.learn = not self.learn
        self.notice("", "Learn: %s" % self.learn)


class BotFactory(protocol.ReconnectingClientFactory):
    """A factory for Bots.

    A new protocol instance will be created each time we connect to the server.
    """

    def __init__(self, channel):
        """Init"""
        self.channel = channel

    def buildProtocol(self, addr):
        """Build protocol object"""
        p = Bot()
        p.factory = self

        return p

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        protocol.ReconnectingClientFactory.clientConnectionLost(self,
            connector, reason)

    def clientConnectionFailed(self, connector, reason):
        """Is run if the connection fails."""
        protocol.ReconnectingClientFactory.clientConnectionLost(self,
            connector, reason)
