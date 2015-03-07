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
        self.nickname = self.factory.config.get("irc", "nick")
        self.password = self.factory.config.get("irc", "pw")
        self.username = self.factory.config.get("irc", "user")
        self.realname = self.factory.config.get("irc", "real")

        irc.IRCClient.connectionMade(self)

    def connectionLost(self, reason):
        """Is run if the connection is lost."""
        irc.IRCClient.connectionLost(self, reason)

    # callbacks for events
    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        channels = self.factory.config.get("irc", "channels").split(",")

        for channel in channels:
            self.join(channel)

        self.brain = Brain("brain.db")

    def kickedFrom(self, channel, kicker, message):
        """Called when I am kicked from a channel."""
        self.join(channel)

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        self.notice(self.factory.config.get("bot", "owner_nick"),
            "I joined {}".format(channel))

    def noticed(self, user, channel, msg):
        """Called when a notice is recieved."""
        self.notice(self.factory.config.get("bot", "owner_nick"),
            "From %s/%s: %s" % (user, channel, msg))

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""

        if msg.startswith("@") and \
            self.factory.config.get("bot", "owner_mask") in user:
            cmd = msg.split()[0].strip("@")
            args = msg.split()[1:] or [None, ]

            func = getattr(self, 'cmd_' + cmd, None)

            if func is not None:
                threads.deferToThread(func, user.split('!', 1)[0],
                    channel, *args)
            else:
                self.notice(user.split('!', 1)[0], "Unknown command!")
        else:
            if self.brain:
                if self.learn:
                    self.brain.learn(msg)

                if channel == self.nickname:
                    self.msg(user.split('!', 1)[0],
                    self.brain.reply(msg).encode('utf8'))

    # User-defined commands
    def cmd_join(self, user, src_chan, channel, password=None):
        """Join a channel. @join <channel> [<password>]"""
        if channel:
            self.join(channel, password)

    def cmd_part(self, user, src_chan, channel, password=None):
        """Leave a channel. @part <channel>"""
        if channel:
            self.part(channel)

    def cmd_help(self, user, src_chan, cmd=None):
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

    def cmd_learn(self, user, src_chan, *args):
        """Toggle learning on/off"""
        self.learn = not self.learn
        self.notice(self.factory.config.get("bot", "owner_nick"),
            "Learn: %s" % self.learn)

    def cmd_quit(self, user, src_chan, *args):
        """Shutdown the bot."""
        self.quit(message="Shutting down.")

    def cmd_sc(self, user, src_chan, *args):
        """Save channel to channel-list."""
        channels = self.factory.config.get("irc", "channels").split(",")

        if args:
            for c in args:
                channels.append(c)
        else:
            channels.append(src_chan)

        new = ""

        for channel in channels:
            new += "%s," % channel

        new = new[:-1]
        self.factory.config.set("irc", "channels", new)

        with open("chatterbox.ini", "wb") as f:
            self.factory.config.write(f)

        self.notice(self.factory.config.get("bot", "owner_nick"),
            "Added channel/s to list.")

    def cmd_lc(self, user, src_chan, *args):
        """List channels."""
        channels = self.factory.config.get("irc", "channels")
        self.notice(self.factory.config.get("bot", "owner_nick"), channels)

    def cmd_msg(self, user, src_chan, dest, message):
        """Tell the bot to send a message. @msg <user> <message>"""
        if dest and message:
            self.msg(dest, message)


class BotFactory(protocol.ReconnectingClientFactory):
    """A factory for Bots.

    A new protocol instance will be created each time we connect to the server.
    """

    def __init__(self, config):
        """Init"""
        self.config = config

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
