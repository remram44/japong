/*
 * Random utilities.
 */
/* Cross-browser addEventListener function */
window.addEvent = function(event, target, method) {
    if(target.addEventListener) {
        target.addEventListener(event, method, false);
    } else if (target.attachEvent) {
        target.attachEvent('on' + event, method);
    }
}

/* Smart animation, via @paul_irish */
window.requestAnimFrame = (function() {
    return window.requestAnimationFrame       ||
           window.webkitRequestAnimationFrame ||
           window.mozRequestAnimationFrame    ||
           window.oRequestAnimationFrame      ||
           window.msRequestAnimationFrame     ||
           function(callback) {
               window.setTimeout(callback, 1000/60);
           };
})();

/*
 * The next bit will be run on page load.
 */
addEvent('load', window, function() {
    /*
     * Setup logging.
     *
     * Messages will be logged both to the 'game-log' element.
     */
    window.gamelog = document.getElementById('game-log');
    window.log = function(type, msg) {
        var node = document.createElement('p');
        node.className = type;
        node.innerText = msg;
        gamelog.appendChild(node);
    };

    /*
     * Get server parameters.
     */
    var nickname, key, localracket, connect_addr;
    (function() {
        var read_param = function(param) {
            var el = document.getElementById(param);
            return el.value;
        };
        nickname = read_param('my-nick');
        key = read_param('my-key');
        localracket = read_param('my-racket');
        connect_addr = read_param('my-server');
    })();

    /*
     * Connect and configure a websocket.
     */
    var sock = new WebSocket('ws://' + connect_addr + '/conn');
    sock.onopen = function() {
        sock.send('Key: ' + key);
        log('warn', "!! Connected");
    };
    sock.onmessage = function(e) {
        window.log('msg', e.data);
    };
    sock.onclose = function(e) {
        window.log('error', "!! Disconnected");
        window.stop_animating = true;
    };
    sock.onerror = function(e) {
        window.log('error', "!! Error: " + e.data);
    };

    /*
     * Chat setup.
     */
    (function() {
        /* Sends on the websocket when send_message is clicked */
        var button = document.getElementById('send_message');
        var msg = document.getElementById('message');
        var sendmsg = function() {
            sock.send('Msg: ' + msg.value);
            msg.value = '';
        }
        addEvent('click', button, sendmsg);
        addEvent('keypress', message, function(e) {
            if(event.keyCode == 13)
                sendmsg();
        });
    })();

    /*
     * Game.
     */
    var canvas = document.getElementById('game-canvas');
    var width = canvas.width;
    var height = canvas.height;
    var RAQ_WIDTH = 10, RAQ_HEIGHT = 60;
    var BALL_SIZE = 30;
    var RAQ_SPEED = 0.15, BALL_SPEED = 0.2;
    var ARROW_UP = 38, ARROW_DOWN = 40;
    var move_down = false, move_up = false;
    var move_dir = 0;

    /* The rackets */
    var Racket = function(x, y) {
        this.x = x;
        this.y = y;
        this.v = 0;
    };
    var center = (height - RAQ_HEIGHT)/2;
    var rackets = new Array(
            new Racket(5, center),
            new Racket(width - RAQ_WIDTH - 5, center));

    /* The ball */
    var ball = {
        x: width/2,
        y: height/3,
        vx: BALL_SPEED,
        vy: BALL_SPEED};

    /* Listen to key events */
    var keydown_event = function(e) {
        if(e.which == ARROW_UP)
            move_up = true;
        else if(e.which == ARROW_DOWN)
            move_down = true;
        else
            return true;
        /* Prevents scrolling */
        e.preventDefault();
        return false;
    }
    var keyup_event = function(e) {
        if(e.which == ARROW_UP)
            move_up = false;
        else if(e.which == ARROW_DOWN)
            move_down = false;
    }
    for(var i in new Array(ARROW_DOWN, ARROW_UP)) {
        addEvent('keydown', document, keydown_event);
        addEvent('keyup', document, keyup_event);
    }

    /* This measures time between each call to elapsed() */
    window.Timer = function() {
        this.last = new Date().getTime();
    };
    Timer.prototype = {
        elapsed: function() {
            var now = new Date().getTime();
            var r = now - this.last;
            this.last = now;
            return r;
        }
    };

    var timer = new Timer();

    /*
     * Main loop.
     */
    window.stop_animating = false;
    window.anim_loop = function() {
        if(window.stop_animating)
            return;
        requestAnimFrame(window.anim_loop);

        /*
         * Physics!
         */
        var elapsed = timer.elapsed();

        /* Move the racket */
        var new_move_dir = 0;
        if(move_down && !move_up)
            new_move_dir = 1;
        else if(move_up && !move_down)
            new_move_dir = -1;
        if(new_move_dir != move_dir) {
            /* TODO : send */
            rackets[localracket].v = RAQ_SPEED * new_move_dir;
            move_dir = new_move_dir;
        }
        for(var r in rackets) {
            rackets[r].y += rackets[r].v * elapsed;
        }

        /* Move the ball */
        ball.x += ball.vx * elapsed;
        ball.y += ball.vy * elapsed;
        /* Vertical collisions */
        while(true) {
            if(ball.y + BALL_SIZE > height)
                ball.y = 2 * (height - BALL_SIZE) - ball.y;
            else if(ball.y < 0)
                ball.y = -ball.y;
            else
                break;
            ball.vy *= -1;
        }
        /* Collisions with a racket */
        if( (ball.x < rackets[0].x + RAQ_WIDTH)
         && (ball.y + BALL_SIZE > rackets[0].y)
         && (ball.y < rackets[0].y + RAQ_HEIGHT) )
            ball.vx = Math.abs(ball.vx);
        if( (ball.x + BALL_SIZE > rackets[1].x)
         && (ball.y + BALL_SIZE > rackets[1].y)
         && (ball.y < rackets[1].y + RAQ_HEIGHT) )
            ball.vx = -Math.abs(ball.vx);
        /* Somebody lost */
        if(ball.x < 0 || ball.x + BALL_SIZE > width) {
            ball.x = (width - BALL_SIZE)/2;
            ball.vx *= -1;
        }

        /*
         * Draw.
         */
        var g = canvas.getContext('2d');
        g.fillStyle = 'rgba(0, 0, 0, 1)';
        g.fillRect(0, 0, width, height);
        g.fillStyle = 'rgba(0, 255, 0, 1)';
        for(var r in rackets) {
            var racket = rackets[r];
            g.fillRect(racket.x, racket.y, RAQ_WIDTH, RAQ_HEIGHT);
        }
        g.fillStyle = 'rgba(0, 0, 127, 1)';
        g.fillRect(ball.x, ball.y, BALL_SIZE, BALL_SIZE);
    };
    anim_loop();
});
