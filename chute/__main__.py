from __future__ import print_function

import os
import thread
import time

from flask import Flask, jsonify, send_from_directory
from PIL import Image
from pdtools import ParadropClient


IMAGE_INTERVAL = os.environ.get('IMAGE_INTERVAL', 2.0)
PARADROP_DATA_DIR = os.environ.get("PARADROP_DATA_DIR", "/tmp")

SAVE_DIR = os.path.join(PARADROP_DATA_DIR, "photos")

server = Flask(__name__)


@server.route('/photos/<path:path>')
def GET_photo(path):
    return send_from_directory(SAVE_DIR, path)


@server.route('/')
def GET_root():
    return send_from_directory('web/app-dist', 'index.html')


@server.route('/<path:path>')
def GET_doc(path):
    return send_from_directory('web/app-dist', path)


def setup():
    # Make sure the photo directory exists.
    if not os.path.isdir(SAVE_DIR):
        os.makedirs(SAVE_DIR)

    # Run the web server in a separate thread.
    thread.start_new_thread(server.run, (), {'host': '0.0.0.0'})


def main():
    client = ParadropClient()

    save_prefix = os.path.join(SAVE_DIR, "camera-")

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

            fileName = "{}-{}.jpg".format(save_prefix, int(time.time()))
            img.save(fileName)
            print("Saved image: {}".format(fileName))

        time.sleep(m_sec)


if __name__ == "__main__":
    setup()
    main()
