import socket
import threading
import time
from flask import Flask, render_template_string, request, redirect, make_response
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")  # Allow cross-origin requests

messages = []  # Store chat messages
connected_users = {}  # Store connected users and their IPs
user_typing = set()  # Track users currently typing

# HTML for the login page
LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>LAN Chat Login</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #0f172a;
            color: white;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .login-box {
            background: #1e293b;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.3);
        }
        .login-box h2 {
            color: #38bdf8;
            margin-bottom: 20px;
        }
        input, button {
            padding: 10px;
            margin: 10px 0;
            width: 100%;
            border: none;
            border-radius: 4px;
        }
        input {
            background: #334155;
            color: white;
        }
        button {
            background: #38bdf8;
            color: white;
            cursor: pointer;
        }
        button:hover {
            background: #0284c7;
        }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>LAN Chat Login</h2>
        <form method="POST">
            <input type="text" name="name" placeholder="Enter Your Name" required>
            <button type="submit">Join Chat</button>
        </form>
    </div>
</body>
</html>
"""

# HTML for the chat page
CHAT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>LAN Chat Room</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #0f172a;
            color: white;
            margin: 0;
            display: flex;
            height: 100vh;
        }
        .chat-container {
            display: flex;
            flex-grow: 1;
        }
        .chat-box {
            background: #1e293b;
            padding: 20px;
            border-radius: 8px;
            width: 70%;
            margin: auto;
            box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.3);
            display: flex;
            flex-direction: column;
            height: 90%;
        }
        .chat-header {
            font-size: 1.5rem;
            color: #38bdf8;
            margin-bottom: 10px;
            text-align: center;
        }
        .chat-messages {
            flex-grow: 1;
            overflow-y: auto;
            background: #334155;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 10px;
        }
        .message {
            margin-bottom: 10px;
            padding: 10px;
            border-radius: 8px;
            max-width: 70%;
        }
        .message-self {
            background: #2563eb;
            align-self: flex-start;
            color: white;
        }
        .message-other {
            background: #475569;
            align-self: flex-end;
            color: white;
        }
        .chat-input {
            display: flex;
        }
        .chat-input input {
            flex-grow: 1;
            padding: 10px;
            border: none;
            border-radius: 4px;
            background: #475569;
            color: white;
        }
        .chat-input button {
            background: #38bdf8;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 10px;
            margin-left: 10px;
            cursor: pointer;
        }
        .chat-input button:hover {
            background: #0284c7;
        }
        .user-list {
            width: 30%;
            padding: 20px;
            background: #1e293b;
            box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.3);
            border-radius: 8px;
            margin: auto;
            height: 90%;
            overflow-y: auto;
        }
        .user-list h3 {
            color: #38bdf8;
            text-align: center;
        }
        .user {
            padding: 10px;
            margin-bottom: 10px;
            background: #334155;
            border-radius: 8px;
        }
        .typing-indicator {
            font-size: 0.9rem;
            color: #9ca3af;
            margin-top: -10px;
            margin-bottom: 10px;
            text-align: left;
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="user-list">
            <h3>Connected Users</h3>
            <ul id="users"></ul>
        </div>
        <div class="chat-box">
            <div class="chat-header">LAN Chat</div>
            <div id="typing-indicator" class="typing-indicator"></div>
            <div class="chat-messages" id="messages"></div>
            <div class="chat-input">
                <input type="text" id="message" placeholder="Type your message...">
                <button id="send">Send</button>
            </div>
        </div>
    </div>
    <script>
        const socket = io();

        const messagesDiv = document.getElementById("messages");
        const usersList = document.getElementById("users");
        const messageInput = document.getElementById("message");
        const sendButton = document.getElementById("send");
        const typingIndicator = document.getElementById("typing-indicator");

        const name = "{{ name }}";
        const ip = "{{ ip }}";

        // Display connected users
        socket.on("update_users", (users) => {
            usersList.innerHTML = "";
            for (const [user, userIp] of Object.entries(users)) {
                const userItem = document.createElement("li");
                userItem.className = "user";
                userItem.textContent = `${user} (${userIp})`;
                usersList.appendChild(userItem);
            }
        });

        // Display messages
        socket.on("receive_message", (data) => {
            const messageDiv = document.createElement("div");
            messageDiv.className = "message";
            messageDiv.classList.add(data.name === name ? "message-self" : "message-other");
            messageDiv.textContent = `${data.name}: ${data.msg}`;
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight; // Auto-scroll
        });

        // Handle typing indicator
        socket.on("user_typing", (data) => {
            if (data.name !== name) {
                typingIndicator.textContent = `${data.name} is typing...`;
            }
        });

        socket.on("user_stopped_typing", (data) => {
            if (data.name !== name) {
                typingIndicator.textContent = "";
            }
        });

        // Send a message
        sendButton.addEventListener("click", () => {
            const msg = messageInput.value.trim();
            if (msg) {
                socket.emit("send_message", { name, msg });
                socket.emit("stopped_typing", { name });
                messageInput.value = "";
            }
        });

        // Send typing events
        messageInput.addEventListener("input", () => {
            if (messageInput.value.trim() !== "") {
                socket.emit("typing", { name });
            } else {
                socket.emit("stopped_typing", { name });
            }
        });

        // Notify server of connection
        socket.emit("user_connected", { name, ip });
    </script>
</body>
</html>
"""

# Utility function to get the local IP address
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form["name"]
        resp = make_response(redirect("/chat"))
        resp.set_cookie("name", name)
        return resp
    return render_template_string(LOGIN_HTML)


@app.route("/chat")
def chat():
    name = request.cookies.get("name")
    if not name:
        return redirect("/")
    ip = get_ip()
    return render_template_string(CHAT_HTML, name=name, ip=ip)


@socketio.on("send_message")
def handle_send_message(data):
    messages.append(data)
    emit("receive_message", data, broadcast=True)


@socketio.on("user_connected")
def handle_user_connected(data):
    connected_users[data["name"]] = data["ip"]
    emit("update_users", connected_users, broadcast=True)


@socketio.on("typing")
def handle_typing(data):
    user_typing.add(data["name"])
    emit("user_typing", data, broadcast=True)


@socketio.on("stopped_typing")
def handle_stopped_typing(data):
    user_typing.discard(data["name"])
    emit("user_stopped_typing", data, broadcast=True)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)