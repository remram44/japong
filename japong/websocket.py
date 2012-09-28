from base64 import b64encode
from hashlib import sha1
import types

from ws4py import WS_KEY, WS_VERSION
from ws4py.messaging import Message
from ws4py.streaming import Stream


class MalformedWebSocket(ValueError):
    pass


def setup_websocket(request):
    if 'Upgrade' not in request.headers.get('Connection', '') or \
            request.headers.get('Upgrade', '').lower() != 'websocket':
        raise MalformedWebSocket

    version = request.headers.get('Sec-WebSocket-Version')
    version_is_valid = False
    if version:
        try:
            version = int(version)
        except:
            pass
        else:
            version_is_valid = version in WS_VERSION

    if not version_is_valid:
        raise MalformedWebSocket

    # Compute the challenge response
    key = request.headers['Sec-WebSocket-Key']
    handshake_response = b64encode(sha1(key + WS_KEY).digest())

    protocols = request.headers.get('Sec-WebSocket-Protocol')

    handshake_reply = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n")
    handshake_reply += "Sec-WebSocket-Version: %s\r\n" % version
    if protocols:
        handshake_reply += "Sec-WebSocket-Protocol: %s\r\n" % protocols
    handshake_reply += "Sec-WebSocket-Accept: %s\r\n" % handshake_response
    handshake_reply += "\r\n"

    return WebSocket(
        handshake_reply,
        protocols)


DEFAULT_READING_SIZE = 2

# This class was adapted from ws4py.websocket:WebSocket
class WebSocket(object):
    def __init__(self, handshake_reply, protocols=None):
        self.stream = Stream(always_mask=False)
        self.handshake_reply = handshake_reply
        self.handshake_sent = False
        self.protocols = protocols
        self.client_terminated = False
        self.server_terminated = False
        self.reading_buffer_size = DEFAULT_READING_SIZE

    def init(self, sender):
        # This was initially a loop that used callbacks in ws4py
        # Here it was turned into a generator, the callback replaced by yield
        self.sender = sender

        self.sender(self.handshake_reply)
        self.handshake_sent = True

    def send(self, payload, binary=False):
        """
        Sends the given ``payload`` out.

        If ``payload`` is some bytes or a bytearray,
        then it is sent as a single message not fragmented.

        If ``payload`` is a generator, each chunk is sent as part of
        fragmented message.

        If ``binary`` is set, handles the payload as a binary message.
        """
        message_sender = self.stream.binary_message if binary else self.stream.text_message

        if isinstance(payload, basestring) or isinstance(payload, bytearray):
            self.sender(message_sender(payload).single(mask=self.stream.always_mask))

        elif isinstance(payload, Message):
            self.sender(payload.single(mask=self.stream.always_mask))

        elif type(payload) == types.GeneratorType:
            bytes = payload.next()
            first = True
            for chunk in payload:
                self.sender(message_sender(bytes).fragment(first=first, mask=self.stream.always_mask))
                bytes = chunk
                first = False

            self.sender(message_sender(bytes).fragment(last=True, mask=self.stream.always_mask))

        else:
            raise ValueError("Unsupported type '%s' passed to send()" % type(payload))

    def dataReceived(self, data):
        """
        Performs the operation of reading from the underlying
        connection in order to feed the stream of bytes.

        We start with a small size of two bytes to be read
        from the connection so that we can quickly parse an
        incoming frame header. Then the stream indicates
        whatever size must be read from the connection since
        it knows the frame payload length.

        Note that we perform some automatic operations:

        * On a closing message, we respond with a closing
          message and finally close the connection
        * We respond to pings with pong messages.
        * Whenever an error is raised by the stream parsing,
          we initiate the closing of the connection with the
          appropiate error code.
        """
        s = self.stream
        
        self.reading_buffer_size = s.parser.send(data) or DEFAULT_READING_SIZE

        if s.closing is not None:
            if not self.server_terminated:
                self.close(s.closing.code, s.closing.reason)
            else:
                self.client_terminated = True
            return None

        if s.errors:
            for error in s.errors:
                self.close(error.code, error.reason)
            s.errors = []
            return None

        if s.has_message:
            msg = s.message
            return msg
            s.message = None
        else:
            if s.pings:
                for ping in s.pings:
                    self.sender(s.pong(ping.data))
                s.pings = []

            if s.pongs:
                s.pongs = []
        return None

    def close(self, code=1000, reason=''):
        """
        Call this method to initiate the websocket connection
        closing by sending a close frame to the connected peer.
        The ``code`` is the status code representing the
        termination's reason.

        Once this method is called, the ``server_terminated``
        attribute is set. Calling this method several times is
        safe as the closing frame will be sent only the first
        time.

        .. seealso:: Defined Status Codes http://tools.ietf.org/html/rfc6455#section-7.4.1
        """
        if not self.server_terminated:
            self.server_terminated = True
            self.sender(self.stream.close(code=code, reason=reason).single(mask=self.stream.always_mask))

    @property
    def terminated(self):
        """
        Returns ``True`` if both the client and server have been
        marked as terminated.
        """
        return self.client_terminated is True and self.server_terminated is True

    def __iter__(self):
        return self.runner
