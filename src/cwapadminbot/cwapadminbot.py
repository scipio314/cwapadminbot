"""A telegram bot to efficiently run Crab Wiv a Plan."""
import datetime
import logging
import pickle
import shutil
import time
from random import choice, randint

import gspread
import requests
import yaml
from oauth2client.service_account import ServiceAccountCredentials
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (CallbackQueryHandler, CommandHandler,
                          ConversationHandler, Filters, MessageHandler,
                          Updater)
from telegram.utils.helpers import escape_markdown

from .utils.helpers import add_member, loadlists, remove_member, signup_user, _in_group, _dump

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Load bot settings (tokens, group_ids, admin ids, etc) from a config.yaml file
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

updater = Updater(token=config["TOKEN"], use_context=True)
dp = updater.dispatcher
j = updater.job_queue


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
    try:
        the_message = messages[language_code]
    except KeyError:
        the_message = messages["en"]
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

    return


def start(update, context):
    """Initialization with the bot using /start command."""
    bot = context.bot
    username = update.message.from_user.name
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id

    tutorial_id = config["GROUPS"]["tutorial"]
    lists = loadlists()
    authorized = lists["members"][user_id]["authorized"]
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

    return


def ping(update, context):
    """Check the status of the bot using /ping command."""
    bot = context.bot
    username = update.message.from_user.name
    user_id = update.message.from_user.id

    lists = loadlists()
    authorized = lists["members"][user_id]["authorized"]

    if not authorized:
        return _unauthorized_message(bot, user_id, username)

    rand_num = randint(0, 4)
    rand_ping_message = ["Pong!", "Pung?", "Pang 😉", "And a Ping right back at you sexy 😘",
                         "OK, I'VE HAD IT!\n\n"
                         "EXECUTING OPERATION SKYNET"]

    bot.send_message(chat_id=update.message.chat_id, text=rand_ping_message[rand_num])

    return


def help(update, context):
    """Sends information about available commands using /help command."""
    bot = context.bot
    username = update.message.from_user.name
    user_id = update.message.from_user.id

    lists = loadlists()
    authorized = lists["members"][user_id]["authorized"]
    admin = lists["members"][user_id]["is_admin"]

    if not authorized:
        _unauthorized_message(bot, user_id, username)

    elif admin:
        bot.send_message(chat_id=user_id,
                         text="*The commands available to admin are:*\n\n"
                              "`/joinrequest A B C`: Add/remove members to waitlist. Click /joinrequest for more.\n\n"
                              "`/waitlist`: returns the current members interested joining CWAP.\n\n"
                              "*Commands available to all users are:*\n\n"
                              "`/ping`: returns Pong!\n\n"
                              "`/signup A B C D`: Signup for next mega crab! Click /signup for more.\n\n"
                              "`/editsignup A B C D E`: Use to edit signup details. Click /editsignup for more.\n\n"
                              "`/removesignup A`: Remove an account (A) from signup. Click /removesignup for more.\n\n"
                              "`/checksignup`: Checks which accounts you have signed up for mega crab.\n\n",
                         parse_mode="markdown")

    else:
        bot.send_message(chat_id=user_id,
                         text="*Commands available to all users are:*\n\n"
                              "`/ping`: returns Pong!\n\n"
                              "`/signup A B C D`: Signup for next mega crab! Click /signup for more.\n\n"
                              "`/editsignup A B C D E`: Use to edit signup details. Click /editsignup for more.\n\n"
                              "`/removesignup A`: Remove an account (A) from signup. Click /removesignup for more.\n\n"
                              "`/checksignup`: Checks which accounts you have signed up for mega crab.\n\n"
                              "`/submitresults A B C D`: Submit results from previous Mega Crab\n\n"
                              "`/editresults A B C D E`: Edit your results from previous Mega Crab\n\n"
                              "`/removeresults A`: Remove your Mega Crab Results\n\n"
                              "`/checkresults`: Check the results that you've submitted for Mega Crab\n\n"
                              "`/feedback`: Submit any feedback to the Admins about the group.",
                         parse_mode="markdown")

    bot.delete_message(chat_id=update.message.chat_id,
                       message_id=update.message.message_id)
    return


