import cv2
import os
import pickle
import time

from operator import itemgetter

import numpy as np
import pandas as pd

import openface

from sklearn.pipeline import Pipeline
from sklearn.lda import LDA
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import SVC
from sklearn.grid_search import GridSearchCV
from sklearn.mixture import GMM
from sklearn.tree import DecisionTreeClassifier
from sklearn.naive_bayes import GaussianNB


clfChoices = [
    'LinearSvm',
    'RadialSvm',
    'GaussianNB',
    'Forest',
    'Logic',
]


np.set_printoptions(precision=2)


class FaceClassifier(object):
    def __init__(self, dlibFacePredictor, classifierModel, networkModel, imgDim, cuda):
        self.imgDim = imgDim
        self.classifierModel = classifierModel
        self.start = time.time()

        self.align = openface.AlignDlib(dlibFacePredictor)
        self.net = openface.TorchNeuralNet(networkModel, imgDim, cuda)

    def getRep(self, imgPath):
        start = time.time()
        bgrImg = cv2.imread(imgPath)
        if bgrImg is None:
            raise Exception("Unable to load image: {}".format(imgPath))

        rgbImg = cv2.cvtColor(bgrImg, cv2.COLOR_BGR2RGB)

        self.start = time.time()

        bbs = self.align.getAllFaceBoundingBoxes(rgbImg)
        if bbs is None:
            return None

        reps = []
        for bb in bbs:
            self.start = time.time()
            alignedFace = self.align.align(
                self.imgDim,
                rgbImg,
                bb,
                landmarkIndices=openface.AlignDlib.OUTER_EYES_AND_NOSE)
            if alignedFace is None:
                raise Exception("Unable to align image: {}".format(imgPath))

            self.start = time.time()
            rep = self.net.forward(alignedFace)
            reps.append((bb.center().x, rep))

        print("Found {} faces".format(len(reps)))
        return (reps, bbs)

    def infer(self, imgPath, multiple=False):
        scores = []
        people = []
        bbs = []

        modelPath = os.path.join("chute", self.classifierModel)
        with open(modelPath, 'r') as f:
            (le, clf) = pickle.load(f)

        try:
            reps, bbs = self.getRep(imgPath)

            if len(reps) > 1:
                print("List of faces in image from left to right")

            for r in reps:
                rep = r[1].reshape(1, -1)
                bbx = r[0]
                self.start = time.time()
                predictions = clf.predict_proba(rep).ravel()
                maxI = np.argmax(predictions)
                person = le.inverse_transform(maxI)
                confidence = predictions[maxI]

                if(confidence < 0.5 ):
                    person = 'Unknown'
                    confidence = 100

                scores.append(confidence)
                people.append(person)
                print("Predict {} with {:.2f} confidence.".format(person, confidence))

            return people, scores, bbs

#                if multiple:
#                    print("Predict {} @ x={} with {:.2f} confidence.".format(person, bbx, confidence))
#                else:
#                    scores.append(confidence)
#                    people.append(person)
#                    print("Predict {} with {:.2f} confidence.".format(person, confidence))
#                    return scores, people
#
#                if isinstance(clf, GMM):
#                    dist = np.linalg.norm(rep - clf.means_[maxI])
#                    print("  + Distance from the mean: {}".format(dist))

        except Exception as e:
            print('!! Warning: %s' % str(e))
            return people, scores, bbs


    def inferMulti(self, imgPath):
        scores = []
        people = []
        threshold = -1;
        votes = {}

        for clfChoice in clfChoices:
            print "\n==============="
            print "Using the classifier: " + clfChoice

            with open(os.path.join(self.classifierModel, clfChoice + ".pkl"), 'r') as f_clf:
                (le, clf) = pickle.load(f_clf)

            try:
                reps = self.getRep(imgPath, False)
                rep = reps[0][1].reshape(1, -1)
            except Exception as e:
                print('!! Warning: %s' % str(e))
                return scores, people

            predictions = clf.predict_proba(rep).ravel()
            maxI = np.argmax(predictions)
            person = le.inverse_transform(maxI)
            confidence = predictions[maxI]

            print person, confidence

            if clfChoice == 'LinearSvm':
                threshold = 0.45
            elif clfChoice == 'RadialSvm':  # Radial Basis Function kernel
                threshold = 0.4
            elif clfChoice == 'GaussianNB':
                threshold = 0.9
            elif clfChoice == 'Forest':
                threshold = 0.55
            elif clfChoice == 'Logic':
                threshold = 0.5

            if(confidence < threshold ):
                person = 'Unknown'

            cnt = votes.get(person)
            if(cnt is None):
                votes[person] = 1
            else:
                votes[person] = cnt + 1

        # get majority vote
        maxNum = -1;
        maxName= None;
        for name, num in votes.iteritems():
            if (num > maxNum):
                maxNum = num
                maxName = name

        print maxName, maxNum

        if(maxNum < (len(clfChoices)+1)/2):
            maxName = 'Unknown'
            maxNum  = len(clfChoices) - maxNum

        scores.append( float (maxNum)/ len(clfChoices))
        people.append(maxName)

        print votes
        return scores, people

    def label(self, imgPath, newPath, people, scores, bbs):
        bgrImg = cv2.imread(imgPath)
        if bgrImg is None:
            raise Exception("Unable to load image: {}".format(imgPath))

        rgbImg = cv2.cvtColor(bgrImg, cv2.COLOR_BGR2RGB)

        for idx, person in enumerate(people):
            cv2.rectangle(rgbImg, (bbs[idx].left(), bbs[idx].top()),
                    (bbs[idx].right(), bbs[idx].bottom()), (0, 255, 0), 2)

            cv2.putText(rgbImg, "{} @{:.2f}".format(person, scores[idx]),
                    (bbs[idx].left(), bbs[idx].bottom()+20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        cv2.imwrite(newPath, rgbImg)
