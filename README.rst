Python
======

This is in dev currently.

Once it is released you'll be able to do the following::

    $ pip install zenircbot_api

And you'll be able to use it like so::

    from zenircbot_api import ZenIRCBot


    client = ZenIRCBot(hostname='redis.server.location', port=6379)
    client.send_privmsg(to='#channel', message='ohai')

Docs are availabe at: http://zenircbot.rtfd.org/
