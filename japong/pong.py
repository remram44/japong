import logging
import os

from jinja2 import Environment, PackageLoader

from japong.server import FileResponse, TemplateResponse, WebsocketResponse


FILE_ALIASES = {
        '': 'index.html'}
STATIC_FILES = {
        'style.css': 'text/css',
        'pong.js': 'text/javascript',
        'favicon.ico': 'image/x-icon'}
TEMPLATE_FILES = set(['index.html'])


class PongGame(object):
    def __init__(self):
        self.tpl_env = Environment(loader=PackageLoader('japong', 'site'))

    def get_response(self, http):
        request = http.request_uri[1:]
        request = FILE_ALIASES.get(request, request)
        if request in STATIC_FILES:
            logging.info("static file %s requested" % request)
            return FileResponse(
                    file=open(os.path.join('japong', 'site', request)),
                    mime=STATIC_FILES[request])
        elif request in TEMPLATE_FILES:
            logging.info("template file %s requested" % request)
            return TemplateResponse(
                    template=self.tpl_env.get_template(request),
                    vars=dict(scripts=['/pong.js']))
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
