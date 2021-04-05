import csv
import datetime

sharingLocationUser = {}
lastShareLocation = {}

def setLastShareLocation(user):
    lastShareLocation[user.id] = datetime.datetime.now()

def setSharingLocationUser(user):
    setLastShareLocation(user)
    sharingLocationUser[user.id] = True

def isLastShareLocationMoreThan15(user):
    lastShareTime = datetime.datetime.now() - lastShareLocation[user.id]
    return lastShareTime > datetime.timedelta(minutes=15)

def isUserSharingLocation(user):
    return user.id in sharingLocationUser

def saveUserDataToExcel(user):
    print("Save user")
    with open("./db/allUser.csv".format(user.id), 'a+') as file:
        writer = csv.writer(file)
        writer.writerow(user.toExcelRow())
    return True

def saveLocationToExcel(user):
    print("Writing location")
    with open("./db/fishing-{}.csv".format(user.id), 'a+') as file:
        writer = csv.writer(file)
        writer.writerow([datetime.datetime.now(), user.id, user.lat, user.long])
    return True
