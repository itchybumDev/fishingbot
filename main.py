import configparser
import logging
import os
import sys
from datetime import datetime

import telegram
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from httplib2 import Http
from oauth2client.service_account import ServiceAccountCredentials
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, ReplyKeyboardRemove
from telegram.ext import MessageHandler, Filters, run_async
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, ConversationHandler

from FishingService import saveLocationToExcel, saveUserDataToExcel, setSharingLocationUser, isUserSharingLocation, \
    isLastShareLocationMoreThan15, FISH_CATEGORIES
from messages import *
from model.User import User

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

config = configparser.ConfigParser()
config.read('config.ini')

START, JOIN, IHAVEAFISH, UPLOADPHOTO, CHOOSECATEGORIES, \
RECEIVECATEGORIES, WHATFISHISIT, RECEIVERELEASEVIDEO, RECEIVEDETAILS = range(9)


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
    file_type = file.file_path.split('.')[-1]
    file.download(
        '{}-{}-{}.{}'.format(update.effective_user.name, update.effective_user.id,
                             datetime.timestamp(datetime.now()), file_type))

    kb = []
    for i in range(0, 4):
        index1 = i * 2
        index2 = i * 2 + 1
        kb.append([telegram.KeyboardButton(text=FISH_CATEGORIES[index1]),
                   telegram.KeyboardButton(text=FISH_CATEGORIES[index2])])

    kb_markup = telegram.ReplyKeyboardMarkup(kb)
    context.bot.send_message(update.effective_chat.id,
                             text=ChooseFishCategories,
                             parse_mode=telegram.ParseMode.MARKDOWN,
                             reply_markup=kb_markup)

    return RECEIVECATEGORIES


@run_async
def receiveCategories(update, context):
    # deleteMessage(update, context, 1)
    fishCategory = update.message.text_markdown

    if fishCategory == FISH_CATEGORIES[-1]:
        context.bot.send_message(update.effective_chat.id,
                                 text=WhatFishIsIt,
                                 parse_mode=telegram.ParseMode.MARKDOWN,
                                 reply_markup=ReplyKeyboardRemove())
        return WHATFISHISIT

    print("Got the category")
    print(fishCategory)

    context.bot.send_message(update.effective_chat.id,
                             text=CouldYouProvideFishMeasurentsMsg,
                             parse_mode=telegram.ParseMode.MARKDOWN,
                             reply_markup=ReplyKeyboardRemove())
    return RECEIVEDETAILS


@run_async
def whatFishIsIt(update, context):
    # deleteMessage(update, context, 0)
    fishDetails = update.message.text_markdown
    print("Got the fish category")
    print(fishDetails)

    context.bot.send_message(update.effective_chat.id,
                             text=CouldYouProvideFishMeasurentsMsg,
                             parse_mode=telegram.ParseMode.MARKDOWN,
                             reply_markup=ReplyKeyboardRemove())

    return RECEIVEDETAILS

@run_async
def receiveDetails(update, context):
    # deleteMessage(update, context, 2)
    fishDetails = update.message.text_markdown

    print("getting fish detail here")
    print(fishDetails)

    context.bot.send_message(update.effective_chat.id,
                             text=CouldYouUploadAVideoToShowYouReleaseTheFish,
                             parse_mode=telegram.ParseMode.MARKDOWN)
    return RECEIVERELEASEVIDEO


@run_async
def receiveReleaseVideo(update, context):
    # deleteMessage(update, context, 2)
    file = context.bot.getFile(update.message.video.file_id)
    # mime_type =
    print("video_id: " + str(file.file_id))
    file_type = file.file_path.split('.')[-1]
    file.download(
        '{}-{}-video-{}.{}'.format(update.effective_user.name, update.effective_user.id, datetime.timestamp(datetime.now()), file_type))

    keyboard = [[InlineKeyboardButton(CaughtAFishMsg, callback_data=str('caught'))],
                [InlineKeyboardButton('Quit', callback_data=str('quit'))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(update.effective_chat.id,
                             text=ThanksForSubmittingTheVideo,
                             parse_mode=telegram.ParseMode.MARKDOWN,
                             reply_markup=reply_markup)
    return IHAVEAFISH


@run_async
def quit(update, context):
    query = update.callback_query
    query.answer()
    query.edit_message_text(QuitMsg)
    return ConversationHandler.END


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

    script_path = os.path.dirname(os.path.realpath(__file__))
    localDir = os.path.join(script_path, "db")
    for x in os.listdir(localDir):
        print("Uploading {}".format(os.path.join(localDir, x)))
        file_metadata = {
            'name': x,
            'parents': [folderId]}
        media = MediaFileUpload(os.path.join(localDir, x), mimetype='image/jpeg')
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
            RECEIVECATEGORIES: [MessageHandler(Filters.text, receiveCategories),
                                CallbackQueryHandler(quit, pattern='^quit$')],
            WHATFISHISIT: [MessageHandler(Filters.text, whatFishIsIt),
                           CallbackQueryHandler(quit, pattern='^quit$')],
            RECEIVEDETAILS: [MessageHandler(Filters.text, receiveDetails),
                             CallbackQueryHandler(quit, pattern='^quit$')],
            RECEIVERELEASEVIDEO: [MessageHandler(Filters.video, receiveReleaseVideo),
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
