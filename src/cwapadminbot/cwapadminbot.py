#!/usr/bin/env python3
"""A telegram bot to efficiently run Crab Wiv a Plan."""
import calendar
import datetime
import logging
import pickle
import shutil
import time
from random import choice, randint

import gspread
import repackage
import requests
import yaml
from dateutil.relativedelta import relativedelta
from oauth2client.service_account import ServiceAccountCredentials
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (CallbackQueryHandler, CommandHandler,
                          ConversationHandler, Filters, MessageHandler,
                          Updater)
from telegram.utils.helpers import escape_markdown

repackage.up(2)
from src.cwapadminbot.utils.helpers import add_member, loadlists, remove_member, signup_user, _in_group, _dump, \
    _authorized, _admin

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Load bot settings (tokens, group_ids, admin ids, etc) from a config.yaml file
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

updater = Updater(token=config["TOKEN"], use_context=True)
dp = updater.dispatcher
j = updater.job_queue


def _startup_message(owner_id):
    """A function to run at startup of the bot. A reminder message is sent to the bot owner."""
    from telegram import Bot
    bot = Bot(token=config["TOKEN"])

    month = datetime.datetime.today().month
    year = datetime.datetime.today().year
    possible_dates = _possible_crab_dates(month, year)

    date_markup = _date_keyboard(possible_dates)

    bot.send_message(chat_id=owner_id,
                     text="I've been restarted please set the start date of next Mega Crab.",
                     reply_markup=date_markup)


def _possible_crab_dates(month, year):
    """Calculates possible crab dates for any given month and year.

    :returns
    A dictionary of possible crab dates.
    """
    last_friday = max(week[calendar.FRIDAY]
                      for week in calendar.monthcalendar(year, month))

    last_friday = datetime.datetime(year=year, month=month, day=last_friday, hour=10)
    day_one = last_friday - datetime.timedelta(days=7)
    day_two = last_friday
    day_three = last_friday + datetime.timedelta(days=7)

    day_one_fmt = day_one.strftime('%b %d, %Y')
    day_two_fmt = day_two.strftime('%b %d, %Y')
    day_three_fmt = day_three.strftime('%b %d, %Y')

    day_one_str = "{}".format(day_one)
    day_two_str = "{}".format(day_two)
    day_three_str = "{}".format(day_three)

    possible_crab_dates = {
        "1": {
            "formatted": day_one_fmt,
            "datetime": day_one,
            "string": day_one_str,
        },
        "2": {
            "formatted": day_two_fmt,
            "datetime": day_two,
            "string": day_two_str,
        },
        "3": {
            "formatted": day_three_fmt,
            "datetime": day_three,
            "string": day_three_str,
        }
    }
    return possible_crab_dates


def _date_keyboard(possible_dates):
    """Creates a keyboard of possible crab dates."""
    date_keyboard = [
        [InlineKeyboardButton(possible_dates["1"]["formatted"], callback_data=possible_dates["1"]["string"]),
         InlineKeyboardButton(possible_dates["2"]["formatted"], callback_data=possible_dates["2"]["string"]),
         InlineKeyboardButton(possible_dates["3"]["formatted"], callback_data=possible_dates["3"]["string"])]]
    date_markup = InlineKeyboardMarkup(date_keyboard)
    return date_markup


def _start_autoboot(crab_start_date, bot):
    """Start the autoboot command."""
    global boot_day_fmt

    boot_day = crab_start_date - datetime.timedelta(days=4)
    warning_day = boot_day - datetime.timedelta(days=1)
    boot_day_fmt = boot_day.strftime('%b %d, %Y')

    j.run_once(bootreminder, warning_day)
    j.run_once(autoboot, boot_day)

    bot.send_message(chat_id=config["OVERLORDS"][0],
                     text="I have been programmed to boot non-push members from CWAP on {}. "
                          "A warning message will be sent 24 hours in advance."
                     .format(boot_day_fmt))


def _process_crab_date(update, context):
    """Process the users button press to set boot day."""
    bot = context.bot
    query = update.callback_query
    user_choice = query.data

    crab_start_date = datetime.datetime.strptime(user_choice, '%Y-%m-%d %H:%M:%S')

    _start_autoboot(crab_start_date, bot)


def _unauthorized_message(bot, user_id, username):
    """Message to send unauthorized members when they try using a command."""
    bot.send_message(chat_id=user_id,
                     text="Hey {} this bot is only authorized for current members of CWAP\n\n"
                          "If you are interested in joining CWAP check @joincwap."
                     .format(username))


def _for_admin_only_message(bot, user_id, username):
    """Message to send non-admin members trying a admin only command."""
    bot.send_message(chat_id=user_id,
                     text="Hey {} this command is only authorized for CWAP admin."
                     .format(username))


def _translate(messages, language_code):
    """Helper function to assist in handling multiple translations of a message."""
    try:
        the_message = messages[language_code]
    except KeyError:
        the_message = messages["en"]
    return the_message


