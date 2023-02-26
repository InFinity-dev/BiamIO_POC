import math
from tkinter import W
dx=0.00005
dy=0.001
velocityX = dx/math.sqrt(dx**2+dy**2)
velocityY = dy/math.sqrt(dx**2+dy**2)

print(velocityX)
print(velocityY)
print(math.sqrt(velocityX**2+velocityY**2))