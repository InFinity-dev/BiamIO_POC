import datetime
import time
from flask import Flask, render_template, Response, request, redirect, url_for, session
from flask_socketio import SocketIO, emit, join_room
import uuid
from engineio.payload import Payload
Payload.max_decode_packets = 200

app = Flask(__name__)
app.config['SECRET_KEY'] = "roomfitisdead"

socketio = SocketIO(app, cors_allowed_origins='*')

waiting_players = []
room_of_players = {}
players_in_room = {} 
last_created_room = ""

# @app.route("/", methods=["GET", "POST"])
@app.route("/")
def index():
    return render_template("index.html")

@socketio.on('connect')
def test_connect():
    print('Client connected')

@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected')

@app.route('/data')
def data():
    while True:
        time.sleep(1)
        socketio.emit('data', {'data': 'This is a data stream!'})


# Handle join event
@socketio.on('join')
def handle_join():
    sid = request.sid
    global last_created_room
    if len(waiting_players) == 0:
        waiting_players.append(sid)
        last_created_room = str(uuid.uuid4())

        # register sid to the room
        join_room(last_created_room)
        room_of_players[sid] = last_created_room
        emit('waiting', {'room_id' : last_created_room, 'sid' : sid}, to=last_created_room)
    else:
        host_sid = waiting_players.pop()
        room_id = room_of_players[host_sid]
        join_room(room_id)

        sid = request.sid
        room_of_players[sid] = room_id
        
        last_created_room = ""
        print(room_of_players)
        emit('matched', {'room_id' : room_id, 'sid' : sid}, to=room_id, broadcast=True)
        emit('start-game', to=room_id)
        

# 소켓 테스트용 1초마다 시간 쏴주는 함수
@app.route("/servertime")
def servertime():
    return render_template("servertime.html")


@socketio.on('get_time')
def get_time():
    while True:
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        socketio.emit('time', {'time': current_time})
        socketio.sleep(1)


if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=7777, debug=True)