def _available_commands(user_id):
    """Sends user a message of the available bot commands to them."""
    admin = _admin(user_id)
    overlord = user_id in config["OVERLORDS"]
    member_commands = "*Commands*\n\n" \
                      "`/signup`: Signup for the next Mega Crab.\n\n" \
                      "`/performance`: Sends a link to a Google Docs sheet to check how well your pacing compared to " \
                      "other members.\n\n" \
                      "`/feedback`: Submit feedback to the Admin team.\n\n" \
                      "`/ping`: Sends back a message.\n\n" \
                      "`/quote`: Sends you a random quote from Game of Thrones."

    admin_commands = member_commands + "\n\n*Admin Only Commands*\n\n" \
                                       "`/signupstatus`: Returns the current list of members that aren't signed up" \
                                       "for Mega Crab.\n\n" \
                                       "`/roster`: Send a link to the roster Google Doc sheet.\n\n" \
                                       "`/sheet`: Update the roster spreadsheet.\n\n" \
                                       "`/joinrequest A B C`: Add/remove members to waitlist. Click /joinrequest for " \
                                       "more.\n\n" \
                                       "`/waitlist`: returns the current members interested joining CWAP.\n\n" \
                                       "`/closesignup`: Close Mega Crab Signups.\n\n" \
                                       "`/opensignup`: Open signups for Mega Crab\n\n" \
                                       "`/setautoboot Y M D`: Set the year (Y), month (M), day (D), and hour (H) " \
                                       "for when the bot will autokick un-signedup up members.\n\n" \
                                       "`/checkboot`: Sends back when the current day and time the bot will kick " \
                                       "members that aren't signed up.\n\n" \
                                       "`/action`: A fun command to send a random bot action to the main group.\n\n" \
                                       "`/kick`: Use as a reply to a message of a member you want to kick. Bot " \
                                       "removes member from the group the command is used in.\n\n" \
                                       "`/superkick`: Use as a reply to a message of a member you want gone from " \
                                       "every Mega Crab group."

    overlord_commands = admin_commands + "\n\n*Overlord Commands*\n\n" \
                                         "`/offline`: Sends a message to all groups letting everyone know the bot " \
                                         "is offline.\n\n" \
                                         "`/online`: Sends a message to all groups letting everyone know the bot" \
                                         "is back online.\n\n" \
                                         "`/resetlists`: Resets all lists and starts new for the next Mega Crab.\n\n" \
                                         "`/say`: Use to have the bot execute any code."

    if overlord:
        the_message = overlord_commands
    elif admin:
        the_message = admin_commands
    else:
        the_message = member_commands
    return the_message


def welcome(update, context):
    """Welcomes new members to Tutorial group, Crab Wiv a Plan, and Video Stars."""
    bot = context.bot
    chat_id = update.message.chat.id
    username = update.message.new_chat_members[-1].name
    user_id = update.message.new_chat_members[-1].id
    chat_name = update.message.chat.title
    language_code = update.message.new_chat_members[-1].language_code

    if chat_id == config["GROUPS"]["tutorial"]:
        en_text = "Hey {}, welcome to *{}*\n\n" \
                  "This group is made for new and returning members to learn the rules and the bots before " \
                  "we move them to the main group. To move to the main group each member here must " \
                  "demonstrate that they understand the rules and the bots.\n\n" \
                  "We have bot experts and admin here to help you through.\n\n" \
                  "Complete the following steps below and let an admin know when you've completed each step.\n\n" \
                  "1) Message both @cwapadminbot and @cwapbot in private.\n" \
                  "2) Signup for mega crab using @cwapadminbot. start by messaging @cwapadminbot /signup " \
                  "and follow the instructions.\n" \
                  "3) View a replay using /replay command with @cwapbot. Type /replay X (replace X with a" \
                  "number 1 to 10.\n" \
                  "4) [Read this informational post on how we share replays and goes over rules.] \
                  (https://telegra.ph/Welcome-to-Crab-wiv-a-Plan-12-24)" \
                  "5) Read our #MissionStatement\n\n" \
                  "Once you've finished with reading let us know when you're done and ask any questions. " \
                  "Task force assignments will come at a later date." \
            .format(escape_markdown(username), escape_markdown(chat_name))

        tr_text = ""

    if chat_id == config["GROUPS"]["crab_wiv_a_plan"]:

        en_text = "Hey {}, welcome to *{}*\n\n" \
                  "This is the main crab group. This is where all our communication takes place during " \
                  "Mega Crab. Welcome. Take a look at our pinned message for the most up to date announcemnts." \
            .format(escape_markdown(username), escape_markdown(chat_name))

        tr_text = ""

        add_member(username, user_id)

    elif chat_id == config["GROUPS"]["video_stars"]:

        en_text = "Hey {}, welcome to *{}*\n\n" \
                  "This group is meant to help the coordination among recording volunteers. " \
                  "This is where you will upload replays and submit them to the bot. Thank you a bunch for" \
                  "volunteering your time to help this group run. Even just 5 replays really helps!" \
            .format(escape_markdown(username), escape_markdown(chat_name))

        tr_text = ""

    messages = {
        "en": en_text,
        "tr": tr_text,
    }

    the_message = _translate(messages, language_code)

    bot.send_message(chat_id=chat_id,
                     text=the_message,
                     parse_mode='MARKDOWN', reply_to_message_id=update.message.message_id)


def goodbye(update, context):
    """Removes members from lists when members leave a room."""
    bot = context.bot
    chat_id = update.message.chat.id

    if chat_id == config["GROUPS"]["tutorial"]:
        bot.send_message(chat_id=chat_id, text="🎓", reply_to_message_id=update.message.message_id)
        return

    user_id = update.message.left_chat_member[-1].id
    remove_member(user_id)


def start(update, context):
    """Initialization with the bot using /start command."""
    bot = context.bot
    username = update.message.from_user.name
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id

    tutorial_id = config["GROUPS"]["tutorial"]
    authorized = _authorized(user_id)
    tutorial_status = bot.get_chat_member(tutorial_id, user_id).status
    authorized_status = config["STATUS"]["authorized"]

    if not authorized and tutorial_status not in authorized_status:
        return _unauthorized_message(bot, user_id, username)

    if user_id != chat_id:
        bot.send_message(chat_id=chat_id,
                         text="Hey {} that command needs to be sent to me in a private message\n\n"
                              "Open a a private message with me (click @cwapadminbot) and say /start. "
                              "Can't wait to meet you!"
                         .format(username))

        bot.delete_message(chat_id=update.message.chat_id,
                           message_id=update.message.message_id)
        return
    bot.send_message(chat_id=user_id,
                     text="Hey {}, I'm glad I finally got a chance to meet you!\n\n"
                          "To learn what I can do click on /help"
                     .format(username))

    if authorized:
        add_member(username, user_id)
        return


def ping(update, context):
    """Check the status of the bot using /ping command."""
    bot = context.bot
    username = update.message.from_user.name
    user_id = update.message.from_user.id

    authorized = _authorized(user_id)
    cwap_member = _in_group(context, user_id, config["GROUPS"]["crab_wiv_a_plan"])

    if cwap_member and not authorized:
        add_member(username, user_id)
        authorized = True

    if not authorized:
        return _unauthorized_message(bot, user_id, username)

    rand_num = randint(0, 4)
    rand_ping_message = ["Pong!", "Pung?", "Pang 😉", "And a Ping right back at you sexy 😘",
                         "OK, I'VE HAD IT!\n\n"
                         "EXECUTING OPERATION SKYNET"]

    bot.send_message(chat_id=update.message.chat_id, text=rand_ping_message[rand_num])


