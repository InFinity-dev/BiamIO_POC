import json
import time
import math
import random
import cvzone
import cv2
import numpy as np
from cvzone.HandTrackingModule import HandDetector
from flask import Flask, render_template, Response, request, redirect, url_for, session
from flask_socketio import SocketIO, emit
import os
import ssl
from distutils.util import strtobool
import aiohttp
from aiohttp import web
import jinja2
import aiohttp_jinja2

from engineio.payload import Payload
Payload.max_decode_packets = 200

app = Flask(__name__)
app.config['SECRET_KEY'] = "roomfitisdead"

socketio = SocketIO(app)

############################## SNAKE GAME LOGIC SECTION ##############################

cap = cv2.VideoCapture(0)
cap.set(3, 1280)
cap.set(4, 720)

detector = HandDetector(detectionCon=0.5, maxHands=1)

class SnakeGameClass:
    def __init__(self, pathFood):
        self.points = []  # all points of the snake
        self.lengths = []  # distance between each point
        self.currentLength = 0  # total length of the snake
        self.allowedLength = 150  # total allowed Length
        self.previousHead = 0, 0  # previous head point

        self.imgFood = cv2.imread(pathFood, cv2.IMREAD_UNCHANGED)
        self.hFood, self.wFood, _ = self.imgFood.shape
        self.foodPoint = 0, 0
        self.randomFoodLocation()

        self.score = 0
        self.gameOver = False

    def randomFoodLocation(self):
        self.foodPoint = random.randint(100, 1000), random.randint(100, 600)

    def update(self, imgMain, currentHead):

        if self.gameOver:
            # pass
            cvzone.putTextRect(imgMain, "Game Over", [300, 400],
                               scale=7, thickness=5, offset=20)
            cvzone.putTextRect(imgMain, f'Your Score: {self.score}', [300, 550],
                               scale=7, thickness=5, offset=20)
        else:
            px, py = self.previousHead
            cx, cy = currentHead

            print(f'{cx} , {cy}')

            self.points.append([cx, cy])
            print(f'{self.points}')

            socketio.emit('game_data', {'head_x': cx, 'head_y': cy})
            socketio.emit('game_data', {'body_node': self.points})

            distance = math.hypot(cx - px, cy - py)
            self.lengths.append(distance)
            # print(f'self.length -> {self.lengths}')
            self.currentLength += distance
            self.previousHead = cx, cy

            # Length Reduction
            if self.currentLength > self.allowedLength:
                for i, length in enumerate(self.lengths):
                    self.currentLength -= length
                    self.lengths.pop(i)
                    self.points.pop(i)
                    if self.currentLength < self.allowedLength:
                        break

            # Check if snake ate the Food
            rx, ry = self.foodPoint
            print(f'먹이 위치 : {self.foodPoint}')
            if rx - self.wFood // 2 < cx < rx + self.wFood // 2 and \
                    ry - self.hFood // 2 < cy < ry + self.hFood // 2:
                self.randomFoodLocation()
                self.allowedLength += 50
                self.score += 1

                print(self.score)
                socketio.emit('game_data', {'score': self.score})

            # Draw Snake
            if self.points:
                for i, point in enumerate(self.points):
                    if i != 0:
                        cv2.line(imgMain, self.points[i - 1], self.points[i], (0, 0, 255), 20)
                cv2.circle(imgMain, self.points[-1], 20, (0, 255, 0), cv2.FILLED)

            # Draw Food
            imgMain = cvzone.overlayPNG(imgMain, self.imgFood,
                                        (rx - self.wFood // 2, ry - self.hFood // 2))

            cvzone.putTextRect(imgMain, f'Score: {self.score}', [50, 80],
                               scale=3, thickness=3, offset=10)

            # Check for Collision
            pts = np.array(self.points[:-5], np.int32)
            pts = pts.reshape((-1, 1, 2))
            cv2.polylines(imgMain, [pts], False, (0, 255, 0), 3)

            minDist = cv2.pointPolygonTest(pts, (cx, cy), True)

            # h, w, c = imgMain.shape
            # opimg = np.zeros([h,w,c])
            # opimg.fill(255)
            # cv2.polylines(opimg, [pts], False, (0, 255, 0), 3)
            # cv2.imshow('opimg',opimg)

            if -1 <= minDist <= 1:
                print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Hit")
                # self.gameOver = True
                # self.points = []  # all points of the snake
                # self.lengths = []  # distance between each point
                # self.currentLength = 0  # total length of the snake
                # self.allowedLength = 150  # total allowed Length
                # self.previousHead = 0, 0  # previous head point
                # self.randomFoodLocation()

        return imgMain

game = SnakeGameClass("./static/food.png")
######################################################################################

@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("snake.html")

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

@app.route('/snake')
def snake():
    def generate():
        while True:
            success, img = cap.read()
            img = cv2.flip(img, 1)
            hands, img = detector.findHands(img, flipType=False)

            if hands:
                lmList = hands[0]['lmList']
                pointIndex = lmList[8][0:2]
                img = game.update(img, pointIndex)

            # encode the image as a JPEG string
            _, img_encoded = cv2.imencode('.jpg', img)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + img_encoded.tobytes() + b'\r\n')

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
