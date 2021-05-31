# pylint: disable=E1101
# pylint: disable=W0105
# pylint: disable=C0325
# -*- coding: utf-8 -*-
"""
Created on Sun Sep 20, 2020

@author: Roboadmin
"""

import face_recognition
import os
import cv2
import numpy as np


class ID():

    def __init__(self, file="./known_faces"):
        """

        Loads Known Faces from dir.

        :param file: Image file name or file object to load.

        :return: Returns a string with "finished" or a Errormassage.
        """
        self.known_faces = []
        self.known_names = []
        for name in os.listdir(file):
            for filename in os.listdir(f"{file}/{name}"):
                image = face_recognition.load_image_file(
                    f"{file}/{name}/{filename}", mode='RGB')
                encoding = face_recognition.face_encodings(image)
                if(not encoding):
                    raise Exception(
                        f"Could not open file {file}/{name}/{filename}")
                self.known_faces.append(encoding[0])
                self.known_names.append(name)

    def check_ID(self, image=None, unknown_faces="./unknown_faces", tolerance=0.55, model="cnn"):
        """
        Looks for known faces and gives the name and postion as return.

        :param image: RGB array with the image (optional)
        :param tolerance: Precision of the model (lower => more accurate)
        :param unknown_faces: Dir of the picture to identify.
        :param mode: Model for processing the images (hog for CPU, cnn for GPU (CUDA)).

        Returns
        -------
        Position,
        face locaton
        both arrays
        """
        if not self.known_faces:
            print("Error: Before you can check ID you must initialize knowen faces!")
            return None
        match = [[], []]
        if image is None:
            for filename in os.listdir(unknown_faces):
                image = face_recognition.load_image_file(
                    f"{unknown_faces}/{filename}")
                if(image == 0):
                    return "Error by reading Pictures of unknown faces"
                locations = face_recognition.face_locations(image, model=model)
                encodings = face_recognition.face_encodings(image, locations)
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                for face_encoding, face_location in zip(encodings, locations):
                    results = face_recognition.compare_faces(
                        self.known_faces, face_encoding, tolerance)
                    if True in results:
                        match[0].append(self.known_names[results.index(True)])
                        match[1].append(face_location)
        else:
            locations = face_recognition.face_locations(image, model=model)
            encodings = face_recognition.face_encodings(image, locations)
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            for face_encoding, face_location in zip(encodings, locations):
                results = face_recognition.compare_faces(
                    self.known_faces, face_encoding, tolerance)
                if True in results:
                    match[0].append(self.known_names[results.index(True)])
                    match[1].append(face_location)
        return match[1], match[0]


def rectangle(img,  top, left, bottom, right, width=1, color=0):
    """
    A fast and simple function to draw a ractangle on an imagearray.
    It also includes clipping on the width parameter.
    Uses Numpy arrays to draw a ractangle arround the given cordinates.

    Parameters
    ----------
    img : np.Array
        Image as imagearray.
    top : int
        Top side coordinates.
    left : int
        Left side coordinates.
    bottom : int
        Bottom side coordinates.
    right : int
        Right side coordinates.
    width : int, optional
        Width of the outline . The default is 1.
    color : int, optional
        Color as array or int. The default is 0.

    Returns
    -------
    img : np.Array
        Returns the array with the ractangle.

    """
    if width < 0:
        width = 0
    img[0 if top-width < 0 else top-width:top, 0 if left -
        width < 0 else left-width:right+width] = color
    img[bottom:bottom+width, 0 if left-width <
        0 else left-width:right+width] = color
    img[top:bottom, 0 if left-width < 0 else left-width:left] = color
    img[top:bottom, right:right+width] = color
    return img
