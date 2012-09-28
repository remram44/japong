import logging
import os

from japong.server import FileResponse, WebsocketResponse


FILE_ALIASES = {
        '': 'index.html'}
STATIC_FILES = {
        'index.html': 'text/html',
        'favicon.ico': 'image/x-icon'}
TEMPLATE_FILES = set()


class PongGame(object):
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
            return PongWebsocketResponse(http)
        logging.info("no match for request %s" % request)
        return None


class PongWebsocketResponse(WebsocketResponse):
    def __init__(self, request):
        WebsocketResponse.__init__(self, request)

    def msgReceived(self, msg):
        if msg.is_text:
            logging.debug("A client sent text %r" % str(msg.data))
        else:
            logging.debug("A client sent binary %r" %
                          str(msg.data).encode('hex'))

        # Just send it back
        self.websocket.send(msg)

    def connectionLost(self):
        pass
