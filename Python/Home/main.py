# -*- coding: utf-8 -*-
"""
Created on Thu Feb 18 21:59:32 2021

@author: Roboadmin
"""
import threading
import time
from PEC_Libs import FaceID as Facerecognition
from PEC_Libs import hardware
import cv2
import base64
import dlib
from flask import Flask, render_template
from flask_socketio import SocketIO
import numpy as np
import os
import yaml


class YamlData(object):
    '''
     - Class for '.yaml' data type files
     - human read able!!
    '''

    def __init__(self, work_dir):
        '''
         - sets the given work_dir
        '''
        self.working_dir = work_dir

    def read_yaml_data(self, file_name):
        '''
         - Reads in a given data file
         - and returns an object with the file content
        '''
        with open(self.working_dir + file_name + '.yaml', 'r') as blc_stream:
            try:
                blc_data = yaml.load(blc_stream)
                print("Load Blc data: Done")
                return blc_data

            except yaml.YAMLError as exc:
                print(exc)

    def write_yaml_data(self, data_to_write, file_name):
        '''
         - Writes an object to a given file
        '''
        with open(self.working_dir + file_name + '.yaml', 'w') as save_file:
            try:
                yaml.dump(data_to_write, save_file, default_flow_style=False)
                print("Written data")
            except IOError:
                print("Writing impossible")

    def init_yaml_file(self, init_data, file_name):
        '''
         - creates the yaml file if not exists
         - or loads it if exists
        '''
        if os.path.isfile(self.working_dir + file_name + '.yaml'):
            data = self.read_yaml_data(file_name)
            return data
        else:
            try:
                with open(self.working_dir + file_name + '.yaml', 'w'):
                    data = self.write_yaml_data(init_data, file_name)
                    return data
                print("Init YAML DataBase")
                print(self.working_dir)
            except IOError:
                print("Writing impossible")

def gstreamer_pipeline(
    capture_width=3280,
    capture_height=2464,
    display_width=620,
    display_height=480,
    framerate=21,
    flip_method=2,
):
    return (
        "nvarguscamerasrc ! "
        "video/x-raw(memory:NVMM), "
        "width=(int)%d, height=(int)%d, "
        "format=(string)NV12, framerate=(fraction)%d/1 ! "
        "nvvidconv flip-method=%d ! "
        "video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=(string)BGR ! appsink"
        % (
            capture_width,
            capture_height,
            framerate,
            flip_method,
            display_width,
            display_height,
        )
    )

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
sio = SocketIO(app, cors_allowed_origins="*")
cap = cv2.VideoCapture(gstreamer_pipeline(), cv2.CAP_GSTREAMER)
trash1, trash2 = cap.read()
print(np.asarray(trash2).shape)
HW = hardware.PEC_HW()
detector = dlib.cnn_face_detection_model_v1('./mmod_human_face_detector.dat')
KILL_ML = False
yamel = YamlData('./account')
border_x = 109
corr_x = 0.0531
# border_y = 396
# corr_y = 0.0694


@sio.on('connect')
def test_connect():
    print("Connected")
    print('Hi')
    sio.emit('sensor', ('Hi', 1))


@sio.on('slider')
def slider(environ, slider_id):
    if slider_id == 1:
        HW.set_fan(environ)
        print(environ)
    elif slider_id == 2:
        HW.set_power(environ)
        print(environ)
    elif slider_id == 3:
        HW.set_mist(environ)
        print(environ)
    else:
        print("Error ID out of range")


@sio.on('cameratrig')
def cameratrig(data):
    global cap
    if cap.isOpened():
        retval, image = cap.read()
        image = image[:480 ,:640 ,:]
        dets = detector(image, 0)
        for i, d in enumerate(dets):
            image = Facerecognition.rectangle(image, d.rect.top(), d.rect.left(), d.rect.bottom(), 
                                              d.rect.right(), width=3)
        retval, buffer = cv2.imencode('.jpg', image[:, ::-1, :])
        jpg_as_text = base64.b64encode(buffer)
        sio.send(str(jpg_as_text)[2:-1], broadcast=True)
    else:
        print("Unable to open camera")



@sio.on("sensortrig")
def sensortrig():
    sio.emit('sensor', (HW.get_fan(), 1))
    sio.emit('sensor', (HW.get_temp(), 2))
    sio.emit('sensor', (HW.get_hum(), 3))
    time.sleep(1)


@sio.on('account')
def account(name, fan, temp, hum):
    yamel.init_yaml_file(name)
    daten = [fan, temp, hum]
    yamel.write_yaml_data(daten, name)


@sio.on('distance')
def distance(dist):
    global border_x, corr_x
    # global border_y, corr_y
    # degy = ((dist+0.1)*20)/dist
    # border_y = int((90-degx)*6)
    # corr_y = (20/degx)/12
    degx = ((dist+0.1)*90)/dist
    border_x = int((122-degx)*7.85)
    corr_x = (90/degx)/15.7


@sio.on('shutdown')
def shutdown():
    HW.sleep()


def Create_account():
    sio.emit('creat')


def Load_settings(Name):
    einstellungen = yamel.read_yaml_data(Name)
    sio.emit('sensor', (Name, 4))
    sio.emit('accountein', (einstellungen[0],
             einstellungen[1], einstellungen[2], 1))


def mainloop():
    FaceID = Facerecognition.ID(os.path.dirname(os.path.abspath(__file__))+"/Pictures")
    unknown = True

    while(not KILL_ML):
        ret, frame = cap.read()
        pos = detector(frame, 0)
        if not pos:
            unknown = True
            time.sleep(1)
        else:
            if unknown:
                unknown = False
                Face = FaceID.check_ID(image = frame)
                if Face:
                    Load_settings(Face)
                else:
                    Create_account()
            print("do it")
            HW.set_xpos(round(corr_x*(pos[0].rect.center().x-border_x)))
            # HW.set_ypos(round(corr_y*(pos[0].rect.center().y-border_y)))


if __name__ == '__main__':
    print("started server")
    try:
        ml = threading.Thread(target=mainloop).start()
        sio.run(app, host = 'localhost', port = 5000)
    except KeyboardInterrupt:
        KILL_ML = True
        ml.join()
        cap.release()
