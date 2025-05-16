import socket
import threading
from flask import Flask, render_template_string, request, redirect, make_response
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")  # Allow cross-origin requests

messages = []  # In-memory storage for chat messages

# HTML for the login page
LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>LAN Chat Login</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #181a1b;
            color: white;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .login-form {
            background: #222;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }
        input, button {
            padding: 10px;
            margin: 5px 0;
            width: 100%;
            border: none;
            border-radius: 4px;
        }
        input {
            background: #444;
            color: white;
        }
        button {
            background: #3b82f6;
            color: white;
            cursor: pointer;
        }
        button:hover {
            background: #2563eb;
        }
    </style>
</head>
<body>
    <form class="login-form" method="POST">
        <h2>Enter Your Name</h2>
        <input type="text" name="name" placeholder="Your Name" required>
        <button type="submit">Join Chat</button>
    </form>
</body>
</html>
"""

# HTML for the chat page
CHAT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>LAN Chat</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #181a1b;
            color: white;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .chat-box {
            background: #222;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            width: 400px;
        }
        #messages {
            background: #333;
            padding: 10px;
            height: 300px;
            overflow-y: auto;
            border-radius: 4px;
            margin-bottom: 10px;
        }
        #messages div {
            margin-bottom: 10px;
        }
        input, button {
            padding: 10px;
            margin: 5px 0;
            border: none;
            border-radius: 4px;
        }
        input {
            width: calc(100% - 80px);
            background: #444;
            color: white;
        }
        button {
            width: 70px;
            background: #3b82f6;
            color: white;
            cursor: pointer;
        }
        button:hover {
            background: #2563eb;
        }
    </style>
</head>
<body>
    <div class="chat-box">
        <h2>LAN Chat</h2>
        <div id="messages"></div>
        <div>
            <input type="text" id="message" placeholder="Type your message">
            <button id="send">Send</button>
        </div>
    </div>
    <script>
        const socket = io();

        const messagesDiv = document.getElementById("messages");
        const messageInput = document.getElementById("message");
        const sendButton = document.getElementById("send");

        // Listen for incoming messages
        socket.on("receive_message", (data) => {
            const messageElement = document.createElement("div");
            messageElement.textContent = `${data.name}: ${data.msg}`;
            messagesDiv.appendChild(messageElement);
            messagesDiv.scrollTop = messagesDiv.scrollHeight; // Auto-scroll
        });

        // Send message on button click
        sendButton.addEventListener("click", () => {
            const message = messageInput.value.trim();
            if (message) {
                socket.emit("send_message", { name: "{{ name }}", msg: message });
                messageInput.value = "";
            }
        });

        // Send message on Enter key press
        messageInput.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                sendButton.click();
            }
        });
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
    return render_template_string(CHAT_HTML, name=name)


@socketio.on("send_message")
def handle_send_message(data):
    messages.append(data)
    emit("receive_message", data, broadcast=True)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)