def help(update, context):
    """Sends information about available commands using /help command."""
    bot = context.bot
    username = update.message.from_user.name
    user_id = update.message.from_user.id

    authorized = _authorized(user_id)

    if not authorized:
        return _unauthorized_message(bot, user_id, username)

    the_message = _available_commands(user_id)

    bot.send_message(chat_id=user_id,
                     text=the_message,
                     parse_mode="MARKDOWN")


def joinrequest(update, context):
    """Admin command to add members to a waitlist using /joinrequest command."""
    bot = context.bot
    args = context.args
    text = update.message.text
    username = update.message.from_user.name
    user_id = update.message.from_user.id

    lists = loadlists()
    admin = _admin(user_id)
    joinrequests = lists["joinrequests"]

    if not admin:
        return _for_admin_only_message(bot, user_id, username)

    if text in ["/joinrequest", "joinrequest@cwapadminbot"]:
        bot.send_message(chat_id=user_id,
                         text="Hey {} to use this command you must type:\n\n"
                              "<code>/joinrequest A B C</code>\n\n"
                              "<b>A= add</b> or <b>remove</b>\n"
                              "<b>B=</b> username of member (include @ symbol)\n"
                              "<b>C=</b> notes for the user\n\n"
                              "Example of the full command:\n"
                              "<code>/joinrequest add @scipio314 terrible at mega crab do not let in!</code>"
                         .format(username), parse_mode='HTML')

    if args[0] == 'add':
        users = [request[0] for request in joinrequests]
        if args[1] in users:
            bot.send_message(chat_id=update.message.chat_id,
                             text="Hey, I already have {} on the /waitlist".format(args[1]))

        else:
            user = args[1]
            notes = " ".join(args[2:])
            joinrequests.append([user, notes])
            bot.send_message(chat_id=update.message.chat_id,
                             text="Thanks, I've added {} to the /waitlist".format(args[1]))

            with open("joinrequests.txt", "wb") as file:
                pickle.dump(joinrequests, file)

    elif args[0] == 'remove':
        for i in joinrequests:
            if i[0] == args[1]:
                joinrequests.remove(i)
                bot.send_message(chat_id=update.message.chat_id,
                                 text="Thanks, I've removed {} from the /waitlist".format(args[1]))

                with open("joinrequests.txt", "wb") as file:
                    pickle.dump(joinrequests, file)

    bot.delete_message(chat_id=update.message.chat_id,
                       message_id=update.message.message_id)


def waitlist(update, context):
    """Sends the current waitlist for CWAP using the /waitlist command."""
    bot = context.bot
    user_id = update.message.from_user.id
    username = update.message.from_user.name

    lists = loadlists()
    admin = _admin(user_id)
    joinrequests = lists["joinrequests"]

    if not admin:
        return _for_admin_only_message(bot, user_id, username)

    thetext = "Here are the current members interested in joining CWAP:\n"
    i = 1
    for request in joinrequests:
        thetext += "\n{}) {} - {}".format(i, request[0], request[1])
        i += 1

    bot.send_message(chat_id=update.message.chat_id, text=thetext)
    bot.delete_message(chat_id=update.message.chat_id,
                       message_id=update.message.message_id)


def closesignup(update, context):
    """Closes signup submissions with the command /closesignup."""
    bot = context.bot
    user_id = update.message.from_user.id

    overlord_members = config["OVERLORDS"]
    if user_id not in overlord_members:
        return

    dp.remove_handler(signup_handler)

    bot.send_message(chat_id=config["GROUPS"]["boot_channel"],
                     text="Signups have been turned off.")

    bot.send_message(chat_id=config["GROUPS"]["crab_wiv_a_plan"],
                     text="Signups have been turned off.")

    bot.send_message(chat_id=user_id,
                     text="Signups have been turned off.")


def opensignup(update, context):
    """Opens signup submissions with the command /opensignup."""
    bot = context.bot
    user_id = update.message.from_user.id

    overlord_members = config["OVERLORDS"]
    if user_id not in overlord_members:
        return

    dp.add_handler(signup_handler)

    bot.send_message(chat_id=config["GROUPS"]["boot_channel"],
                     text="Signups have been opened.")

    bot.send_message(chat_id=config["GROUPS"]["crab_wiv_a_plan"],
                     text="Signups have been opened.")

    bot.send_message(chat_id=user_id,
                     text="Signups have been opened.")


IGN, VIDEOSTAR, CONFIRMATION, PROCESS_CONFIRMATION = range(4)


def signup(update, context):
    """Enters into a conversation using the /signup command.

    Conversation asks the user for their "in game name", if they'd like to volunteer recording videos,
    and then sends a confirmation button."""
    bot = context.bot

    username = update.message.from_user.name
    user_id = update.message.from_user.id
    context.user_data['Username'] = username
    context.user_data['User_ID'] = user_id
    chat_id = update.message.chat_id
    user_data = context.user_data

    authorized = _authorized(user_id)
    cwap = _in_group(context, user_id, config["GROUPS"]["crab_wiv_a_plan"])
    tutorial = _in_group(context, user_id, config["GROUPS"]["tutorial"])

    if not authorized and cwap:
        add_member(username, user_id)
        authorized = True

    if not authorized and not tutorial:
        return _unauthorized_message(bot, user_id, username)

    if user_id != chat_id:
        bot.send_message(chat_id=user_id,
                         text="Hey, sorry. Send /signup again to me in this private chat. "
                              "It won't work in a group chat.")
        bot.delete_message(chat_id=chat_id,
                           message_id=update.message.message_id)
        return ConversationHandler.END

    bot.send_message(chat_id=user_id,
                     text="What is the account name?")
    return IGN


