import os
import sys
import time
import csv

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from httplib2 import Http
from oauth2client.service_account import ServiceAccountCredentials

user_folder = {}
uploaded_files = []

ROOT_FOLDER = '1Fe2z7g0A7GYmSd3PmiwaJl4y6M1ZxEu0'

def getAllAvailableFolders(drive):
    global user_folder
    global uploaded_files

    request = drive.files().list(q="'{}' in parents and mimeType = 'application/vnd.google-apps.folder'".format(ROOT_FOLDER)).execute()
    folders = request.get('files', [])
    for f in folders:
        user_folder[f['name']] = f['id']

    request = drive.files().list(q="mimeType != 'application/vnd.google-apps.folder'").execute()
    files = request.get('files', [])
    for f in files:
        uploaded_files.append(f['name'])


def shareFolder(drive, fileId):
    # All folder
    def callback(request_id, response, exception):
        if exception:
            # Handle error
            print
            exception
        else:
            print
            "Permission Id: %s" % response.get('id')

    batch = drive.new_batch_http_request(callback=callback)
    user_permission = {
        'type': 'user',
        'role': 'writer',
        'emailAddress': 'botfishing2021@gmail.com'
    }
    batch.add(drive.permissions().create(
        fileId=fileId,
        body=user_permission,
        fields='id',
    ))
    print("Done Granting permission")
    batch.execute()


def createFolder(drive, folderName):
    folder_metadata = {
        'name': folderName,
        'parents': [ROOT_FOLDER],
        'mimeType': 'application/vnd.google-apps.folder'
    }
    file = drive.files().create(body=folder_metadata,
                                fields='id').execute()
    print('Folder ID: %s' % file.get('id'))
    return file.get('id')

def print_files_in_folder(drive, folder_id):
    """Print files belonging to a folder.

  Args:
    service: Drive API service instance.
    folder_id: ID of the folder to print files from.
  """
    page_token = None
    while True:
        try:
            param = {}
            if page_token:
                param['pageToken'] = page_token
            children = drive.children().list(
                folderId=folder_id, **param).execute()

            for child in children.get('items', []):
                print('File Id: %s' % child['id'])
            page_token = children.get('nextPageToken')
            if not page_token:
                break
        except HttpError as error:
            print('An error occurred: {}'.format(error))
            break


def getParentFolderId(drive, x):
    folderName = "-".join(x.split('-')[:2])
    folderName = folderName.replace(".csv", '')
    print("Saving to folder " + folderName)
    if folderName not in user_folder:
        folderId = createFolder(drive, folderName)
        user_folder[folderName] = folderId
    else:
        folderId = user_folder.get(folderName)
    return folderId


def main():
    scopes = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive.appdata']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scopes)
    http_auth = credentials.authorize(Http())
    drive = build('drive', 'v3', http=http_auth)

    getAllAvailableFolders(drive)

    for x in os.listdir('.'):
        if 'jpg' in x.lower() or 'jpeg' in x.lower() or 'png' in x.lower():
            p_folderId = getParentFolderId(drive, x)
            uploadPhotoFile(drive, p_folderId, x)
        else:
            print("Not uploading {}".format(x))

    build_all_lat_long_file()

    uploadFile(drive)


def build_all_lat_long_file():
    script_path = os.path.dirname(os.path.realpath(__file__))
    localDir = os.path.join(script_path, "db")
    for x in os.listdir(localDir):
        if "allUser" in x or "fish" in x:
            print("not lat long file " + x)
        else:
            data = None
            with open(os.path.join(localDir, x), newline='') as f:
                reader = csv.reader(f)
                data = list(reader)
            row_to_write = data[-1]
            with open("./db/allUser-latlong.csv", 'a+') as file:
                writer = csv.writer(file)
                writer.writerow(row_to_write)



def uploadPhotoFile(drive, p_folderId, x):
    if x in uploaded_files:
        print("{} is already uploaded".format(x))
        return

    print("Uploading {}".format(x))
    file_metadata = {
        'name': x,
        'parents': [p_folderId]}
    media = MediaFileUpload(x, mimetype='image/jpeg')
    file = drive.files().create(body=file_metadata,
                                media_body=media,
                                fields='id').execute()
    uploaded_files.append(x)
    print('File ID: %s' % file.get('id'))

def deleteFileOnDriveUnderDb(drive):
    folderId = "1hsl-O9SnyRCrOCKTSswoBjGu1K0XEB_a"
    request = drive.files().list(q="'{}' in parents".format(folderId)).execute()
    files = request.get('files', [])
    for f in files:
        drive.files().delete(fileId=f['id']).execute()


def deleteSameFileUnderFolder(drive, folderId, fileName):
    request = drive.files().list(q="'{}' in parents".format(folderId)).execute()
    files = request.get('files', [])
    for f in files:
        if fileName in f['name']:
            drive.files().delete(fileId=f['id']).execute()


def uploadFile(drive):

    script_path = os.path.dirname(os.path.realpath(__file__))
    localDir = os.path.join(script_path, "db")
    for x in os.listdir(localDir):
        print("Uploading {}".format(os.path.join(localDir, x)))

        if 'allUser' not in x:
            folderId = getParentFolderId(drive, x)
        else:
            # "db" folder on google drive
            folderId = "1hsl-O9SnyRCrOCKTSswoBjGu1K0XEB_a"

        deleteSameFileUnderFolder(drive, folderId, x)

        file_metadata = {
            'name': x,
            'parents': [folderId]}
        media = MediaFileUpload(os.path.join(localDir, x), mimetype='text/csv')
        file = drive.files().create(body=file_metadata,
                                    media_body=media,
                                    fields='id').execute()
        print('Uploaded DB File ID: %s' % file.get('id'))


if __name__ == '__main__':
    print("Starting Bot")
    try:
        while True:
            main()
            time.sleep(1800)
    except KeyboardInterrupt:
        print("Terminated using Ctrl + C")
    print("Exiting Bot")
    sys.exit()
