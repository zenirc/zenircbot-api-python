"""ZenIRCBot API"""
# These are at the top to ensure gevent can monkey patch before
# threading gets imported.
from gevent import monkey
monkey.patch_all()

import atexit
import json
import gevent
from redis import StrictRedis


__version__ = '2.2.7'


def load_config(name):
    """ Loads a JSON file and returns an object.

    :param string name: The JSON file to load.
    :returns: An native object with the contents of the JSON file.

    This is a helper so you don't have to do the file IO and JSON
    parsing yourself.
    """
    with open(name) as f:
        return json.loads(f.read())


class ZenIRCBot(object):
    """Instantiates a new ZenIRCBot API object.

    :param string host: Redis hostname (default: 'localhost')
    :param integer port: Redis port (default: 6379)
    :param integer db: Redis DB number (default: 0)
    :param string name: Name for the service using this instance
    :returns: ZenIRCBot instance

    Takes Redis server parameters to use for instantiating Redis
    clients.

    """

    def __init__(self, host='localhost', port=6379, db=0, name="bot"):
        self.host = host
        self.port = port
        self.db = db
        self.service_name = name
        self.redis = StrictRedis(host=self.host,
                                 port=self.port,
                                 db=self.db)
        self.commands = []  # list of command callbacks

    def send_privmsg(self, to, message):
        """Sends a message to the specified channel(s)

        :param to: A list or a string, if it is a list it will send to
                   all the people or channels listed.
        :param string message: The message to send.

        This is a helper so you don't have to handle the JSON or the
        envelope yourself.

        """
        if isinstance(to, basestring):
            to = (to,)
        for channel in to:
            self.get_redis_client().publish('out',
                                            json.dumps({
                                                'version': 1,
                                                'type': 'privmsg',
                                                'data': {
                                                    'to': channel,
                                                    'message': message,
                                                }}))

    def send_action(self, to, message):
        """Sends an "ACTION" message to the specified channel(s)

        :param to: A list or a string, if it is a list it will send to
                   all the people or channels listed.
        :param string message: The message to send.

        This is a helper so you don't have to handle the JSON or the
        envelope yourself.

        """
        if isinstance(to, basestring):
            to = (to,)
        for channel in to:
            self.get_redis_client().publish('out',
                                            json.dumps({
                                                'version': 1,
                                                'type': 'privmsg_action',
                                                'data': {
                                                    'to': channel,
                                                    'message': message,
                                                }}))

    def send_admin_message(self, message):
        """
        :param string message: The message to send.

        This is a helper function that sends the message to all of the
        channels defined in ``admin_spew_channels``.

        """
        admin_channels = self.redis.get('zenircbot:admin_spew_channels')
        if admin_channels:
            self.send_privmsg(admin_channels, message)

    def non_blocking_redis_subscribe(self, func, args=[], kwargs={}):
        pubsub = self.get_redis_client().pubsub()
        pubsub.subscribe('in')
        for msg in pubsub.listen():
            if msg['type'] == 'message':
                message = json.loads(msg['data'])
                func(message=message, *args, **kwargs)

    def register_commands(self, service, commands):
        """
        :param string script: The script with extension that you are
                              registering.

        :param list commands: A list of objects with name and description
                              attributes used to reply to
                              a commands query.

        This will notify all ``admin_spew_channels`` of the script
        coming online when the script registers itself. It will also
        setup a subscription to the 'out' channel that listens for
        'commands' to be sent to the bot and responds with the list of
        script, command name, and command description for all
        registered scripts.

        """
        self.send_admin_message(service + ' online!')
        if commands:
            def registration_reply(message, service, commands):
                if message['version'] == 1:
                    if message['type'] == 'directed_privmsg':
                        if message['data']['message'] == 'commands':
                            for command in commands:
                                self.send_privmsg(message['data']['sender'],
                                                  '%s: %s - %s' % (
                                                      service,
                                                      command['name'],
                                                      command['description']
                                                  ))
                        elif message['data']['message'] == 'services':
                            self.send_privmsg(message['data']['sender'],
                                              service)
            greenlet = gevent.spawn(self.non_blocking_redis_subscribe,
                                    func=registration_reply,
                                    kwargs={
                                        'service': service,
                                        'commands': commands
                                    })
            # Ensures that the greenlet is cleaned up.
            atexit.register(lambda gl: gl.kill(), greenlet)

    def get_redis_client(self):
        """ Get redis client using values from instantiation time."""
        return StrictRedis(host=self.host,
                           port=self.port,
                           db=self.db)

    def simple_command(self, commandstr, desc="a command", **options):
        """ A decorator to register a command as a callback when the command
        is triggered. The unction must take one argument, which is the message
        text.

            @zen.simple_command("ping"):
            def ping(msg):
                return "pong"

        :param string commandstr: string to use as a command
        :param string desc: optional description text
        :returns: decorated function

        This should be used in conjuction with ZenIRCBot.listen() which will
        finish the registration process and starts listening to redis for
        messages
        """

        # make decorator, f is the wrapped function passed through **options
        def decorator(f):
            self.commands.append({'str': commandstr,
                                  'desc': desc,
                                  'name': f.__name__,
                                  'callback': f,
                                })
        return decorator


    def listen(self):
        """ Start listening. This is blocking and should be the last line in a
        service. Once this is called the service is running.
        """

        # actually register commands
        self.register_commands(self.service_name,
            [{'name': '!'+c['str'], 'description': c['desc']} for c in self.commands]
        )

        # boilerplate pubsub listening
        subscription = self.get_redis_client().pubsub()
        subscription.subscribe('in')
        for msg in subscription.listen():
            if msg.get('type') == 'message':
                message = json.loads(msg['data'])
                if message['version'] == 1:
                    if message['type'] == 'directed_privmsg':
                        text = message['data']['message']

                        # Look for any command matches in registered commands
                        for command in self.commands:

                            # match command
                            if text.startswith(command['str']):

                                # do callback and send returned value to channel
                                self.send_privmsg(message['data']['channel'],
                                    command['callback'](text))
