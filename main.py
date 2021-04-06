import configparser
import logging
import sys
from datetime import datetime
import os
import sys
import time

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from httplib2 import Http
from oauth2client.service_account import ServiceAccountCredentials

import telegram
from oauth2client.service_account import ServiceAccountCredentials
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import MessageHandler, Filters, run_async
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, ConversationHandler

from FishingService import saveLocationToExcel, saveUserDataToExcel, setSharingLocationUser, isUserSharingLocation, isLastShareLocationMoreThan15
from model.User import User
from messages import *

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

config = configparser.ConfigParser()
config.read('config.ini')

START, JOIN, IHAVEAFISH, UPLOADPHOTO, GETDETAILS = range(5)


def send_edit_text(query, text):
    query.edit_message_text(text, parse_mode=telegram.ParseMode.MARKDOWN)


@run_async
def start(update, context):
    currUser = User(update.effective_user.first_name,
                    update.effective_user.full_name,
                    update.effective_user.id,
                    update.effective_user.is_bot,
                    update.effective_user.last_name,
                    update.effective_user.name)
    saveUserDataToExcel(currUser)

    keyboard = []
    keyboard.append([InlineKeyboardButton("Next", callback_data=str('next'))])

    reply_markup = InlineKeyboardMarkup(keyboard)
    # Send message with text and appended InlineKeyboard
    update.message.reply_text(
        text=StartMsg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    # Tell ConversationHandler that we're in state `FIRST` now
    return JOIN


@run_async
def getLocation(update, context):
    currUser = User(update.effective_user.first_name,
                    update.effective_user.full_name,
                    update.effective_user.id,
                    update.effective_user.is_bot,
                    update.effective_user.last_name,
                    update.effective_user.name)
    message = None
    if update.edited_message:
        message = update.edited_message
    else:
        message = update.message
    current_pos = (message.location.latitude, message.location.longitude)
    currUser.setLocation(message.location.latitude, message.location.longitude)

    print(current_pos)
    setSharingLocationUser(currUser)
    saveLocationToExcel(currUser)


@run_async
def joined(update, context):
    currUser = User(update.effective_user.first_name,
                    update.effective_user.full_name,
                    update.effective_user.id,
                    update.effective_user.is_bot,
                    update.effective_user.last_name,
                    update.effective_user.name)
    query = update.callback_query
    query.answer()

    context.bot.delete_message(update.effective_chat.id, query.message.message_id)

    if not isUserSharingLocation(currUser):
        keyboard = [[InlineKeyboardButton('Next', callback_data=str('next'))]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(update.effective_chat.id,
                                 text=NotSharedLocationPleaseShareMsg,
                                parse_mode=telegram.ParseMode.MARKDOWN,
                                reply_markup=reply_markup)
        return JOIN

    keyboard = [[InlineKeyboardButton(CaughtAFishMsg, callback_data=str('caught'))],
                [InlineKeyboardButton('Quit', callback_data=str('quit'))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(update.effective_chat.id,
                             text=YouMayBeginYourCatchMsg,
                             parse_mode=telegram.ParseMode.MARKDOWN,
                             reply_markup=reply_markup)
    return IHAVEAFISH


@run_async
def reportAFish(update, context):
    query = update.callback_query
    query.answer()
    context.bot.delete_message(update.effective_chat.id, query.message.message_id)

    # Check if the user is still logged in
    currUser = User(update.effective_user.first_name,
                    update.effective_user.full_name,
                    update.effective_user.id,
                    update.effective_user.is_bot,
                    update.effective_user.last_name,
                    update.effective_user.name)
    if (isLastShareLocationMoreThan15(currUser)):
        keyboard = []
        keyboard.append([InlineKeyboardButton("Next", callback_data=str('next'))])

        reply_markup = InlineKeyboardMarkup(keyboard)
        # Send message with text and appended InlineKeyboard
        context.bot.send_message(update.effective_chat.id,
            text=YourLiveLocationExpiredMsg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        # Tell ConversationHandler that we're in state `FIRST` now
        return JOIN

    keyboard = [[InlineKeyboardButton('Quit', callback_data=str('quit'))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(update.effective_chat.id,
                            text=CongratulationsOnCaughtMsg,
                            parse_mode=telegram.ParseMode.MARKDOWN,
                            reply_markup=reply_markup)
    return UPLOADPHOTO


@run_async
def receivePhoto(update, context):
    file = context.bot.getFile(update.message.photo[-1].file_id)
    print("file_id: " + str(file.file_id))
    file.download('{}-{}-{}.jpg'.format(update.effective_user.name,update.effective_user.id, datetime.timestamp(datetime.now())))

    context.bot.send_message(update.effective_chat.id,
                            text=CouldYouProvideFishMeasurentsMsg,
                            parse_mode=telegram.ParseMode.MARKDOWN)

    return GETDETAILS


@run_async
def receiveDetails(update, context):
    deleteMessage(update, context, 2)
    fishDetails = update.message.text_markdown

    print("getting fish detail here")
    print(fishDetails)

    keyboard = [[InlineKeyboardButton(CaughtAFishMsg, callback_data=str('caught'))],
                [InlineKeyboardButton('Quit', callback_data=str('quit'))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(update.effective_chat.id,
                             text=ThanksForSubmittingFishDetailsMsg,
                             parse_mode=telegram.ParseMode.MARKDOWN,
                             reply_markup=reply_markup)
    return IHAVEAFISH


@run_async
def quit(update, context):
    query = update.callback_query
    query.answer()
    query.edit_message_text(QuitMsg)
    return ConversationHandler.END\


@run_async
def uploadDb(update, context):
    print("uploading db to google drive")
    scopes = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive.appdata']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scopes)
    http_auth = credentials.authorize(Http())
    drive = build('drive', 'v3', http=http_auth)
    uploadFile(drive)

def uploadFile(drive):
    folderId = "1hsl-O9SnyRCrOCKTSswoBjGu1K0XEB_a"
    localDir = './db'
    for x in os.listdir(localDir):
        print("Uploading {}".format(localDir + '/' + x))
        file_metadata = {
            'name': localDir + '/' + x,
            'parents': [folderId]}
        media = MediaFileUpload(x, mimetype='image/jpeg')
        file = drive.files().create(body=file_metadata,
                                    media_body=media,
                                    fields='id').execute()
        print('Uploaded DB File ID: %s' % file.get('id'))



def main():
    # ad.startAdmin()
    updater = Updater(config['telegram']['token_dev'], use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start, pass_args=True)],
        states={
            START: [MessageHandler(Filters.text, start)],
            JOIN: [CallbackQueryHandler(joined, pattern='^next$')],
            IHAVEAFISH: [CallbackQueryHandler(reportAFish, pattern='^caught$'),
                         CallbackQueryHandler(quit, pattern='^quit$')],
            UPLOADPHOTO: [MessageHandler(Filters.photo, receivePhoto),
                          CallbackQueryHandler(quit, pattern='^quit$')],
            GETDETAILS: [MessageHandler(Filters.text, receiveDetails),
                         CallbackQueryHandler(quit, pattern='^quit$')],
        },
        fallbacks=[CommandHandler('start', start)]
    )

    location_handler = MessageHandler(Filters.location, getLocation)

    dp.add_handler(conv_handler)
    dp.add_handler(location_handler)
    dp.add_handler(CommandHandler('uploadDb', uploadDb, pass_args=True))

    # dp.add_error_handler(error_handler)
    updater.start_polling(poll_interval=1.0, timeout=20)
    updater.idle()


def deleteMessage(update, context, previous=0):
    currNumb = update.message.message_id
    for i in range(currNumb, previous * -1 + currNumb - 1, -1):
        try:
            context.bot.delete_message(chat_id=update.message.chat.id, message_id=i)
        except:
            logger.error('Cannot delete message for chat')


if __name__ == '__main__':
    logger.info("Starting Bot")
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Terminated using Ctrl + C")
    logger.info("Exiting Bot")
    sys.exit()
