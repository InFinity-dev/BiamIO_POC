from flask import Flask, render_template
from flask_cors import CORS
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins='*')
cors = CORS(app)

@socketio.on('connect')
def handle_connect():
    print('A user connected')

@socketio.on('message')
def handle_message(data):
    print('Received message:', data)
    response = 'Received message: ' + data
    emit('response', response)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)