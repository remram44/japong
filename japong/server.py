import logging

from twisted.internet import protocol

from japong.http import Http, HttpError
from japong.websocket import setup_websocket


class HttpProto(protocol.Protocol):
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
            import sys, traceback
            traceback.print_exc(sys.stderr)
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
                        response.template.render(**response.vars),
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
        self.msgReceived(self.websocket.dataReceived(data))

    def connectionLost(self):
        pass


class HttpFactory(protocol.Factory):
    def __init__(self, host, handler):
        self.host = host
        self.handler = handler

    def buildProtocol(self, addr):
        return HttpProto(self, self.host)

    def get_response(self, http):
        return self.handler.get_response(http)
