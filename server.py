from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# List of users waiting for a match
waiting_users = []

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def on_connect():
    # Add the user to the waiting list
    waiting_users.append(request.sid)
    print(f'User {request.sid} connected and added to the waiting list')

    # Check if there's a user waiting to be matched
    if len(waiting_users) >= 2:
        # Get the first two users from the waiting list
        user1 = waiting_users.pop(0)
        user2 = waiting_users.pop(0)

        # Join the two users to a room with a unique name
        room = f'{user1}-{user2}'
        join_room(room)

        # Notify the users that they have been matched and provide them with the room name
        emit('matched', {'room': room}, to=user1)
        emit('matched', {'room': room}, to=user2)

@socketio.on('message')
def on_message(data):
    # Send the message to the other user in the same room
    room = request.sid.split('-')[0] + '-' + request.sid.split('-')[1]
    emit('message', data, room=room)

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=7777, debug=True)
