# -*- coding: utf-8 -*-

from twisted.words.protocols import irc
from twisted.internet import threads
from twisted.python import log
from cobe.brain import Brain
import re


class Bot(irc.IRCClient):
    """ChatBot class"""

    nickname = ""
    password = ""
    username = ""
    realname = ""
    learn = False
    brain = None
    private = False
    kickrejoin = False
    joininvite = False

    def connectionMade(self):
        """Is run when the connection is successful."""
        self.nickname = self.factory.nickname
        self.password = self.factory.password
        self.username = self.factory.username
        self.realname = self.factory.realname
        self.lineRate = self.factory.linerate
        self.private = self.factory.private
        self.joininvite = self.factory.joininvite

        irc.IRCClient.connectionMade(self)

    def connectionLost(self, reason):
        """Is run if the connection is lost."""
        irc.IRCClient.connectionLost(self, reason)

    # callbacks for events
    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        self.brain = Brain("cobe.brain")

    def kickedFrom(self, channel, kicker, message):
        """Called when I am kicked from a channel."""
        if self.kickrejoin:
            self.join(channel)

        log.msg("I was kicked from {} by {} because: {}".format(
            channel, kicker, message))

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        log.msg("I joined {}".format(channel))

    def noticed(self, user, channel, msg):
        """Called when a notice is recieved."""
        log.msg("From %s/%s: %s" % (user, channel, msg))

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""

        if msg.startswith(self.factory.prefix):
            if user.split('!', 1)[0] == "No-0n3":
                cmd = msg.split()[0].strip(self.factory.prefix)
                args = msg.split()[1:] or [None, ]

                func = getattr(self, 'cmd_' + cmd, None)

                if func is not None:
                    threads.deferToThread(func, user,
                        channel, *args)
                else:
                    self.notice(user.split('!', 1)[0], "Unknown command!")
        else:
            if self.brain:
                reply = self.brain.reply(msg).encode('utf8')

                if channel == self.nickname:
                    self.msg(user.split('!', 1)[0], reply)
                elif self.nickname.lower() in msg.lower():
                    if self.private:
                        self.msg(user.split('!', 1)[0], reply)
                    else:
                        self.msg(channel, reply)

                if self.learn:
                    nick_exclude = re.compile(re.escape(self.nickname), re.I)
                    self.brain.learn(nick_exclude.sub('', msg))

    def irc_INVITE(self, inviter, params):
        """Action when the bot recevies an invite."""
        log.msg("{} invited {} to {}.".format(inviter, params[0], params[1]))

        if self.joininvite:
            self.join(params[1])

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
        user = user.split('!', 1)[0]

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
        self.notice(user.split('!', 1)[0], "Learn: %s" % self.learn)

    def cmd_quit(self, user, src_chan, *args):
        """Shutdown the bot."""
        self.quit(message="Shutting down.")

    def cmd_msg(self, user, src_chan, dest, *message):
        """Tell the bot to send a message. @msg <user> <message>"""
        if dest and message:
            self.msg(dest, ' '.join(message))

    def cmd_reload(self, user, src_chan, *args):
        """Command to reload brain. @reload"""
        self.brain = Brain("cobe.brain")

    def cmd_kickrejoin(self, user, src_chan, *args):
        """Command to toggle kickrejoin. @kickrejoin"""
        self.kickrejoin = not self.kickrejoin
        self.notice(user.split('!', 1)[0], "Kickrejoin: %s" % self.kickrejoin)

    def cmd_joininvite(self, user, src_chan, *args):
        """Command to toggle joininvite. @joininvite"""
        self.joininvite = not self.joininvite
        self.notice(user.split('!', 1)[0], "Joininvite: %s" % self.joininvite)
