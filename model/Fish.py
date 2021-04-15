# State [Done, Unassigned, Assigned]
from datetime import datetime


class Fish:
    def __init__(self, photoId, category, description, videoId):
        self.photoId = photoId
        self.category = category
        self.description = description
        self.videoId = videoId

    def setPhotoId(self, photoId):
        self.photoId = photoId

    def setCategory(self, category):
        self.category = category

    def setDescription(self, description):
        self.description = description

    def setVideoId(self, videoId):
        self.videoId = videoId

    def toExcelRow(self):
        return [self.photoId, self.category, self.description, self.videoId]
