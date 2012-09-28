import logging
import os

from twisted.internet import protocol, reactor

from japong.http import Http, HttpError
from japong.websocket import setup_websocket


class PongProto(protocol.Protocol):
    def __init__(self, factory, host):
        self.factory = factory
        self.http = Http(host)
        self.ws = None

    def dataReceived(self, data):
        # Parse HTTP request
        if not self.http.headers_recvd:
            try:
                if self.http.received(data, self.transport.write):
                    self.process_request()
            except HttpError:
                self.transport.loseConnection()
        # Websocket stuff
        elif self.ws is not None:
            self.ws.dataReceived(data)
        # An HTTP connection should be closed by now -- could be a non-GET
        # HTTP query sending data before the connection is effectively closed?
        else:
            logging.error("Receiving data on unknown client; request was %r" %
                          self.http)

    def process_request(self):
        logging.debug("%s %s" % (self.http.method, self.http.request_uri))

        if self.http.method != 'GET':
            self.http.send_error(status=400, sender=self.transport.write)

        try:
            response = self.factory.get_response(self.http)
        except:
            self.http.send_error(status=500, sender=self.transport.write)
        else:
            if response is None:
                self.http.send_error(status=404, sender=self.transport.write)
                self.transport.loseConnection()
            elif isinstance(response, FileResponse):
                self.http.send_file(
                        file=response.file,
                        mime=response.mime,
                        sender=self.transport.write)
                response.file.close()
                self.transport.loseConnection()
            elif isinstance(response, TemplateResponse):
                self.http.send_page(
                        reponse.template % response.vars,
                        mime=response.mime,
                        sender=self.transport.write)
                self.transport.loseConnection()
            elif isinstance(response, WebsocketResponse):
                response.init(self.transport)
                self.ws = response
                # don't close the connection ;-)

    def connectionLost(self, reason):
        if self.ws is not None:
            self.ws.connectionLost()


class Response(object):
    def __init__(self, mime='text/plain'):
        self.mime = mime


class FileResponse(Response):
    def __init__(self, file, mime='text/plain'):
        Response.__init__(self, mime)
        self.file = file


class TemplateResponse(Response):
    def __init__(self, template, vars={}, mime='text/html'):
        Response.__init__(self, mime)
        self.template = template
        self.vars = vars


class WebsocketResponse(Response):
    def __init__(self, request):
        self.websocket = setup_websocket(request)

    def init(self, transport):
        def sender(data):
            transport.write(str(data))
        self.websocket.init(sender)

    def dataReceived(self, data):
        msg = self.websocket.dataReceived(data)

        if msg.is_text:
            logging.debug("A client sent text %r" % str(msg.data))
        else:
            logging.debug("A client sent binary %r" %
                          str(msg.data).encode('hex'))

        # Just send it back
        self.websocket.send(msg)

    def connectionLost(self):
        pass


FILE_ALIASES = {
        '': 'index.html'}
STATIC_FILES = {
        'index.html': 'text/html',
        'favicon.ico': 'image/x-icon'}
TEMPLATE_FILES = set()


class PongFactory(protocol.Factory):
    def __init__(self, host):
        self.host = host

    def buildProtocol(self, addr):
        return PongProto(self, self.host)

    def get_response(self, http):
        request = http.request_uri[1:]
        request = FILE_ALIASES.get(request, request)
        if request in STATIC_FILES:
            logging.info("static file %s requested" % request)
            return FileResponse(
                    file=open(os.path.join('japong', 'site', request)),
                    mime=STATIC_FILES[request])
        elif request == 'conn':
            logging.info("'conn' requested! initiating websocket")
            return WebsocketResponse(http)
        logging.info("no match for request %s" % request)
        return None


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

    reactor.listenTCP(port, PongFactory(host))
    reactor.run()
