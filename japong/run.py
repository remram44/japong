import logging
from optparse import OptionParser
from twisted.internet import reactor

from japong.server import HttpFactory
from japong.pong import PongGame


def main():
    optparser = OptionParser()
    optparser.add_option(
            '-q', '--quiet',
            action='store_const', dest='verbosity', const=0,
            help="don't output anything to stderr")
    optparser.add_option(
            '-v', '--verbose',
            action='count', dest='verbosity',
            help="increase program verbosity")
    optparser.add_option(
            '-l', '--hostname',
            action='store', dest='hostname',
            help="hostname (or location) of this server")
    optparser.add_option(
            '-i', '--interface',
            action='store', dest='interface',
            help="interface (IP address) to bind to")
    optparser.add_option(
            '-p', '--port',
            action='store', dest='port', type='int',
            help="port number on which to listen")
    optparser.set_defaults(verbosity=1, hostname=None, interface='',
                           port=8000)
    (options, args) = optparser.parse_args()
    options = vars(options) # options is not a dict!?

    run(**options)


def run(port, hostname, interface, verbosity):
    if verbosity == 0: # -q
        level = logging.CRITICAL
    elif verbosity == 1: # default
        level = logging.WARNING
    elif verbosity == 2: # -v
        level = logging.INFO
    else: # -v -v
        level = logging.DEBUG
    logging.basicConfig(level=level)

    if hostname:
        if not hostname.startswith('http://'):
            hostname = 'http://%s' % (hostname,)
        sep = hostname.find('/')
        if sep != -1:
            hostname = hostname[:sep]
        if port != 80 and not ':' in hostname:
            hostname = "http://%s:%d/" % (hostname, port)
        else:
            hostname = "http://%s/" % hostname
        logging.info('Hostname set to %s' % hostname)

    pong = PongGame()

    reactor.listenTCP(port, HttpFactory(hostname, pong), interface=interface)
    reactor.run()
