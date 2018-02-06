import operator
import os
import re

from datetime import datetime
from functools import wraps, update_wrapper

from flask import Flask, jsonify, make_response, send_from_directory


PARADROP_DATA_DIR = os.environ.get("PARADROP_DATA_DIR", "/tmp")

PHOTO_NAME_RE = re.compile(r"\w+\-(\d+)\.jpg")
SAVE_DIR = os.path.join(PARADROP_DATA_DIR, "photos")
STATUS_DIR = os.path.join(PARADROP_DATA_DIR, "status")
MAX_LATEST = 40

server = Flask(__name__)


def nocache(view):
    @wraps(view)
    def no_cache(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Last-Modified'] = datetime.now()
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response
    return update_wrapper(no_cache, view)


#@server.route('/status')
#@nocache
#def GET_latest():
#    return send_from_directory(STATUS_DIR, 'latest.json')


@server.route('/status/<path:path>')
@nocache
def GET_status(path):
    return send_from_directory(STATUS_DIR, path)


@server.route('/photos')
@nocache
def GET_photos():
    photos = []
    for fname in os.listdir(SAVE_DIR):
        match = PHOTO_NAME_RE.match(fname)
        if match is None:
            continue

        ts = match.group(1)
        try:
            ts = float(ts)
        except ValueError:
            pass

        photos.append({
            'path': os.path.join('/photos', fname),
            'ts': ts
        })

    photos.sort(key=operator.itemgetter('ts'), reverse=True)
    return jsonify(photos[:MAX_LATEST])


@server.route('/photos/<path:path>')
def GET_photo(path):
    return send_from_directory(SAVE_DIR, path)


@server.route('/')
def GET_root():
    return send_from_directory('web/app-dist', 'index.html')


@server.route('/<path:path>')
def GET_doc(path):
    return send_from_directory('web/app-dist', path)