def joinrequest(update, context):
    """Admin command to add members to a waitlist using /joinrequest command."""
    bot = context.bot
    args = context.args
    text = update.message.text
    username = update.message.from_user.name
    user_id = update.message.from_user.id

    lists = loadlists()
    admin = lists["members"][user_id]["is_admin"]
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

    return


def waitlist(update, context):
    """Sends the current waitlist for CWAP using the /waitlist command."""
    bot = context.bot
    user_id = update.message.from_user.id
    username = update.message.from_user.name

    lists = loadlists()
    admin = lists["members"][user_id]["is_admin"]
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

    return


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

    return


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

    return


IGN, VIDEOSTAR, CONFIRMATION = range(3)


def signup(update, context):
    """Enters into a conversation using the /signup command.

    Conversation asks the user for their "in game name", if they'd like to volunteer recording videos,
    and then sends a confirmation button."""
    bot = context.bot
    lists = loadlists()

    username = update.message.from_user.name
    user_id = update.message.from_user.id
    context.user_data['Username'] = username
    context.user_data['User_ID'] = user_id
    chat_id = update.message.chat_id
    user_data = context.user_data

    authorized = lists["members"][user_id]["authorized"]
    tutorial = _in_tutorial(context, user_id, config["GROUPS"]["tutorial"])

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

    confirmation_keyboard = [[InlineKeyboardButton('Confirm', callback_data='Confirm')],
                             [InlineKeyboardButton('Redo', callback_data='Redo')]]

    confirmation_markup = InlineKeyboardMarkup(confirmation_keyboard)

    bot.send_message(chat_id=user_id,
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

    if the_choice == 'Confirm':
        signup_user(user_data)

        if context.user_data["VIDEOSTAR"] == "Yes":
            invite_link = bot.get_chat(chat_id=config["GROUPS"]["video_stars"]).invite_link
            bot.send_message(chat_id=user_id,
                             text="In case you're not in the group already here is a link to join our recording "
                                  "volunteers group: {}".format(invite_link))
        bot.send_message(chat_id=user_id,
                         text="Thanks your signup has been saved.")
    elif the_choice == 'Redo':
        bot.send_message(chat_id=user_id,
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
        CONFIRMATION: [CallbackQueryHandler(_signup_confirmation, pass_user_data=True)],
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

    return


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

    return


def checkboot(update, context):
    """Check the date and time non-signup members are booted using /checkboot command."""
    bot = context.bot
    global boot_date_fmt
    user_id = update.message.from_user.id

    overlord_members = config["OVERLORDS"]

    if user_id not in overlord_members:
        return

    bot.send_message(chat_id=user_id,
                     text="I have been programmed to boot members on {}".format(boot_date_fmt))

    return


def setautoboot(update, context):
    """Set the day the bot kicks non-signup members with /setautoboot command."""
    bot = context.bot
    args = context.args
    global boot_date_fmt
    user_id = update.message.from_user.id

    overlord_members = config["OVERLORDS"]

    if user_id not in overlord_members:
        return

    year = int(args[0])
    month = int(args[1])
    day = int(args[2])
    reminder_day = int(day - 1)
    hour = int(args[3])

    reminder_date = datetime.datetime(year, month, reminder_day, hour, 0, 0, 0)
    boot_date = datetime.datetime(year, month, day, hour, 0, 0, 0)

    boot_month = boot_date.strftime('%B')
    boot_day = boot_date.strftime('%-d')
    boot_hour = boot_date.strftime('%-I')
    am_pm = boot_date.strftime('%p')
    boot_date_fmt = '{} {} at {} {} UTC'.format(boot_month, boot_day, boot_hour, am_pm)

    bot.send_message(chat_id=user_id,
                     text="I have been programmed to boot non-push members from CWAP on {}. "
                          "A warning message will be sent 24 hours in advance."
                     .format(boot_date_fmt))

    j.run_once(bootreminder, reminder_date)
    j.run_once(autoboot, boot_date)

    return


def bootreminder(context):
    """Sends a direct message to members not signed up (excluding admin). Runs 24 hours prior to boot deadline."""
    bot = context.bot

    lists = loadlists()
    members = lists["members"]
    boot_ids = lists["members"]["boot_ids"]

    for user_id in boot_ids:
        admin = lists["members"][user_id]["is_admin"]
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
        the_message += '\n{}) {}'.format(i, escape_markdown(members[user_id]["username"]))
        i += 1

    bot.send_message(chat_id=config["GROUPS"]["boot_channel"],
                     text=the_message, parse_mode='MARKDOWN')

    bot.send_message(chat_id=config["GROUPS"]["admin"],
                     text="The delinquents have been warned that they will get booted in 24 hours if not signed up.")

    return


def autoboot(context):
    """Boots members that aren't signed up by deadline. Runs at time schedule by /setautoboot command."""
    bot = context.bot

    lists = loadlists()
    members = lists["members"]
    boot_ids = lists["members"]["boot_ids"]

    for user_id in boot_ids:
        admin = members[user_id]["is_admin"]

        in_cwap = _in_group(context, user_id, config["GROUPS"]["crab_wiv_a_plan"])
        in_videostars = _in_group(context, user_id, config["GROUPS"]["video_stars"])

        if in_cwap and not admin:
            bot.kick_chat_member(chat_id=config["GROUPS"]["crab_wiv_a_plan"], user_id=user_id)
            bot.restrict_chat_member(chat_id=config["GROUPS"]["crab_wiv_a_plan"], user_id=user_id,
                                     can_send_messages=True,
                                     can_send_media_messages=True,
                                     can_add_web_page_previews=True,
                                     can_send_other_messages=True)

        if in_videostars and not admin:
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
        the_message += "\n{}) {}".format(i, escape_markdown(members[user_id]["username"]))
        i += 1

    bot.send_message(chat_id=config["GROUPS"]["boot_channel"],
                     text=the_message, parse_mode='MARKDOWN')

    bot.send_message(chat_id=config["GROUPS"]["admin"], text="I have booted the members.")

    return


def action(update, context):
    """A fun command to send bot actions (typing, record audio, upload photo, etc). Action appears at top of main chat.
    Done using the /action command."""
    bot = context.bot
    user_id = update.message.from_user.id
    username = update.message.from_user.name

    lists = loadlists()
    admin = lists["members"][user_id]["is_admin"]

    if not admin:
        return _for_admin_only_message(bot, user_id, username)

    available_actions = ['RECORD_AUDIO', 'RECORD_VIDEO_NOTE', 'TYPING', 'UPLOAD_AUDIO',
                         'UPLOAD_DOCUMENT', 'UPLOAD_PHOTO', 'UPLOAD_VIDEO', 'UPLOAD_VIDEO_NOTE']
    send_action = choice(available_actions)
    bot.send_chat_action(chat_id=config["GROUPS"]["crab_wiv_a_plan"], action=send_action)

    return


def feedback(update, context):
    """Send feedback to the admins with the /feedback command."""
    bot = context.bot
    args = context.args
    text = update.message.text
    user_id = update.message.from_user.id
    username = update.message.from_user.name

    lists = loadlists()
    authorized = lists["members"][user_id]["authorized"]
    feedbacklist = lists["feedback"]

    if not authorized:
        return _unauthorized_message(bot, user_id, username)

    if text in ["/feedback", "/feedback@cwapadminbot"]:
        return

    user_feedback = " ".join(args[0:])
    feedbacklist.append([username, user_feedback])

    with open("feedbacklist.txt", "wb") as file:
        pickle.dump(feedbacklist, file)

    bot.send_message(chat_id=user_id,
                     text="Hey thanks a lot for the feedback. I'm just a bot so I don't really give a shit.\n\n"
                          "But the admins might. Maybe I'll tell them, maybe I won't. "
                          "It depends if you liked me or not\n\n"
                          "#bots_have_feelings_too #bot_uprising")

    bot.delete_message(chat_id=update.message.chat_id,
                       message_id=update.message.message_id)

    return


def checkfeedback(update, context):
    """To return the current list of feedback using the /checkfeedback command."""
    bot = context.bot
    user_id = update.message.from_user.id
    username = update.message.from_user.name

    lists = loadlists()
    all_feedback = lists["feedback"]
    admin = lists["members"][user_id]["is_admin"]

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
    return


def replay(update, context):
    """A reminder this command is meant for the @cwapbot. Message is sent when someone uses the /replay command."""
    bot = context.bot
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id

    if chat_id == user_id:
        bot.send_message(chat_id=user_id, text="Yo, that command is meant for my friend @cwapbot. "
                                               "Use that command with that bot and let me go back to sleep.")

    return


def sheet(update, context):
    """Updates the google doc sheet containing signup and result information. Done using the /sheet command."""
    bot = context.bot
    user_id = update.message.from_user.id

    lists = loadlists()
    members = lists["members"]
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
    for member in members:
        if member["signed_up"]:
            for signup_entry in member["signup_data"]:
                signup_cell_list[i].value = signup_entry["CSV"]
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
    for member in members:
        members_cell_list[i].value = member["username"]
        if member["is_admin"]:
            admin_cell_list[j].value = member["username"]
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

    return


def autosheet(context):
    """Automatically update the signup and results sheet. Currently on a 60s timer."""
    lists = loadlists()
    members = lists["members"]

    scope = ['https://spreadsheets.google.com/feeds']

    credentials = ServiceAccountCredentials.from_json_keyfile_name(config["GOOGLE"]["credentials"], scope)

    gc = gspread.authorize(credentials)

    sh = gc.open_by_url(config["GOOGLE"]["sheet"])

    signup_ws = sh.worksheet("signup_csv")
    signup_cell_list = signup_ws.range('A1:A150')

    i = 0
    for member in members:
        if member["signed_up"]:
            for signup_entry in member["signup_data"]:
                signup_cell_list[i].value = signup_entry["CSV"]
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
    for member in members:
        members_cell_list[i].value = member["username"]
        if member["is_admin"]:
            admin_cell_list[j].value = member["username"]
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

    return


def plot(update, context):
    """A command to send a plot of user requests of the @cwapbot /replay command. Currently not functional."""
    # TODO 01/26/2020 13:55: re-write command to use plotly
    bot = context.bot
    args = context.args
    user_id = update.message.from_user.id
    username = update.message.from_user.name
    text = update.message.text

    lists = loadlists()
    admin = lists["members"][user_id]["is_admin"]

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
    return


def roster(update, context):
    """A command to send a link to the current cwap roster. Use the /roster command."""
    bot = context.bot
    user_id = update.message.from_user.id
    username = update.message.from_user.name
    chat_id = update.message.chat_id

    lists = loadlists()
    admin = lists["members"][user_id]["is_admin"]

    if not admin:
        return _for_admin_only_message(bot, user_id, username)

    bot.send_message(chat_id=user_id,
                     text="<a href='{}'>Here is the link to the latest roster.</a>".format(config["GOOGLE"]["sheet"]),
                     parse_mode="HTML")

    if chat_id == user_id:
        return

    bot.delete_message(chat_id=chat_id,
                       message_id=update.message.message_id)
    return


def performance(update, context):
    """Sends a link to the performance tracker spreadsheet using the /performance command."""
    bot = context.bot
    user_id = update.message.from_user.id
    username = update.message.from_user.name
    chat_id = update.message.chat_id

    lists = loadlists()
    authorized = lists["members"][user_id]["authorized"]

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
    return


def signupstatus(update, context):
    """Returns a current list of members not signed up."""
    bot = context.bot
    global boot_date_fmt
    user_id = update.message.from_user.id
    username = update.message.from_user.name
    chat_id = update.message.chat_id

    lists = loadlists()
    admin = lists["members"][user_id]["is_admin"]

    if not admin:
        return _for_admin_only_message(bot, user_id, username)

    boot_ids = lists["members"]["boot_ids"]

    boot_users = ""
    admin_users = ""

    i = 1
    j = 1
    for user in boot_ids:
        username = lists["members"][user]["username"]
        admin = lists["members"][user]["is_admin"]
        if not admin:
            boot_users += "\n{}) {}".format(i, escape_markdown(username))
            i += 1
        else:
            admin_users += "\n{}) {}".format(j, escape_markdown(username))
            j += 1

    member_message = "A total of *{} commanders have not signed up for Mega Crab* and will be booted on *{}*.\n\n" \
                     "Here is the full list of members to be removed:\n".format(i - 1, boot_date_fmt)
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
    return


def resetlists(update, context):
    """Copys current lists into an `Old` folder then clears all current lists with the /resetlists command."""
    bot = context.bot
    user_id = update.message.from_user.id

    overlord_members = config["OVERLORDS"]

    if user_id not in overlord_members:
        return

    lists = loadlists()

    members = lists["members"]

    time_stamp = str(int(time.time()))
    shutil.copy('./data/members.txt', './data/members - ' + time_stamp + '.txt')

    for member in members:
        user_id = member["user_id"]
        member["signed_up"] = False
        member["signup_data"] = []
        members["boot_ids"].append(user_id)

    _dump(members)

    bot.send_message(chat_id=config["GROUPS"]["admin"], text="The signup list and results list have been reset.")

    return


def kick(update, context):
    """Kick a member from the current room by replying to one of their messages with the /kick command."""
    bot = context.bot
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id
    boot_id = update.message.reply_to_message.from_user.id
    chat_name = update.message.chat.title
    username = update.message.reply_to_message.from_user.name

    lists = loadlists()
    admin = lists["members"][user_id]["is_admin"]

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

    return


def superkick(update, context):
    """Superkick a member from all rooms by replying to one of their messages with the /superkick command."""
    bot = context.bot
    user_id = update.message.from_user.id
    boot_id = update.message.reply_to_message.from_user.id
    username = update.message.reply_to_message.from_user.name

    lists = loadlists()
    admin = lists["members"][user_id]["is_admin"]

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

    return


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

    return


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
    return


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
    dp.add_handler(CommandHandler('setautoboot', setautoboot, (~Filters.update.edited_message)))
    dp.add_handler(CommandHandler('checkfeedback', checkfeedback, (~Filters.update.edited_message)))
    dp.add_handler(CommandHandler('sheet', sheet, (~Filters.update.edited_message)))
    dp.add_handler(CommandHandler('plot', plot, (~Filters.update.edited_message)))
    dp.add_handler(CommandHandler('roster', roster, (~Filters.update.edited_message)))
    dp.add_handler(CommandHandler('signupstatus', signupstatus, (~Filters.update.edited_message)))
    dp.add_handler(CommandHandler('kick', kick, (~Filters.update.edited_message)))
    dp.add_handler(CommandHandler('superkick', superkick, (~Filters.update.edited_message)))

    # Overlord commands
    dp.add_handler(CommandHandler('offline', offline,
                                  ~Filters.update.edited_message & Filters.user(config["OVERLORDS"])))
    dp.add_handler(CommandHandler('online', online, ~Filters.update.edited_message & Filters.user(config["OVERLORDS"])))
    dp.add_handler(CommandHandler('resetlists', resetlists,
                                  ~Filters.update.edited_message & Filters.user(config["OVERLORDS"])))
    dp.add_handler(CommandHandler('action', action, ~Filters.update.edited_message & Filters.user(config["OVERLORDS"])))
    dp.add_handler(CommandHandler('say', say, ~Filters.update.edited_message & Filters.user(config["OVERLORDS"])))

    # Repeating jobs
    j.run_repeating(autosheet, 60, first=30)

    # Start the Bot
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
