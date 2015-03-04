#!/usr/bin/env python
# -*- coding: utf-8 -*-

import chatterbox
from twisted.application import internet, service

application = service.Application('ChatterBox')
factory = chatterbox.BotFactory("")
connection = internet.TCPClient('', 6667, factory)
connection.setServiceParent(service.IServiceCollection(application))
