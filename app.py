import json
import datetime
import time
import math
import random
import cvzone
import cv2
import numpy as np
from cvzone.HandTrackingModule import HandDetector
from flask import Flask, render_template, Response, request, redirect, url_for, session
from flask_socketio import SocketIO, emit, join_room
import os
import ssl
from distutils.util import strtobool
import aiohttp
from aiohttp import web
import jinja2
import aiohttp_jinja2
import uuid
from engineio.payload import Payload

Payload.max_decode_packets = 200

app = Flask(__name__)
app.config['SECRET_KEY'] = "roomfitisdead"

socketio = SocketIO(app, cors_allowed_origins='*')

############################## SNAKE GAME LOGIC SECTION ##############################
cap = cv2.VideoCapture(0)
cap.set(3, 1280)
cap.set(4, 720)
cap.set(cv2.CAP_PROP_FPS, 60)
fps = cap.get(cv2.CAP_PROP_FPS)

detector = HandDetector(detectionCon=0.5, maxHands=1)


class SnakeGameClass:
    def __init__(self, pathFood):
        self.points = []  # all points of the snake
        self.lengths = []  # distance between each point
        self.currentLength = 0  # total length of the snake
        self.allowedLength = 150  # total allowed Length
        self.previousHead = random.randint(100, 1000), random.randint(100, 600)

        self.speed = 0.1
        self.velocityX = random.choice([-1, 0, 1])
        self.velocityY = random.choice([-1, 0, 1])

        self.imgFood = cv2.imread(pathFood, cv2.IMREAD_UNCHANGED)
        self.hFood, self.wFood, _ = self.imgFood.shape
        self.foodPoint = 0, 0
        self.randomFoodLocation()

        self.score = 0
        self.gameOver = False

    # ---collision function---
    def ccw(self, p, a, b):
        vect_sub_ap = [a[0] - p[0], a[1] - p[1]]
        vect_sub_bp = [b[0] - p[0], b[1] - p[1]]
        return vect_sub_ap[0] * vect_sub_bp[1] - vect_sub_ap[1] * vect_sub_bp[0]

    def segmentIntersects(self, p1_a, p1_b, p2_a, p2_b):
        ab = self.ccw(p1_a, p1_b, p2_a) * self.ccw(p1_a, p1_b, p2_b)
        cd = self.ccw(p2_a, p2_b, p1_a) * self.ccw(p2_a, p2_b, p1_b)

        if (ab == 0 and cd == 0):
            if (p1_b[0] < p1_a[0] and p1_b[1] < p1_a[1]):
                p1_a, p1_b = p1_b, p1_a
            if (p2_b[0] < p2_a[0] and p2_b[1] < p2_a[1]):
                p2_a, p2_b = p2_b, p2_a
            return not ((p1_b[0] < p2_a[0] and p1_b[1] < p2_a[1]) or (p2_b[0] < p1_a[0] and p2_b[1] < p1_a[1]))

        return ab <= 0 and cd <= 0

    def isCollision(self, u1_head_pt, u2_pts):
        if not u2_pts:
            return False
        p1_a, p1_b = u1_head_pt[0], u1_head_pt[1]

        for u2_pt in u2_pts:
            p2_a, p2_b = u2_pt[0], u2_pt[1]
            if self.segmentIntersects(p1_a, p1_b, p2_a, p2_b):
                print(u2_pt)
                return True
        return False

    # ---collision function---end

    def randomFoodLocation(self):
        self.foodPoint = random.randint(100, 1000), random.randint(100, 600)

    def draw_snakes(self, imgMain, points, score, isMe):

        maincolor = (0, 0, 255)

        if isMe:
            maincolor = (0, 255, 0)

            # Draw Score
            cvzone.putTextRect(imgMain, f'Score: {score}', [50, 80],
                               scale=3, thickness=3, offset=10)

        # Draw Snake
        if points:
            cv2.circle(imgMain, points[-1][1], 15, maincolor, cv2.FILLED)

        pts = np.array(points, np.int32)
        if len(pts.shape) == 3:
            pts = pts[:, 1]
        pts = pts.reshape((-1, 1, 2))
        cv2.polylines(imgMain, np.int32([pts]), False, maincolor, 7)

        return imgMain

    def draw_Food(self, imgMain):
        # Draw Food
        rx, ry = self.foodPoint
        imgMain = cvzone.overlayPNG(imgMain, self.imgFood,
                                    (rx - self.wFood // 2, ry - self.hFood // 2))
        return imgMain

    def my_snake_update(self, HandPoints, o_bodys):
        px, py = self.previousHead
        # ----HandsPoint moving ----
        s_speed = 30
        if HandPoints:
            m_x, m_y = HandPoints
            dx = m_x - px  # -1~1
            dy = m_y - py

            # speed 범위: 0~1460
            if math.hypot(dx, dy) > math.hypot(1280, 720) / 10:
                self.speed = math.hypot(1280, 720) / 10  # 146
            elif math.hypot(dx, dy) < s_speed:
                self.speed = s_speed
            else:
                self.speed = math.hypot(dx, dy)

            if dx != 0:
                self.velocityX = dx / 1280
            if dy != 0:
                self.velocityY = dy / 720

            # print(self.velocityX)
            # print(self.velocityY)

            cx = round(px + self.velocityX * self.speed)
            cy = round(py + self.velocityY * self.speed)

        else:
            self.speed = s_speed
            cx = round(px + self.velocityX * self.speed)
            cy = round(py + self.velocityY * self.speed)
        # ----HandsPoint moving ----end

        # print(f'{cx} , {cy}')

        self.points.append([[px, py], [cx, cy]])
        # print(f'{self.points}')

        distance = math.hypot(cx - px, cy - py)
        self.lengths.append(distance)
        # print(f'self.length -> {self.lengths}')
        self.currentLength += distance
        self.previousHead = cx, cy

        # Length Reduction
        if self.currentLength > self.allowedLength:
            for i, length in enumerate(self.lengths):
                self.currentLength -= length
                self.lengths = self.lengths[1:]
                self.points = self.points[1:]

                if self.currentLength < self.allowedLength:
                    break

        # Check if snake ate the Food
        rx, ry = self.foodPoint
        # print(f'먹이 위치 : {self.foodPoint}')
        if rx - self.wFood // 2 < cx < rx + self.wFood // 2 and \
                ry - self.hFood // 2 < cy < ry + self.hFood // 2:
            self.randomFoodLocation()
            self.allowedLength += 50
            self.score += 1

        socketio.emit('game_data', {'head_x': cx, 'head_y': cy, 'body_node': self.points, 'score': self.score, 'fps' : fps})

        # ---- Collision ----
        # print(self.points[-1])
        # print(self.points[:-5])
        if self.isCollision(self.points[-1], o_bodys):
            print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Hit")
            self.gameOver = True
            self.points = []  # all points of the snake
            self.lengths = []  # distance between each point
            self.currentLength = 0  # total length of the snake
            self.allowedLength = 150  # total allowed Length
            self.previousHead = 0, 0  # previous head point
            self.randomFoodLocation()

    def update(self, imgMain, receive_Data, HandPoints=[]):
        global gameover_flag

        if self.gameOver:
            # pass
            cvzone.putTextRect(imgMain, "Game Over", [300, 400],
                               scale=7, thickness=5, offset=20)
            cvzone.putTextRect(imgMain, f'Your Score: {self.score}', [300, 550],
                               scale=7, thickness=5, offset=20)
            gameover_flag = True
        else:
            # draw others snake
            o_body_node = []
            o_score = 0

            if receive_Data:
                o_body_node = receive_Data["opp_body_node"]
                o_score = receive_Data["opp_score"]

            # 0 이면 상대 뱀
            imgMain = self.draw_snakes(imgMain, o_body_node, o_score, 0)

            # update and draw own snake
            self.my_snake_update(HandPoints, o_body_node)
            imgMain = self.draw_Food(imgMain)
            # 1 이면 내 뱀
            imgMain = self.draw_snakes(imgMain, self.points, self.score, 1)

        return imgMain


game = SnakeGameClass("./static/food.png")

opponent_data = []
gameover_flag = False
######################################################################################

@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")


@app.route("/enter_snake", methods=["GET", "POST"])
def enter_snake():
    room_id = request.args.get('room_id')
    sid = request.args.get('sid')
    print(room_id, sid)
    return render_template("snake.html", room_id=room_id, sid=sid)


@socketio.on('connect')
def test_connect():
    print('Client connected')


@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected')


@socketio.on('opp_data_transfer')
def opp_data_transfer(data):
    opp_head_x = data['data']['opp_head_x']
    opp_head_y = data['data']['opp_head_y']
    opp_body_node = data['data']['opp_body_node']
    opp_score = data['data']['opp_score']
    opp_room_id = data['data']['opp_room_id']
    opp_sid = data['data']['opp_sid']

    global opponent_data
    opponent_data = data['data']
    # socketio.emit('opp_data_to_test_server', {'data' : data}, broadcast=True)
    # print('Received data from client:', opp_head_x, opp_head_y, opp_score, opp_sid)


@app.route('/snake')
def snake():
    def generate():
        global opponent_data
        global game
        global gameover_flag
        
        while True:
            success, img = cap.read()
            img = cv2.flip(img, 1)
            hands, img = detector.findHands(img, flipType=False)

            pointIndex = []

            if hands:
                lmList = hands[0]['lmList']
                pointIndex = lmList[8][0:2]

            img = game.update(img, opponent_data, pointIndex)

            # encode the image as a JPEG string
            _, img_encoded = cv2.imencode('.jpg', img)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + img_encoded.tobytes() + b'\r\n')

            if gameover_flag:
                time.sleep(3)
                print("game ended")
                game = SnakeGameClass("./static/food.png")
                gameover_flag = False
            else:
                pass

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == "__main__":
    socketio.run(app, host='localhost', port=5000, debug=True)
