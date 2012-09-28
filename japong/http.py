class LineTooLong(ValueError):
    pass


class LineReader(object):
    def __init__(self, data=''):
        self._buf = data

    def read_line(self, data='', max=4096):
        p = self._buf.find('\n')
        if p >= 0:
            l = self._buf[:p]
            self._buf = self._buf[p+1:] + data
            if l and l[-1] == '\r':
                l = l[:-1]
            return l

        p = data.find('\n')
        if p >= 0:
            l = self._buf + data[:p]
            self._buf = data[p+1:]
            if l and l[-1] == '\r':
                l = l[:-1]
            return l

        self._buf += data
        if len(self._buf) > max:
            raise LineTooLong

        return None


class HttpError(Exception):
    pass


_HTTP_METHODS = set(['GET', 'HEAD', 'POST',
                     'CONNECT', 'PUT', 'DELETE',
                     'OPTIONS', 'TRACE'])

_HTTP_STATUSES = {
        100: 'Continue',
        101: 'Switching Protocols',
        200: 'Ok',
        301: 'Moved Permanently',
        302: 'Found',
        303: 'See Other',
        304: 'Not Modified',
        400: 'Bad Request',
        401: 'Unauthorized',
        403: 'Forbidden',
        404: 'Not Found',
        414: 'Request-URI Too Long',
        500: 'Internal Server Error',
        501: 'Not Implemented',
        503: 'Service Unavailable'}


class Http(object):
    def __init__(self, host):
        self.hostname = host
        self._buffer = LineReader()

        self.headers_recvd = False
        self.headers = dict()
        self.method = None
        self.request_uri = None

    def received(self, data, sender=None):
        try:
            line = self._buffer.read_line(data)
            while line is not None:
                if line == '':
                    # The LineHeader's buffer might contain more data
                    # This doesn't apply to GET though
                    if self.request_uri and self.headers.get('Host'):
                        self.headers_recvd = True
                        return True
                    else:
                        raise HttpError("Unexpected end of headers")

                # Read request
                if self.request_uri is None:
                    parts = line.split(' ')
                    if len(parts) != 3:
                        raise HttpError("Invalid first line")
                    if parts[0] not in _HTTP_METHODS:
                        raise HttpError("Unknown method")
                    self.method = parts[0]
                    self.request_uri = parts[1]
                    self.version = parts[2]
                    if not self.version.startswith('HTTP/'):
                        raise HttpError("Supplied protocol version is "
                                               "not HTTP")
                # Read headers
                else:
                    name, value = line.split(': ', 1)
                    if name in self.headers:
                        raise HttpError("A header has been supplied "
                                               "twice")
                    self.headers[name] = value

                line = self._buffer.read_line()

            return False
        except LineTooLong:
            if sender:
                send_error(sender, status=414)
            raise
        except HttpError:
            if sender:
                send_error(sender, status=400)
            raise

    def send_error(self, sender, status=500):
        descr = _HTTP_STATUSES.get(status)
        if descr:
            error = "%d %s" % (status, descr)
        else:
            error = "Error %d" % status
        content = (
                "<html>\n"
                "<head><title>{error}</title></head>\n"
                "<body bgcolor=\"white\">\n"
                "<center><h1>{error}</h1></center>\n"
                "<hr><center>nginx/1.2.1</center>\n"
                "</body>\n"
                "</html>\n").format(error=error)
        self.send_page(content, sender, status)

    def _send_headers(self, sender, status, mime):
        descr = _HTTP_STATUSES.get(status)
        if descr:
            descr = ' ' + descr
        sender("HTTP/1.1 %d%s\r\n" % (status, descr))
        host = self.hostname or self.headers.get('Host', 'localhost')
        sender("Host: %s\r\n" % host)
        sender("Content-type: %s\r\n" % mime)
        sender("Connection: close\r\n")
        sender("\r\n")
        
    def send_page(self, page, sender, status=200, mime='text/html'):
        self._send_headers(sender, status, mime)
        if isinstance(page, unicode):
            page = page.encode('utf-8')
        sender(page)

    def send_file(self, file, sender, status=200, mime='text/html'):
        self._send_headers(sender, status, mime)
        buf = file.read(4096)
        while buf:
            sender(buf)
            buf = file.read(4096)

    def __repr__(self):
        return "Http(method=%r, uri=%r, headers_recvd=%r)" % (
               self.method, self.request_uri, self.headers_recvd)
