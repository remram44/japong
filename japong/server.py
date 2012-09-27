from twisted.internet import protocol, reactor

from japong.http import Http, HttpError


class PongProto(protocol.Protocol):
    def __init__(self, host):
        self.http = Http(host)

    def dataReceived(self, data):
        try:
            # Parse HTTP request
            if not self.http.header_recvd:
                if not self.http.received(data, self.transport.write):
                    return

            print self.http.method, self.http.request_uri
            print self.http.headers

            if self.http.method != 'GET':
                self.http.send_error(status=400, sender=self.transport.write)

            if self.http.request_uri == '/':
                page = 'TODO : page'
                self.http.send_page(page, status=200, mime='text/plain',
                                    sender=self.transport.write)
                self.transport.loseConnection()
            elif self.http.request_uri == '/conn':
                page = 'TODO : websocket'
                self.http.send_page(page, status=200, mime='text/plain',
                                    sender=self.transport.write)
                self.transport.loseConnection()
            else:
                self.http.send_error(status=404, sender=self.transport.write)
        except HttpError:
            self.transport.loseConnection()

    def connectionLost(self, reason):
        pass


class PongFactory(protocol.Factory):
    def __init__(self, host):
        self.host = host

    def buildProtocol(self, addr):
        return PongProto(self.host)


def run(port, host, verbosity):
    if not host:
        host = "http://127.0.0.1"
    if port != 80 and not ':' in host:
        host += ":%d" % port

    reactor.listenTCP(port, PongFactory(host))
    reactor.run()
