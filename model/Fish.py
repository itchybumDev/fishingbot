# State [Done, Unassigned, Assigned]
from datetime import datetime


class Fish:
    def __init__(self, userId, userName, photoId, category, description, released):
        self.userId = userId
        self.userName = userName
        self.photoId = photoId
        self.category = category
        self.description = description
        self.released = released
        self.createdTimestamp = datetime.now()

    def setPhotoId(self, photoId):
        self.photoId = photoId

    def setCategory(self, category):
        self.category = category

    def setDescription(self, description):
        self.description = description

    def setVideoId(self, videoId):
        self.videoId = videoId

    def toExcelRow(self):
        return [self.userId, self.userName, self.photoId, self.category, self.description, self.released, self.createdTimestamp]