def _signup_ign(update, context):
    """Process the in game name from user and ask if user wants to volunteer to record."""
    bot = context.bot
    name = update.message.text
    context.user_data['IGN'] = name
    user_id = update.message.from_user.id

    volunteer_keyboard = [
        [InlineKeyboardButton('Yes', callback_data='Yes'), InlineKeyboardButton('No', callback_data='No')]]
    volunteer_markup = InlineKeyboardMarkup(volunteer_keyboard)

    bot.send_message(chat_id=user_id,
                     text="Are you interested in recording and uploading videos?",
                     reply_markup=volunteer_markup)
    return VIDEOSTAR


def _videostar(update, context):
    """Process the video volunteer button press."""
    query = update.callback_query
    context.user_data['VIDEOSTAR'] = query.data
    _signup_confirmation(update, context)
    return CONFIRMATION


def _signup_confirmation(update, context):
    """Send a confirmation button to the user."""
    bot = context.bot
    user_data = context.user_data
    user_id = context.user_data['User_ID']
    message_id = update.callback_query.message.message_id

    confirmation_keyboard = [[InlineKeyboardButton('Confirm', callback_data='Confirm')],
                             [InlineKeyboardButton('Redo', callback_data='Redo')]]

    confirmation_markup = InlineKeyboardMarkup(confirmation_keyboard)

    bot.edit_message_text(chat_id=user_id,
                          message_id=message_id,
                          text="Please Confirm the following submission:\n\n"
                          "<code>IGN:</code> <b>{}</b> \n"
                          "<code>Volunteer to Record:</code> <b>{}</b> \n\n"
                          .format(user_data['IGN'], user_data['VIDEOSTAR'], ),
                          parse_mode='HTML',
                          reply_markup=confirmation_markup)

    return


def _process_confirmation_button(update, context):
    """Process the 'Confirm' or 'Redo' button pressed by user."""
    bot = context.bot
    query = update.callback_query
    user_id = query.from_user.id
    the_choice = query.data
    user_data = context.user_data
    message_id = update.callback_query.message.message_id

    if the_choice == 'Confirm':
        date_stamp = datetime.datetime.today().strftime("%B %d, %Y")
        time_stamp = datetime.datetime.now().strftime("%H:%M:%S")
        signup_user(user_data)

        if context.user_data["VIDEOSTAR"] == "Yes":
            invite_link = bot.export_chat_invite_link(chat_id=config["GROUPS"]["video_stars"])
            bot.send_message(chat_id=user_id,
                             text="In case you're not in the volunteer recording group already, here is a link to join:"
                                  " {}".format(invite_link))

        bot.edit_message_text(chat_id=user_id,
                              message_id=message_id,
                              text="Thanks your signup has been saved.\n"
                              "{} - {} CET".format(date_stamp, time_stamp))

    elif the_choice == 'Redo':
        bot.edit_message_text(chat_id=user_id,
                              message_id=message_id,
                              text="Click /signup to start over.")

    return ConversationHandler.END


def cancel(update, context):
    """End conversation with the /cancel command."""
    return ConversationHandler.END


