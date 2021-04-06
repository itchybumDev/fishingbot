import configparser
import logging
import sys
from datetime import datetime

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import MessageHandler, Filters
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, ConversationHandler

from FishingService import saveLocationToExcel, saveUserDataToExcel, setSharingLocationUser, isUserSharingLocation, isLastShareLocationMoreThan15
from model.User import User

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

config = configparser.ConfigParser()
config.read('config.ini')

START, JOIN, IHAVEAFISH, UPLOADPHOTO, GETDETAILS = range(5)


def send_edit_text(query, text):
    query.edit_message_text(text, parse_mode=telegram.ParseMode.MARKDOWN)


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
        u"Please share live location then pressed next.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    # Tell ConversationHandler that we're in state `FIRST` now
    return JOIN


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
                                 text='You have not share your location, please share location and click next',
                                parse_mode=telegram.ParseMode.MARKDOWN,
                                reply_markup=reply_markup)
        return JOIN

    keyboard = [[InlineKeyboardButton('Caught a fish', callback_data=str('caught'))],
                [InlineKeyboardButton('Quit', callback_data=str('quit'))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(update.effective_chat.id,
                             text='Great, you may begin your catch & release journey',
                             parse_mode=telegram.ParseMode.MARKDOWN,
                             reply_markup=reply_markup)
    return IHAVEAFISH


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
            text=u"Your live location seems to expired.\nPlease share live location then pressed next.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        # Tell ConversationHandler that we're in state `FIRST` now
        return JOIN

    keyboard = [[InlineKeyboardButton('Quit', callback_data=str('quit'))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(update.effective_chat.id,
                            text='Congratulations on your catch. Please upload a photo of the fish',
                            parse_mode=telegram.ParseMode.MARKDOWN,
                            reply_markup=reply_markup)
    return UPLOADPHOTO


def receivePhoto(update, context):
    file = context.bot.getFile(update.message.photo[-1].file_id)
    print("file_id: " + str(file.file_id))
    file.download('{}-{}-{}.jpg'.format(update.effective_user.name,update.effective_user.id, datetime.timestamp(datetime.now())))

    context.bot.send_message(update.effective_chat.id,
                            text='That is one great looking fish. Could you provide some measurements?',
                            parse_mode=telegram.ParseMode.MARKDOWN)

    context.bot.send_message(update.effective_chat.id,
                             text='Size: <insert here>',
                             parse_mode=telegram.ParseMode.MARKDOWN)
    return GETDETAILS


def receiveDetails(update, context):
    deleteMessage(update, context, 2)
    fishDetails = update.message.text_markdown

    print("getting fish detail here")
    print(fishDetails)

    keyboard = [[InlineKeyboardButton('Caught a fish', callback_data=str('caught'))],
                [InlineKeyboardButton('Quit', callback_data=str('quit'))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(update.effective_chat.id,
                             text='Thanks for the details. Lets get out there and fish more.',
                             parse_mode=telegram.ParseMode.MARKDOWN,
                             reply_markup=reply_markup)
    return IHAVEAFISH

def quit(update, context):
    query = update.callback_query
    query.answer()
    query.edit_message_text("Thanks for using fishing bot. Press /start again to join back")
    return ConversationHandler.END

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
