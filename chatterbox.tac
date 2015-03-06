#!/usr/bin/env python
# -*- coding: utf-8 -*-

import chatterbox
from twisted.application import internet, service
from ConfigParser import SafeConfigParser

config = SafeConfigParser(allow_no_value=True)
config.read("chatterbox.ini")

application = service.Application('ChatBot')
factory = chatterbox.BotFactory(config)
connection = internet.TCPClient(config.get("irc", "host"),
    config.getint("irc", "port"), factory)
connection.setServiceParent(service.IServiceCollection(application))