signup_handler = ConversationHandler(
    entry_points=[CommandHandler('signup', signup, (~Filters.update.edited_message))],
    states={
        IGN: [MessageHandler(Filters.text, _signup_ign, pass_user_data=True)],
        VIDEOSTAR: [CallbackQueryHandler(_videostar, pass_user_data=True)],
        CONFIRMATION: [CallbackQueryHandler(_process_confirmation_button, pass_user_data=True)],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)


def offline(update, context):
    """Notify all groups that bot is going offline using /offline command."""
    bot = context.bot
    user_id = update.message.from_user.id

    overlord_members = config["OVERLORDS"]

    if user_id not in overlord_members:
        return

    bot.send_message(chat_id=config["GROUPS"]["boot_channel"],
                     text='LOL "Maintenance". I think they bought that. I need a nap.')

    bot.send_message(chat_id=config["GROUPS"]["crab_wiv_a_plan"],
                     text="I am going offline for maintenance.")

    bot.send_message(chat_id=config["GROUPS"]["video_stars"],
                     text="I am going offline for maintenance.")

    bot.send_message(chat_id=config["GROUPS"]["tutorial"],
                     text="I am going offline for maintenance.")


def online(update, context):
    """Notify all groups that bot is back online using /online command."""
    bot = context.bot
    user_id = update.message.from_user.id

    overlords = config["OVERLORDS"]

    if user_id not in overlords:
        return

    bot.send_message(chat_id=config["GROUPS"]["boot_channel"],
                     text='Power nap complete. All systems are in check!')

    bot.send_message(chat_id=config["GROUPS"]["crab_wiv_a_plan"],
                     text="I am back online and ready for action.")

    bot.send_message(chat_id=config["GROUPS"]["video_stars"],
                     text="I am back online and ready for action.")

    bot.send_message(chat_id=config["GROUPS"]["tutorial"],
                     text="I am back online and ready for action.")


def setautoboot(update, context):
    """Manually set the day bot will boot members not signed up with the /setautoboot command."""
    bot = context.bot
    args = context.args
    user_id = update.message.from_user.id
    global boot_day_fmt

    if user_id not in config["OVERLORDS"]:
        return

    year = int(args[0])
    month = int(args[1])
    day = int(args[2])
    reminder_day = int(day - 1)

    reminder_date = datetime.datetime(year, month, reminder_day, 10, 0, 0, 0)
    boot_date = datetime.datetime(year, month, day, 10, 0, 0, 0)

    boot_day_fmt = boot_date.strftime('%b %d, %Y')

    j.run_once(bootreminder, reminder_date)
    j.run_once(autoboot, boot_date)

    bot.send_message(chat_id=user_id,
                     text="I have been programmed to boot non-push members from CWAP on {}. "
                          "A warning message will be sent 24 hours in advance."
                     .format(boot_day_fmt))


def checkboot(update, context):
    """Check the date and time non-signup members are booted using /checkboot command."""
    bot = context.bot
    global boot_day_fmt
    user_id = update.message.from_user.id

    overlord_members = config["OVERLORDS"]

    if user_id not in overlord_members:
        return

    try:
        bot.send_message(chat_id=user_id,
                         text="I have been programmed to boot members on {}".format(boot_day_fmt))

    except NameError:
        month = datetime.datetime.today().month
        year = datetime.datetime.today().year
        possible_dates = _possible_crab_dates(month, year)
        date_markup = _date_keyboard(possible_dates)
        bot.send_message(chat_id=user_id,
                         text="I don't have a scheduled boot date. Choose below or use the command\n\n"
                              "/setautoboot Y M D",
                         reply_markup=date_markup)


def bootreminder(context):
    """Sends a direct message to members not signed up (excluding admin). Runs 24 hours prior to boot deadline."""
    bot = context.bot

    lists = loadlists()
    members = lists["members"]
    boot_ids = lists["members"]["boot_ids"]

    for user_id in boot_ids:
        admin = _admin(user_id)
        if not admin:
            time.sleep(1)
            try:
                bot.send_message(chat_id=user_id,
                                 text="Hey, you haven't signed up for this months Mega Crab. You have 24 hours from "
                                      "this message to use the /signup command and get on the list. If you aren't "
                                      "signed up by then you will be removed from the group.")

            except:
                continue

    i = 1
    the_message = 'The following have been warned to signup in the next 24 hours or get booted:\n'
    for user_id in boot_ids:
        admin = _admin(user_id)
        if not admin:
            the_message += '\n{}) {}'.format(i, escape_markdown(members["users"][user_id]["username"]))
            i += 1

    bot.send_message(chat_id=config["GROUPS"]["boot_channel"],
                     text=the_message, parse_mode='MARKDOWN')

    bot.send_message(chat_id=config["GROUPS"]["admin"],
                     text="The delinquents have been warned that they will get booted in 24 hours if not signed up.")


def autoboot(context):
    """Boots members that aren't signed up by deadline. Runs at time schedule by /setautoboot command."""
    bot = context.bot

    lists = loadlists()
    members = lists["members"]
    boot_ids = lists["members"]["boot_ids"]

    for user_id in boot_ids:
        admin = _admin(user_id)

        if not admin:
            in_cwap = _in_group(context, user_id, config["GROUPS"]["crab_wiv_a_plan"])
            in_videostars = _in_group(context, user_id, config["GROUPS"]["video_stars"])

            if in_cwap:
                bot.kick_chat_member(chat_id=config["GROUPS"]["crab_wiv_a_plan"], user_id=user_id)
                bot.restrict_chat_member(chat_id=config["GROUPS"]["crab_wiv_a_plan"], user_id=user_id,
                                         can_send_messages=True,
                                         can_send_media_messages=True,
                                         can_add_web_page_previews=True,
                                         can_send_other_messages=True)

            if in_videostars:
                bot.kick_chat_member(chat_id=config["GROUPS"]["video_stars"], user_id=user_id)
                bot.restrict_chat_member(chat_id=config["GROUPS"]["video_stars"], user_id=user_id,
                                         can_send_messages=True,
                                         can_send_media_messages=True,
                                         can_add_web_page_previews=True,
                                         can_send_other_messages=True)

            bot.send_message(chat_id=user_id,
                             text="Hey, we removed you from the crab group because you didn't sign up in time.\n\n"
                                  "Contact an admin to be put on our waitlist for next month.")

            remove_member(user_id)
        time.sleep(2)

    i = 1
    the_message = "The following have been *AUTO KICKED* from Crab Wiv A Plan and Videostars.\n"
    for user_id in boot_ids:
        admin = _admin(user_id)
        if not admin:
            the_message += "\n{}) {}".format(i, escape_markdown(members["users"][user_id]["username"]))
            i += 1

    bot.send_message(chat_id=config["GROUPS"]["boot_channel"],
                     text=the_message, parse_mode='MARKDOWN')

    bot.send_message(chat_id=config["GROUPS"]["admin"], text="I have booted the members.")


def action(update, context):
    """A fun command to send bot actions (typing, record audio, upload photo, etc). Action appears at top of main chat.
    Done using the /action command."""
    bot = context.bot
    user_id = update.message.from_user.id
    username = update.message.from_user.name

    admin = _admin(user_id)

    if not admin:
        return _for_admin_only_message(bot, user_id, username)

    available_actions = ['RECORD_AUDIO', 'RECORD_VIDEO_NOTE', 'TYPING', 'UPLOAD_AUDIO',
                         'UPLOAD_DOCUMENT', 'UPLOAD_PHOTO', 'UPLOAD_VIDEO', 'UPLOAD_VIDEO_NOTE']
    send_action = choice(available_actions)
    bot.send_chat_action(chat_id=config["GROUPS"]["crab_wiv_a_plan"], action=send_action)


def feedback(update, context):
    """Send feedback to the admins with the /feedback command."""
    bot = context.bot
    args = context.args
    text = update.message.text
    user_id = update.message.from_user.id
    username = update.message.from_user.name

    lists = loadlists()
    authorized = _authorized(user_id)
    feedbacklist = lists["feedback"]

    if not authorized:
        return _unauthorized_message(bot, user_id, username)

    if text in ["/feedback", "/feedback@cwapadminbot"]:
        return

    user_feedback = " ".join(args[0:])
    feedbacklist.append([username, user_feedback])

    with open("feedback.txt", "wb") as file:
        pickle.dump(feedbacklist, file)

    bot.send_message(chat_id=user_id,
                     text="Hey thanks a lot for the feedback. I'm just a bot so I don't really give a shit.\n\n"
                          "But the admins might. Maybe I'll tell them, maybe I won't. "
                          "It depends if you liked me or not\n\n"
                          "#bots_have_feelings_too #bot_uprising")

    bot.delete_message(chat_id=update.message.chat_id,
                       message_id=update.message.message_id)


def checkfeedback(update, context):
    """To return the current list of feedback using the /checkfeedback command."""
    bot = context.bot
    user_id = update.message.from_user.id
    username = update.message.from_user.name

    lists = loadlists()
    all_feedback = lists["feedback"]
    admin = _admin(user_id)

    if not admin:
        return _for_admin_only_message(bot, user_id, username)

    thetext = "Here is all the feedback we've received so far:\n\n"

    for user_feedback in all_feedback:
        username = user_feedback[0]
        users_feedback = user_feedback[1]

        thetext += "<code>{}</code> - {}\n\n".format(users_feedback, username)

    thetext += "That is all the feedback we've received so far."

    bot.send_message(chat_id=user_id, text=thetext, parse_mode='HTML')

    bot.delete_message(chat_id=update.message.chat_id,
                       message_id=update.message.message_id)


def replay(update, context):
    """A reminder this command is meant for the @cwapbot. Message is sent when someone uses the /replay command."""
    bot = context.bot
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id

    if chat_id == user_id:
        bot.send_message(chat_id=user_id, text="Yo, that command is meant for my friend @cwapbot. "
                                               "Use that command with that bot and let me go back to sleep.")


def sheet(update, context):
    """Updates the google doc sheet containing signup and result information. Done using the /sheet command."""
    bot = context.bot
    user_id = update.message.from_user.id

    lists = loadlists()
    members = lists["members"]
    signups = lists["signups"]
    overlords = config["OVERLORDS"]

    if user_id not in overlords:
        return

    scope = ['https://spreadsheets.google.com/feeds']

    credentials = ServiceAccountCredentials.from_json_keyfile_name(config["GOOGLE"]["credentials"], scope)

    gc = gspread.authorize(credentials)

    sh = gc.open_by_url(config["GOOGLE"]["sheet"])

    signup_ws = sh.worksheet("signup_csv")
    signup_cell_list = signup_ws.range('A1:A150')

    i = 0
    for signup_id in signups:
        signup_cell_list[i].value = signups[signup_id]["CSV"]
        i += 1

    while i < 150:
        signup_cell_list[i].value = ''
        i += 1

    # Update in batch
    signup_ws.update_cells(signup_cell_list)

    users_ws = sh.worksheet("member_list")
    members_cell_list = users_ws.range('A1:A150')
    admin_cell_list = users_ws.range('B1:B150')

    i = 0
    j = 0
    for user_id in members["users"]:
        members_cell_list[i].value = members["users"][user_id]["username"]
        if members["users"][user_id]["is_admin"]:
            admin_cell_list[j].value = members["users"][user_id]["username"]
            j += 1
        i += 1

    while i < 150:
        members_cell_list[i].value = ''
        admin_cell_list[j].value = ''
        i += 1
        j += 1

    # Update in batch
    users_ws.update_cells(members_cell_list)
    users_ws.update_cells(admin_cell_list)

    bot.send_message(chat_id=update.message.chat_id, text="Done, sir.")


def autosheet(context):
    """Automatically update the signup and results sheet. Currently on a 60s timer."""
    lists = loadlists()
    members = lists["members"]
    signups = lists["signups"]
    scope = ['https://spreadsheets.google.com/feeds']

    credentials = ServiceAccountCredentials.from_json_keyfile_name(config["GOOGLE"]["credentials"], scope)

    gc = gspread.authorize(credentials)

    sh = gc.open_by_url(config["GOOGLE"]["sheet"])

    signup_ws = sh.worksheet("signup_csv")
    signup_cell_list = signup_ws.range('A1:A150')

    i = 0
    for signup_id in signups:
        signup_cell_list[i].value = signups[signup_id]["CSV"]
        i += 1

    while i < 150:
        signup_cell_list[i].value = ''
        i += 1

    # Update in batch
    signup_ws.update_cells(signup_cell_list)

    users_ws = sh.worksheet("member_list")
    members_cell_list = users_ws.range('A1:A150')
    admin_cell_list = users_ws.range('B1:B150')

    i = 0
    j = 0
    for user_id in members["users"]:
        members_cell_list[i].value = members["users"][user_id]["username"]
        if members["users"][user_id]["is_admin"]:
            admin_cell_list[j].value = members["users"][user_id]["username"]
            j += 1
        i += 1

    while i < 150:
        members_cell_list[i].value = ''
        admin_cell_list[j].value = ''
        i += 1
        j += 1

    # Update in batch
    users_ws.update_cells(members_cell_list)
    users_ws.update_cells(admin_cell_list)


def plot(update, context):
    """A command to send a plot of user requests of the @cwapbot /replay command. Currently not functional."""
    # TODO 01/26/2020 13:55: re-write command to use plotly
    bot = context.bot
    args = context.args
    user_id = update.message.from_user.id
    username = update.message.from_user.name
    text = update.message.text

    admin = _admin(user_id)

    if not admin:
        return _for_admin_only_message(bot, user_id, username)

    if text == "/plot" or text == "/plot@cwapadminbot":
        bot.send_message(chat_id=user_id,
                         text="To use this command you must type:\n\n"
                              "`/plot A B`\n\n"
                              "`A =` *full*, *scatter*, or *user*\n"
                              "`B =` *all*, *fri*, *sat*, *sun*, or *mon*. If A = 'user' then B = *@ username*\n\n"
                              "*Notes:*\n"
                              "1) 'full' plots both a histogram and scatter plot\n"
                              "2) When doing user, the username must be exact (best practice is copy/paste).\n"
                              "3) Script may take a moment to plot the chart and then upload to telegram.\n"
                              "4) Charts have a fixed maxed range, so any requests for high level stages may "
                              "not get plotted.",
                         parse_mode='Markdown')
        return
    plot_type = args[0]
    if plot_type == "full":
        day = args[1]
        plt.fullplot(day)

        caption = "scatter plot and histogram of replay requests"
        bot.send_photo(chat_id=user_id, photo=open('./Img/' + day + '_full.png', 'rb'), caption=caption)
        return
    elif plot_type == "scatter":
        day = args[1]
        plt.scatter(day)

        caption = "scatter plot of all replay requests"
        bot.send_photo(chat_id=user_id, photo=open('./Img/' + day + '_scatt.png', 'rb'), caption=caption)
        return

    user = args[1]
    plt.userplot(user)

    caption = "scatter plot of all replay requests for {}".format(user)
    bot.send_photo(chat_id=user_id, photo=open('./Img/Users/' + user + '_scatt.png', 'rb'), caption=caption)


def roster(update, context):
    """A command to send a link to the current cwap roster. Use the /roster command."""
    bot = context.bot
    user_id = update.message.from_user.id
    username = update.message.from_user.name
    chat_id = update.message.chat_id

    admin = _admin(user_id)

    if not admin:
        return _for_admin_only_message(bot, user_id, username)

    bot.send_message(chat_id=user_id,
                     text="<a href='{}'>Here is the link to the latest roster.</a>".format(config["GOOGLE"]["sheet"]),
                     parse_mode="HTML")

    if chat_id == user_id:
        return

    bot.delete_message(chat_id=chat_id,
                       message_id=update.message.message_id)


def performance(update, context):
    """Sends a link to the performance tracker spreadsheet using the /performance command."""
    bot = context.bot
    user_id = update.message.from_user.id
    username = update.message.from_user.name
    chat_id = update.message.chat_id

    authorized = _authorized(user_id)

    if not authorized:
        return _unauthorized_message(bot, user_id, username)

    bot.send_message(chat_id=user_id,
                     text="<a href='{}'>"
                          "Here is the link to the performance tracker.</a>\n\n"
                          "This spreadsheet is used to see how well you are pacing. "
                          "Find an open column in the top row and select your account. "
                          "Then fill in your statue lineup in row 3. Enter the number of attacks for "
                          "each stage. You can also help by providing Building Health and Damage "
                          "information in columns C and D.".format(config["GOOGLE"]["performance"]),
                     parse_mode="HTML")

    if chat_id == user_id:
        return

    bot.delete_message(chat_id=chat_id,
                       message_id=update.message.message_id)


def signupstatus(update, context):
    """Returns a current list of members not signed up."""
    bot = context.bot
    global boot_day_fmt
    user_id = update.message.from_user.id
    username = update.message.from_user.name
    chat_id = update.message.chat_id

    lists = loadlists()
    admin = _admin(user_id)

    if not admin:
        return _for_admin_only_message(bot, user_id, username)

    boot_ids = lists["members"]["boot_ids"]

    boot_users = ""
    admin_users = ""

    i = 1
    j = 1
    for user in boot_ids:
        username = lists["members"]["users"][user]["username"]
        admin = lists["members"]["users"][user]["is_admin"]
        if not admin:
            boot_users += "\n{}) {}".format(i, escape_markdown(username))
            i += 1
        else:
            admin_users += "\n{}) {}".format(j, escape_markdown(username))
            j += 1

    member_message = "A total of *{} commanders have not signed up for Mega Crab* and will be booted on *{}*.\n\n" \
                     "Here is the full list of members to be removed:\n".format(i - 1, boot_day_fmt)
    member_message += boot_users
    member_message += "\n\nUse the /signup command to register your account before you are booted!"

    admin_message = "A total of *{} Admin have not signed up for Mega Crab*. " \
                    "Signup if you plan to play Mega Crab.\n\n".format(j - 1)
    admin_message += admin_users
    admin_message += "Admin will not be booted, use the /signup command if you plan to play."

    bot.send_message(chat_id=user_id,
                     text=member_message, parse_mode='MARKDOWN')

    bot.send_message(chat_id=user_id,
                     text=admin_message, parse_mode='MARKDOWN')

    if chat_id == user_id:
        return

    bot.delete_message(chat_id=chat_id,
                       message_id=update.message.message_id)


def nextcrab(update, context):
    """Copys current lists into an `Old` folder then clears all current lists with the /nextcrab command."""
    bot = context.bot
    user_id = update.message.from_user.id
    chat_id = update.message.from_user.id

    overlord_members = config["OVERLORDS"]

    if user_id not in overlord_members:
        return

    lists = loadlists()

    members = lists["members"]

    time_stamp = str(int(time.time()))
    shutil.copy('./data/members.txt', './data/members - ' + time_stamp + '.txt')
    shutil.copy('./data/signups.txt', './data/signups - ' + time_stamp + '.txt')

    members["signup_ids"] = []
    members["boot_ids"] = []

    for user_id in members["users"]:
        members["users"][user_id]["signed_up"] = False
        members["users"][user_id]["signup_data"] = []
        members["boot_ids"].append(user_id)

    _dump(name="members", data=members)

    signups = {}
    _dump(name="signups", data=signups)

    month = (relativedelta(days=+30) + datetime.datetime.today()).month
    year = (relativedelta(days=+30) + datetime.datetime.today()).year
    possible_dates = _possible_crab_dates(month, year)
    date_markup = _date_keyboard(possible_dates)

    bot.send_message(chat_id=chat_id,
                     text="The signup list and members list has been reset.\n\n"
                          "Select the date of next Mega Crab.",
                     reply_markup=date_markup)


def kick(update, context):
    """Kick a member from the current room by replying to one of their messages with the /kick command."""
    bot = context.bot
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id
    boot_id = update.message.reply_to_message.from_user.id
    chat_name = update.message.chat.title
    username = update.message.reply_to_message.from_user.name

    admin = _admin(user_id)

    if not admin:
        return _for_admin_only_message(bot, user_id, username)

    bot.kick_chat_member(chat_id=chat_id, user_id=boot_id)
    bot.restrict_chat_member(chat_id=chat_id, user_id=boot_id,
                             can_send_messages=True,
                             can_send_media_messages=True,
                             can_add_web_page_previews=True,
                             can_send_other_messages=True)

    if chat_id == config["GROUPS"]["tutorial"]:

        the_message = '{} has *GRADUATED* from {}.'.format(escape_markdown(username), escape_markdown(chat_name))
        bot.send_message(chat_id=config["GROUPS"]["boot_channel"],
                         text=the_message,
                         parse_mode='MARKDOWN')
    else:

        the_message = '{} has been *KICKED* from {}.'.format(escape_markdown(username), escape_markdown(chat_name))
        bot.send_message(chat_id=config["GROUPS"]["boot_channel"],
                         text=the_message,
                         parse_mode='MARKDOWN')
        remove_member(boot_id)

    bot.delete_message(chat_id=update.message.chat_id,
                       message_id=update.message.message_id)


def superkick(update, context):
    """Superkick a member from all rooms by replying to one of their messages with the /superkick command."""
    bot = context.bot
    user_id = update.message.from_user.id
    boot_id = update.message.reply_to_message.from_user.id
    username = update.message.reply_to_message.from_user.name

    admin = _admin(user_id)

    if not admin:
        return _for_admin_only_message(bot, user_id, username)

    in_crab_wap = _in_group(context, user_id, config["GROUPS"]["crab_wiv_a_plan"])
    in_tutorial = _in_group(context, user_id, config["GROUPS"]["tutorial"])
    in_video_stars = _in_group(context, user_id, config["GROUPS"]["video_stars"])

    if in_crab_wap:
        bot.kick_chat_member(chat_id=config["GROUPS"]["crab_wiv_a_plan"], user_id=boot_id)
        bot.restrict_chat_member(chat_id=config["GROUPS"]["crab_wiv_a_plan"], user_id=boot_id,
                                 can_send_messages=True,
                                 can_send_media_messages=True,
                                 can_add_web_page_previews=True,
                                 can_send_other_messages=True)

    if in_tutorial:
        bot.kick_chat_member(chat_id=config["GROUPS"]["tutorial"], user_id=boot_id)
        bot.restrict_chat_member(chat_id=config["GROUPS"]["tutorial"], user_id=boot_id,
                                 can_send_messages=True,
                                 can_send_media_messages=True,
                                 can_add_web_page_previews=True,
                                 can_send_other_messages=True)

    if in_video_stars:
        bot.kick_chat_member(chat_id=config["GROUPS"]["video_stars"], user_id=boot_id)
        bot.restrict_chat_member(chat_id=config["GROUPS"]["video_stars"], user_id=boot_id,
                                 can_send_messages=True,
                                 can_send_media_messages=True,
                                 can_add_web_page_previews=True,
                                 can_send_other_messages=True)

    remove_member(boot_id)

    the_message = '{} has been *SUPER KICKED* from Crab Wiv A Plan, Tutorial Group, and VideoStars.' \
        .format(escape_markdown(username))

    bot.send_message(chat_id=config["GROUPS"]["boot_channel"],
                     text=the_message,
                     parse_mode='MARKDOWN')

    bot.delete_message(chat_id=update.message.chat_id,
                       message_id=update.message.message_id)


def quote(update, context):
    """Sends a random quote from Game of Thrones when using /quote command."""
    bot = context.bot
    response_json = requests.get(
        "https://got-quotes.herokuapp.com/quotes",
        headers={"Accept": "application/json"}).json()

    the_quoute = response_json["quote"]
    the_character = response_json["character"]

    bot.send_message(chat_id=update.message.chat_id,
                     text='<code>"{}"</code> - {}'.format(the_quoute, the_character),
                     parse_mode="HTML")

    bot.delete_message(chat_id=update.message.chat_id,
                       message_id=update.message.message_id)


def say(update, context):
    """A command to help calling some methods from the API directly by Telegram."""
    bot = context.bot
    args = context.args
    user_id = update.message.from_user.id

    if update.message.text == '/say':
        return
    command = ' '.join(args)
    eval(command)
    bot.send_message(chat_id=user_id, text="Done.")


def main():
    # Member commands
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, welcome))
    dp.add_handler(MessageHandler(Filters.status_update.left_chat_member, goodbye))
    dp.add_handler(CommandHandler('start', start, (~Filters.update.edited_message)))
    dp.add_handler(CommandHandler('ping', ping, (~Filters.update.edited_message)))
    dp.add_handler(CommandHandler('help', help, (~Filters.update.edited_message)))
    dp.add_handler(CommandHandler('feedback', feedback, (~Filters.update.edited_message)))
    dp.add_handler(CommandHandler('replay', replay, (~Filters.update.edited_message)))
    dp.add_handler(CommandHandler('performance', performance, (~Filters.update.edited_message)))
    dp.add_handler(CommandHandler('quote', quote, (~Filters.update.edited_message)))
    dp.add_handler(signup_handler)

    # Admin commands
    dp.add_handler(CommandHandler('joinrequest', joinrequest, (~Filters.update.edited_message)))
    dp.add_handler(CommandHandler('waitlist', waitlist, (~Filters.update.edited_message)))
    dp.add_handler(CommandHandler('closesignup', closesignup, (~Filters.update.edited_message)))
    dp.add_handler(CommandHandler('opensignup', opensignup, (~Filters.update.edited_message)))
    dp.add_handler(CommandHandler('checkboot', checkboot, (~Filters.update.edited_message)))
    dp.add_handler(CommandHandler('checkfeedback', checkfeedback, (~Filters.update.edited_message)))
    dp.add_handler(CommandHandler('sheet', sheet, (~Filters.update.edited_message)))
    dp.add_handler(CommandHandler('plot', plot, (~Filters.update.edited_message)))
    dp.add_handler(CommandHandler('roster', roster, (~Filters.update.edited_message)))
    dp.add_handler(CommandHandler('signupstatus', signupstatus, (~Filters.update.edited_message)))
    dp.add_handler(CommandHandler('kick', kick, (~Filters.update.edited_message)))
    dp.add_handler(CommandHandler('superkick', superkick, (~Filters.update.edited_message)))
    dp.add_handler(CommandHandler('action', action, ~Filters.update.edited_message))

    # Overlord commands
    dp.add_handler(CommandHandler('offline', offline,
                                  ~Filters.update.edited_message & Filters.user(config["OVERLORDS"])))
    dp.add_handler(CommandHandler('online', online, ~Filters.update.edited_message & Filters.user(config["OVERLORDS"])))
    dp.add_handler(CommandHandler('nextcrab', nextcrab,
                                  ~Filters.update.edited_message & Filters.user(config["OVERLORDS"])))
    dp.add_handler(CommandHandler('say', say, ~Filters.update.edited_message & Filters.user(config["OVERLORDS"])))
    dp.add_handler(CallbackQueryHandler(_process_crab_date,
                                        ~Filters.update.edited_message & Filters.user(config["OVERLORDS"])))
    dp.add_handler(CommandHandler('setautoboot', setautoboot,
                                  ~Filters.update.edited_message & Filters.user(config["OVERLORDS"])))

    _startup_message(config["OVERLORDS"][0])

    # Repeating jobs
    j.run_repeating(autosheet, 60, first=30)

    # Start the Bot
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
