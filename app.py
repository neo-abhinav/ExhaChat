import socket
import threading
from flask import Flask, render_template_string, request, redirect, make_response
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

users = set()
messages = []

LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>LAN Chat Login</title>
</head>
<body>
    <h2>Enter your name to join LAN Chat</h2>
    <form method="post">
        <input type="text" name="name" required placeholder="Your Name">
        <input type="submit" value="Join Chat">
    </form>
</body>
</html>
"""

CHAT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>LAN Chat Room</title>
    <script src="//cdnjs.cloudflare.com/ajax/libs/socket.io/2.3.0/socket.io.js"></script>
</head>
<body>
    <h2>LAN Chat</h2>
    <p>Welcome, <b>{{ name }}</b>! Your LAN IP: {{ ip }}</p>
    <div id="chat-box" style="border:1px solid #ccc; width:400px; height:300px; overflow:auto;">
        {% for msg in messages %}
            <b>{{ msg.name }}</b>: {{ msg.msg }}<br>
        {% endfor %}
    </div>
    <input type="text" id="msg" placeholder="Type message...">
    <button onclick="sendMsg()">Send</button>
    <script>
        var socket = io();
        var name = "{{ name }}";
        socket.on('receive_message', function(data){
            var chatBox = document.getElementById('chat-box');
            chatBox.innerHTML += "<b>" + data.name + "</b>: " + data.msg + "<br>";
            chatBox.scrollTop = chatBox.scrollHeight;
        });
        function sendMsg() {
            var msg = document.getElementById('msg').value;
            if(msg) {
                socket.emit('send_message', {name: name, msg: msg});
                document.getElementById('msg').value = '';
            }
        }
        document.getElementById('msg').addEventListener('keydown', function(e) {
            if (e.key === 'Enter') sendMsg();
        });
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
        resp.set_cookie('name', name)
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
    messages.append({'name': name, 'msg': msg})
    emit('receive_message', {'name': name, 'msg': msg}, broadcast=True)

# Basic LAN discovery: broadcast a UDP packet with your IP
def lan_discovery_broadcast():
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    message = b'LAN_CHAT_DISCOVERY'
    while True:
        udp.sendto(message, ('<broadcast>', 54545))
        socketio.sleep(5)

# Listen for other LAN chat servers
def lan_discovery_listen():
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp.bind(('', 54545))
    while True:
        data, addr = udp.recvfrom(1024)
        if data == b'LAN_CHAT_DISCOVERY':
            print(f"Discovered chat server at {addr[0]}")

if __name__ == '__main__':
    threading.Thread(target=lan_discovery_broadcast, daemon=True).start()
    threading.Thread(target=lan_discovery_listen, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=5000)