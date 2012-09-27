from optparse import OptionParser

from japong.server import run


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
