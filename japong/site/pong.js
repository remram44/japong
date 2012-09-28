/*
 * This function is a cross-browser addEventListener function.
 */
window.addEvent = function(event, target, method) {
    if(target.addEventListener) {
        target.addEventListener(event, method, false);
    } else if (target.attachEvent) {
        target.attachEvent("on" + event, method);
    }
}

/*
 * The next bit will be run on page load.
 */
addEvent("load", window, function() {
    /*
     * Setup logging.
     *
     * Messages will be logged both to the browser's console and to the
     * 'game-log' element.
     */
    window.gamelog = document.getElementById('game-log');
    window.log = function(type, msg) {
        console.log(msg);
        var node = document.createElement('p');
        node.className = type;
        node.innerText = msg;
        gamelog.appendChild(node);
    };

    /*
     * Connect and configure a websocket.
     */
    var sock = new WebSocket('ws://127.0.0.1:8000/conn');
    sock.onopen = function() {
        log('warn', "Connected");
    };
    sock.onmessage = function(e) {
        window.log('msg', e.data);
    };
    sock.onclose = function(e) {
        window.log('warn', "Disconnected");
    };
    sock.onerror = function(e) {
        window.log('error', "Error: " + e.data);
    };

    /*
     * Sends on the websocket when send_message is clicked.
     */
    (function() {
        var button = document.getElementById('send_message');
        var msg = document.getElementById('message');
        addEvent('click', button, function(e) {
            sock.send(msg.value);
            msg.value = "";
        });
        addEvent('keypress', message, function(e) {
            if(event.keyCode == 13)
            {
                sock.send(msg.value);
                msg.value = "";
            }
        });
    })();
});
