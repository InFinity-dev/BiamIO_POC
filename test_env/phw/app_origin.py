from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

waiting_players = []

# Global variables to store dot positions
dot1_pos = {'x': 0, 'y': 0}
dot2_pos = {'x': 0, 'y': 0}

# Handle connection event
@socketio.on('connect')
def handle_connect():
    print(waiting_players)
    print('Client connected ', request.sid)

# Handle disconnection event
@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in waiting_players:
        waiting_players.remove(request.sid)
        print(waiting_players)
        print('Client disconnected ', request.sid)

# @socketio.on('matchmake')
# def handle_matchmake():
#     if len(waiting_players) >= 2:
#         # pair up the first two waiting players
#         player1 = waiting_players.pop(0)
#         player2 = waiting_players.pop(0)
#         print(player1, player2)
#         # notify the two players that they have been matched
#         socketio.emit('matched', room=player1)
#         socketio.emit('matched', room=player2)
#     else:
#         # notify the player that they are still waiting for a match
#         socketio.emit('waiting', room=request.sid)

# Handle join event
@socketio.on('join')
def handle_join(data):
    join_room(request.sid)
    if len(waiting_players) == 0:
        waiting_players.append(request.sid)
        print(waiting_players)
        emit('waiting')
    else:
        dot1_sid = waiting_players.pop()
        dot2_sid = request.sid
        dot1_x, dot1_y = data['dot1_x'], data['dot1_y']
        dot2_x, dot2_y = data['dot2_x'], data['dot2_y']
        emit('matched', to=dot1_sid)
        emit('matched', to=dot2_sid)
        emit('start-game', {'dot1_x': dot1_x, 'dot1_y': dot1_y, 'dot2_x': dot2_x, 'dot2_y': dot2_y}, to=dot1_sid)
        emit('start-game', {'dot1_x': dot2_x, 'dot1_y': dot2_y, 'dot2_x': dot1_x, 'dot2_y': dot1_y}, to=dot2_sid)

@socketio.on('move')
def handle_move(data):
    emit(data['dot']+'-position', {'x': data['x'], 'y': data['y']}, broadcast=True)

# Handle reset event
@socketio.on('reset')
def handle_reset():
    emit('reset', broadcast=True)

# Render the HTML template
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0')