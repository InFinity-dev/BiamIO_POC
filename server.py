from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room, close_room, rooms, disconnect
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins='*')

# Store connected clients
clients = set()

# Store waiting clients
waiting_clients = set()

@socketio.on('connect')
def on_connect():
    clients.add(request.sid)

@socketio.on('disconnect')
def on_disconnect():
    clients.remove(request.sid)
    waiting_clients.discard(request.sid)

@socketio.on('join_queue')
def on_join_queue():
    waiting_clients.add(request.sid)
    if len(waiting_clients) > 1:
        # Match two random clients
        client1, client2 = random.sample(waiting_clients, 2)
        waiting_clients.discard(client1)
        waiting_clients.discard(client2)
        # Send match event to clients
        emit('match', {'client1': client1, 'client2': client2}, room=client1)
        emit('match', {'client1': client1, 'client2': client2}, room=client2)

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=7777, debug=True)