from __future__ import print_function

import json
import os
import thread
import time

from flask import Flask, jsonify, send_from_directory
from PIL import Image
from pdtools import ParadropClient

from .face_classifier import FaceClassifier
from .server import server
from .sonos_controller import SonosController


IMAGE_INTERVAL = os.environ.get('IMAGE_INTERVAL', 1.0)
PARADROP_DATA_DIR = os.environ.get("PARADROP_DATA_DIR", "/tmp")

SAVE_DIR = os.path.join(PARADROP_DATA_DIR, "photos")
STATUS_DIR = os.path.join(PARADROP_DATA_DIR, "status")


def setup():
    # Make sure the status and photo directories exist.
    if not os.path.isdir(STATUS_DIR):
        os.makedirs(STATUS_DIR)
    if not os.path.isdir(SAVE_DIR):
        os.makedirs(SAVE_DIR)

    # Run the web server in a separate thread.
    thread.start_new_thread(server.run, (), {'host': '0.0.0.0'})


def main():
    client = ParadropClient()
    sonos = SonosController()

    latest_path = os.path.join(STATUS_DIR, "latest.json")
    save_prefix = os.path.join(SAVE_DIR, "camera")

    dlibFacePredictor = "/opt/openface/models/dlib/shape_predictor_68_face_landmarks.dat"
    classifierModel = "LinearSvm.pkl"
    networkModel = "/opt/openface/models/openface/nn4.small2.v1.t7"
    imgDim = 96
    cuda = False
    classifier = FaceClassifier(dlibFacePredictor, classifierModel, networkModel, imgDim, cuda)

    try:
        m_sec = float(IMAGE_INTERVAL)
    except ValueError:
        raise Exception("IMAGE_INTERVAL is not numeric")

    while True:
        for camera in client.get_cameras():
            try:
                img = camera.get_image()
            except Exception as error:
                print("Error getting image from {}: {}".format(camera, str(error)))
                continue

            if img is None:
                print("** No image returned from {}".format(camera))
                continue

            # Load into Image object so we can compare images using PIL
            try:
                img = Image.open(img)
            except Exception as error:
                print("Image: {}".format(str(error)))
                continue

            timestamp = int(time.time())
            fileName = "camera-{}.jpg".format(timestamp)
            path = os.path.join(SAVE_DIR, fileName)
            img.save(path)
            print("Saved image: {}".format(path))

            people, scores, bbs = classifier.infer(path)
            if len(people) > 0:
                print("Detected: {} with score {}".format(people[0], scores[0]))

            newPath = os.path.join(STATUS_DIR, "latest.jpg")
            classifier.label(path, newPath, people, scores, bbs)

            latest = dict()
            latest['path'] = 'status/latest.jpg'
            latest['ts'] = timestamp
            latest['detections'] = [
                {'name': people[i], 'score': scores[i]} for i in range(len(people))
            ]

            with open(latest_path, 'w') as output:
                output.write(json.dumps(latest))

            if len(people) > 0:
                if all(p == "Unknown" for p in people):
                    sonos.play_alarm()
                else:
                    sonos.play_by_name(people[0])

        time.sleep(m_sec)


if __name__ == "__main__":
    setup()
    main()
