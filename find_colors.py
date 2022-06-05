import binascii

import numpy as np
import scipy.cluster
from PIL import Image


class FindColors:
    """Finds the most used colors in an image as well as the dominant color"""

    def __init__(self, file):
        self.file = file
        self.NUM_CLUSTERS = 10
        self.ar = None
        self.codes = None
        self.read_image()
        self.find_colors()
        self.find_dominant_color()

    def read_image(self):
        """Reads image file and prepares it for processing"""
        im = Image.open(self.file).resize((150, 150))
        self.ar = np.asarray(im)
        shape = self.ar.shape
        self.ar = self.ar.reshape(np.product(shape[:2]), shape[2]).astype(float)
        return self.ar

    def find_colors(self, number_of_colors=10):
        """Extracts n amount of dominant colors from image, if none specified, extracts 10
        returned as a string with the rgb and html codes"""
        self.NUM_CLUSTERS = number_of_colors
        colors = []
        self.codes, distance = scipy.cluster.vq.kmeans(self.ar, self.NUM_CLUSTERS)
        for _ in self.codes:
            color = binascii.hexlify(bytearray(int(x) for x in _)).decode('ascii')
            color = "%s (#%s)" % (_, color)
            colors.append(color)
        return colors

    def find_dominant_color(self):
        """Finds the dominant color in an image"""
        vecs, distance = scipy.cluster.vq.vq(self.ar, self.codes)
        counts, bins = np.histogram(vecs, len(self.codes))
        max_index = np.argmax(counts)
        peak = self.codes[max_index]
        color = binascii.hexlify(bytearray(int(x) for x in peak)).decode('ascii')
        return "%s (#%s)" % (peak, color)


