import socket
import threading
from flask import Flask, render_template_string, request, redirect, make_response
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

messages = []

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>LAN Chat Login</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        :root {
            --main-bg: #171923;
            --card-bg: #22243a;
            --accent: #3b82f6;
            --accent2: #a855f7;
            --input-bg: #23263a;
            --input-border: #44476a;
            --text: #f3f4f6;
            --text-dim: #b3b7cf;
            --shadow: 0 8px 32px 0 rgba(0,0,0,0.37);
        }
        body {
            background: var(--main-bg);
            color: var(--text);
            font-family: 'Segoe UI', 'Roboto', 'Arial', sans-serif;
            height: 100vh;
            margin: 0;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-card {
            background: var(--card-bg);
            box-shadow: var(--shadow);
            padding: 2.5rem 2.5rem 1.5rem 2.5rem;
            border-radius: 1.5rem;
            min-width: 340px;
            display: flex;
            flex-direction: column;
            align-items: center;
            animation: fadeIn 1s cubic-bezier(.39,.575,.565,1) both;
        }
        .login-card h2 {
            margin-bottom: 1.2rem;
            font-size: 2rem;
            font-weight: bold;
            letter-spacing: 0.03em;
            color: var(--accent);
            text-shadow: 0 2px 16px #000a;
        }
        .login-card form {
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .login-card input[type="text"] {
            padding: 0.8rem 1.2rem;
            border-radius: 0.6rem;
            border: 1px solid var(--input-border);
            background: var(--input-bg);
            color: var(--text);
            font-size: 1.1rem;
            margin-bottom: 1.5rem;
            outline: none;
            transition: border 0.2s;
            box-shadow: 0 1px 2px #0003;
        }
        .login-card input[type="text"]:focus {
            border: 1.5px solid var(--accent2);
        }
        .login-card input[type="submit"] {
            background: linear-gradient(90deg, var(--accent) 0%, var(--accent2) 100%);
            color: #fff;
            border: none;
            padding: 0.8rem 2.2rem;
            border-radius: 0.6rem;
            font-size: 1.1rem;
            font-weight: bold;
            cursor: pointer;
            letter-spacing: 0.04em;
            box-shadow: 0 2px 12px #000a;
            transition: background 0.2s, transform 0.1s;
        }
        .login-card input[type="submit"]:hover {
            background: linear-gradient(90deg, var(--accent2) 0%, var(--accent) 100%);
            transform: scale(1.04);
        }
        @keyframes fadeIn {
            0% { opacity: 0; transform: scale(0.98);}
            100% { opacity: 1; transform: scale(1);}
        }
    </style>
</head>
<body>
    <div class="login-card">
        <h2>LAN Chat</h2>
        <form method="post" autocomplete="off">
            <input type="text" name="name" maxlength="20" required placeholder="Enter your name...">
            <input type="submit" value="Join Chat">
        </form>
    </div>
</body>
</html>
"""

CHAT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>LAN Chat Room</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="//cdnjs.cloudflare.com/ajax/libs/socket.io/2.3.0/socket.io.js"></script>
    <style>
        :root {
            --main-bg: #171923;
            --card-bg: #22243a;
            --accent: #3b82f6;
            --accent2: #a855f7;
            --input-bg: #23263a;
            --input-border: #44476a;
            --text: #f3f4f6;
            --text-dim: #b3b7cf;
            --msg-bg-self: #a855f7;
            --msg-bg-other: #23263a;
            --msg-bg-sys: #44476a;
            --shadow: 0 8px 32px 0 rgba(0,0,0,0.37);
        }
        html, body {
            height: 100%;
            margin: 0;
            background: var(--main-bg);
            color: var(--text);
            font-family: 'Segoe UI', 'Roboto', 'Arial', sans-serif;
            box-sizing: border-box;
        }
        .container {
            min-height: 100vh;
            width: 100vw;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .chat-card {
            background: var(--card-bg);
            box-shadow: var(--shadow);
            border-radius: 1.5rem;
            padding: 2.2rem 2.5rem 1.6rem 2.5rem;
            max-width: 480px;
            width: 96vw;
            display: flex;
            flex-direction: column;
            animation: fadeIn 0.8s cubic-bezier(.39,.575,.565,1) both;
        }
        .chat-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.9rem;
        }
        .chat-title {
            font-size: 1.7rem;
            font-weight: bold;
            letter-spacing: 0.03em;
            color: var(--accent);
            text-shadow: 0 2px 16px #000a;
        }
        .user-info {
            font-size: 0.97rem;
            color: var(--text-dim);
            background: #23263a;
            padding: 0.4em 0.8em;
            border-radius: 0.7em;
            box-shadow: 0 1px 4px #0002;
        }
        #chat-box {
            border-radius: 1rem;
            background: #181a28;
            border: 1px solid var(--input-border);
            box-shadow: 0 1px 16px #0001;
            width: 100%;
            min-height: 260px;
            max-height: 320px;
            padding: 1.1em 1.2em 0.9em 1.2em;
            font-size: 1.07rem;
            overflow-y: auto;
            margin-bottom: 1.2em;
            scrollbar-width: thin;
        }
        .msg {
            margin-bottom: 0.85em;
            display: flex;
            flex-direction: column;
            gap: 0.1em;
            word-break: break-word;
            animation: fadeMsg 0.25s;
        }
        .msg.msg-self .msg-bubble {
            align-self: flex-end;
            background: linear-gradient(90deg, var(--accent) 0%, var(--accent2) 100%);
            color: #fff;
            border-bottom-right-radius: 0.4em;
            border-bottom-left-radius: 1.1em;
            border-top-right-radius: 1.1em;
            border-top-left-radius: 1.1em;
        }
        .msg.msg-other .msg-bubble {
            align-self: flex-start;
            background: var(--msg-bg-other);
            color: var(--text);
            border-bottom-left-radius: 0.4em;
            border-bottom-right-radius: 1.1em;
            border-top-right-radius: 1.1em;
            border-top-left-radius: 1.1em;
        }
        .msg .msg-bubble {
            max-width: 295px;
            padding: 0.65em 1em;
            font-size: 1.06em;
            box-shadow: 0 2px 10px #0002;
            margin-bottom: 0.08em;
        }
        .msg .msg-sender {
            font-size: 0.95em;
            color: var(--text-dim);
            margin-bottom: 0.03em;
            padding-left: 0.1em;
            font-weight: 600;
            letter-spacing: 0.01em;
        }
        .msg.msg-sys .msg-bubble {
            background: var(--msg-bg-sys);
            color: #fff;
            font-size: 0.98em;
            text-align: center;
            border-radius: 0.7em;
            margin: 0 auto;
            padding: 0.5em 1em;
        }
        @keyframes fadeIn {
            0% { opacity: 0; transform: translateY(50px);}
            100% { opacity: 1; transform: translateY(0);}
        }
        @keyframes fadeMsg {
            0% { opacity: 0; transform: translateY(7px);}
            100% { opacity: 1; transform: translateY(0);}
        }
        .chat-input-row {
            display: flex;
            align-items: center;
            gap: 0.7em;
            margin-top: 0.2em;
        }
        #msg {
            flex: 1;
            padding: 0.75em 1em;
            border-radius: 0.7em;
            border: 1.5px solid var(--input-border);
            background: var(--input-bg);
            color: var(--text);
            font-size: 1.09em;
            outline: none;
            transition: border 0.2s;
        }
        #msg:focus {
            border: 1.5px solid var(--accent);
        }
        .send-btn {
            background: linear-gradient(90deg, var(--accent2) 0%, var(--accent) 100%);
            color: #fff;
            border: none;
            padding: 0.7em 1.4em;
            border-radius: 0.7em;
            font-size: 1.1em;
            font-weight: bold;
            cursor: pointer;
            letter-spacing: 0.04em;
            box-shadow: 0 2px 10px #0002;
            transition: background 0.22s, transform 0.13s;
        }
        .send-btn:hover {
            background: linear-gradient(90deg, var(--accent) 0%, var(--accent2) 100%);
            transform: scale(1.06);
        }
        @media (max-width: 600px) {
            .chat-card { padding: 1.2rem 0.5rem 0.9rem 0.5rem; }
            #chat-box { font-size: 0.98rem; min-height: 160px; max-height: 220px;}
            .chat-title { font-size: 1.18rem; }
            .user-info { font-size: 0.85rem;}
        }
    </style>
</head>
<body>
    <div class="container">
    <div class="chat-card">
        <div class="chat-header">
            <div class="chat-title">LAN Chat</div>
            <div class="user-info">
                <span style="color:var(--accent2);font-weight:600;">{{ name|e }}</span> &bull;
                <span title="Your device LAN IP">{{ ip }}</span>
            </div>
        </div>
        <div id="chat-box">
            {% for msg in messages %}
                {% if msg['sys'] %}
                    <div class="msg msg-sys"><div class="msg-bubble">{{ msg['msg'] }}</div></div>
                {% elif msg['name'] == name %}
                    <div class="msg msg-self">
                        <div class="msg-sender">You</div>
                        <div class="msg-bubble">{{ msg['msg'] }}</div>
                    </div>
                {% else %}
                    <div class="msg msg-other">
                        <div class="msg-sender">{{ msg['name']|e }}</div>
                        <div class="msg-bubble">{{ msg['msg'] }}</div>
                    </div>
                {% endif %}
            {% endfor %}
        </div>
        <form class="chat-input-row" onsubmit="sendMsg();return false;" autocomplete="off">
            <input type="text" id="msg" maxlength="240" placeholder="Type your message..." autofocus autocomplete="off">
            <button type="button" class="send-btn" onclick="sendMsg()">Send</button>
        </form>
    </div>
    </div>
    <script>
        var socket = io();
        var name = "{{ name|escapejs }}";
        var chatBox = document.getElementById('chat-box');
        function scrollToBottom() {
            chatBox.scrollTop = chatBox.scrollHeight;
        }
        scrollToBottom();

        socket.on('receive_message', function(data){
            let div = document.createElement('div');
            if (data.sys) {
                div.className = 'msg msg-sys';
                div.innerHTML = `<div class="msg-bubble">${data.msg}</div>`;
            } else if (data.name === name) {
                div.className = 'msg msg-self';
                div.innerHTML = `<div class="msg-sender">You</div><div class="msg-bubble">${data.msg}</div>`;
            } else {
                div.className = 'msg msg-other';
                div.innerHTML = `<div class="msg-sender">${data.name}</div><div class="msg-bubble">${data.msg}</div>`;
            }
            chatBox.appendChild(div);
            scrollToBottom();
        });
        function sendMsg() {
            var msg = document.getElementById('msg').value.trim();
            if(msg) {
                socket.emit('send_message', {name: name, msg: msg});
                document.getElementById('msg').value = '';
            }
        }
        document.getElementById('msg').addEventListener('keydown', function(e) {
            if (e.key === 'Enter') sendMsg();
        });
        window.onload = function() {
            setTimeout(scrollToBottom, 20);
        }
    </script>
</body>
</html>
"""

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

@app.route('/', methods=['GET', 'POST'])
def index():
    name = request.cookies.get('name')
    if request.method == 'POST':
        name = request.form['name']
        resp = make_response(redirect('/chat'))
        resp.set_cookie('name', name, max_age=60*60*24*30)
        return resp
    if not name:
        return render_template_string(LOGIN_HTML)
    return redirect('/chat')

@app.route('/chat')
def chat():
    name = request.cookies.get('name')
    if not name:
        return redirect('/')
    ip = get_ip()
    return render_template_string(CHAT_HTML, name=name, ip=ip, messages=messages)

@socketio.on('send_message')
def handle_message(data):
    name = data['name']
    msg = data['msg']
    messages.append({'name': name, 'msg': msg, 'sys': False})
    emit('receive_message', {'name': name, 'msg': msg, 'sys': False}, broadcast=True)

def system_broadcast(msg):
    messages.append({'name': '', 'msg': msg, 'sys': True})
    socketio.emit('receive_message', {'msg': msg, 'sys': True})

def lan_discovery_broadcast():
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    message = b'LAN_CHAT_DISCOVERY'
    while True:
        udp.sendto(message, ('<broadcast>', 54545))
        socketio.sleep(5)

def lan_discovery_listen():
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp.bind(('', 54545))
    known = set()
    while True:
        data, addr = udp.recvfrom(1024)
        if data == b'LAN_CHAT_DISCOVERY':
            ip = addr[0]
            if ip not in known:
                known.add(ip)
                system_broadcast(f"Peer found on LAN: <span style='color:#a855f7;font-weight:600'>{ip}</span>")

if __name__ == '__main__':
    threading.Thread(target=lan_discovery_broadcast, daemon=True).start()
    threading.Thread(target=lan_discovery_listen, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)