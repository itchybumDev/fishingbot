# State [Done, Unassigned, Assigned]
from datetime import datetime

class User:
    def __init__(self, first_name, full_name, id, is_bot, last_name, name):
        self.first_name = first_name
        self.full_name = full_name
        self.id = id
        self.is_bot = is_bot
        self.last_name = last_name
        self.name = name
        self.created_on = datetime.today()
        self.modifiedOn = datetime.today()
        self.isLocationShared = False
        self.lat = 0
        self.long = 0

    def locationIsNowShared(self):
        self.isLocationShared = True

    def setLocation(self, lat, long):
        self.lat = lat
        self.long = long

    def toString(self):
        return 'User {} - {} - {} - {} - {} - {} - {} - {}'.format(self.first_name, self.full_name, self.id, self.is_bot, self.last_name, self.name)

    def toExcelRow(self):
        return [self.first_name, self.full_name, self.id, self.is_bot, self.last_name, self.name, self.created_on, self.modifiedOn]