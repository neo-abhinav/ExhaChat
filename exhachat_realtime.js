// ExhaChat Backend Server
// Install dependencies: npm install express socket.io cors

const express = require('express');
const http = require('http');
const socketIO = require('socket.io');
const cors = require('cors');

const app = express();
const server = http.createServer(app);
const io = socketIO(server, {
    cors: {
        origin: "*",
        methods: ["GET", "POST"]
    }
});

app.use(cors());
app.use(express.json());
app.use(express.static('public')); // Serve HTML file from public folder

const PASSWORD = "Seashore";
const users = new Map(); // userId -> {name, socketId}
const messages = []; // Store last 200 messages
const privateMessages = new Map(); // userId -> messages array

// Socket.IO connection
io.on('connection', (socket) => {
    console.log('New client connected:', socket.id);

    // Handle login
    socket.on('login', (data) => {
        const { name, password, userId } = data;

        if (password !== PASSWORD) {
            socket.emit('login_failed', { message: 'Wrong password' });
            return;
        }

        // Register user
        users.set(userId, { name, socketId: socket.id });
        socket.userId = userId;
        socket.userName = name;

        // Send existing messages to new user
        socket.emit('login_success', {
            userId,
            messages: messages.slice(-200),
            privateMessages: Array.from(privateMessages.entries())
        });

        // Broadcast user joined
        io.emit('user_joined', {
            userId,
            name,
            users: Array.from(users.entries()).map(([id, data]) => ({ id, name: data.name }))
        });

        console.log(`${name} logged in`);
    });

    // Handle group message
    socket.on('send_message', (data) => {
        const message = {
            id: Date.now() + '_' + Math.random().toString(36).slice(2, 6),
            from: socket.userName,
            fromId: socket.userId,
            text: data.text,
            ts: Date.now()
        };

        messages.push(message);
        if (messages.length > 200) messages.shift();

        io.emit('new_message', message);
    });

    // Handle private message
    socket.on('send_private_message', (data) => {
        const message = {
            id: Date.now() + '_' + Math.random().toString(36).slice(2, 6),
            from: socket.userName,
            fromId: socket.userId,
            toId: data.toId,
            text: data.text,
            ts: Date.now()
        };

        // Store private message
        const key1 = `${socket.userId}_${data.toId}`;
        const key2 = `${data.toId}_${socket.userId}`;

        if (!privateMessages.has(key1)) privateMessages.set(key1, []);
        if (!privateMessages.has(key2)) privateMessages.set(key2, []);

        privateMessages.get(key1).push(message);
        privateMessages.get(key2).push(message);

        // Send to sender
        socket.emit('new_private_message', message);

        // Send to recipient if online
        const recipient = users.get(data.toId);
        if (recipient) {
            io.to(recipient.socketId).emit('new_private_message', message);
        }
    });

    // Handle typing indicator
    socket.on('typing', (data) => {
        socket.broadcast.emit('user_typing', {
            name: socket.userName,
            chatId: data.chatId
        });
    });

    socket.on('stopped_typing', () => {
        socket.broadcast.emit('user_stopped_typing', {
            name: socket.userName
        });
    });

    // Handle disconnect
    socket.on('disconnect', () => {
        if (socket.userId) {
            users.delete(socket.userId);
            io.emit('user_left', {
                userId: socket.userId,
                users: Array.from(users.entries()).map(([id, data]) => ({ id, name: data.name }))
            });
            console.log(`${socket.userName} disconnected`);
        }
    });
});

const PORT = 80;
server.listen(PORT, () => {
    console.log(`ExhaChat server running on port ${PORT}`);
    console.log(`Open http://localhost:${PORT} in your browser`);
});