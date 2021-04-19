import csv
import datetime

sharingLocationUser = {}
lastShareLocation = {}
FISH_CATEGORIES = ['Groupers/Kerapu', 'Snappers/Jenahak', 'Sharks/Ikan Yu', 'Rays/Ikan Pari', 'Others/Lain']


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
    with open("./db/{}-{}.csv".format(user.name, user.id), 'a+') as file:
        writer = csv.writer(file)
        writer.writerow([datetime.datetime.now(), user.name, user.id, user.lat, user.long])
    return True


def saveFishToExcel(user, fish):
    print("Writing Fish details")
    with open("./db/{}-{}-fish.csv".format(user.name, user.id), 'a+') as file:
        writer = csv.writer(file)
        writer.writerow(fish.toExcelRow())

    with open("./db/allUser-fish.csv".format(user.name, user.id), 'a+') as file:
        writer = csv.writer(file)
        writer.writerow(fish.toExcelRow())
    return True
