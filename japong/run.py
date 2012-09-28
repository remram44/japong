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
            '-n', '--hostname',
            action='store', dest='host',
            help="hostname (or location) of this server")
    optparser.add_option(
            '-p', '--port',
            action='store', dest='port',
            help="port number on which to listen")
    optparser.set_defaults(verbosity=1, host=None, port=8000)
    (options, args) = optparser.parse_args()
    options = vars(options) # options is not a dict!?

    run(**options)


def run(port, host, verbosity):
    if verbosity == 0: # -q
        level = logging.CRITICAL
    elif verbosity == 1: # default
        level = logging.WARNING
    elif verbosity == 2: # -v
        level = logging.INFO
    else: # -v -v
        level = logging.DEBUG
    logging.basicConfig(level=level)

    if not host:
        host = "http://127.0.0.1"
    if port != 80 and not ':' in host:
        host += ":%d" % port

    pong = PongGame()

    reactor.listenTCP(port, HttpFactory(host, pong))
    reactor.run()
