IGN, STAGE, DESTROY, LOCAL, LOCAL_NO, USER_CONFIRMATION, USER_CHOICE, REDO, EDIT_IGN, EDIT_COUNTRY, EDIT_STAGE, EDIT_DESTROY, CANCEL = range(13)


def user_results(user_data):
    global resultslist
    user_result = []

    user_result.append(user_data['Username'])
    user_result.append(user_data['User_ID'])
    user_result.append(user_data['IGN'])
    user_result.append(user_data['Country'])
    user_result.append(user_data['Stage_Finished'])
    user_result.append(user_data['Local_No_One'])
    csv_data = "{},{},{},{},{},{},{}".format(user_data['Username'], user_data['Country'], user_data['IGN'],
                                             user_data['Stage'], user_data['Percentage'], user_data['Stage_Finished'],
                                             user_data['Local_No_One'])
    user_result.append(csv_data)
    resultslist.append(user_result)

    with open("resultslist.txt", "wb") as file:
        pickle.dump(resultslist, file)

    return


def edit_ign(update, context):
    name = update.message.text
    context.user_data['IGN'] = name
    user_confirmation(update, context)
    return USER_CHOICE


def edit_leaderboard(update, context):
    bot = context.bot
    country = update.message.text.upper()
    user_id = update.message.from_user.id

    if len(country) > 2:
        bot.send_message(chat_id=user_id,
                         text="Only enter two letters")
        return EDIT_COUNTRY
    context.user_data['Country'] = country
    user_confirmation(update, context)
    return USER_CHOICE


def edit_stage(update, context):
    stage_finished = int(update.message.text)
    context.user_data['Stage'] = stage_finished
    percent_destroyed = context.user_data['Percentage'] / 100
    stage_finished = context.user_data['Stage'] + percent_destroyed
    context.user_data['Stage_Finished'] = stage_finished
    user_confirmation(update, context)
    return USER_CHOICE


def edit_destroyed(update, context):
    context.user_data['Percentage'] = float(update.message.text)
    percent_destroyed = float(update.message.text) / 100
    stage_finished = context.user_data['Stage'] + percent_destroyed
    context.user_data['Stage_Finished'] = stage_finished
    user_confirmation(update, context)
    return USER_CHOICE


def submitresults(update, context):
    bot = context.bot
    global oldsignuplist
    user_id = update.message.from_user.id
    username = update.message.from_user.name
    context.user_data['Username'] = username
    context.user_data['User_ID'] = user_id
    chat_id = update.message.chat_id

    if user_id != chat_id:
        bot.send_message(chat_id=user_id,
                         text="Hey, sorry. Send /submitresults again to me in this private chat. "
                              "It won't work in a group chat.")
        bot.delete_message(chat_id=chat_id,
                           message_id=update.message.message_id)
        return ConversationHandler.END

    ign_keyboard = []
    for user in oldsignuplist:
        if user[1] == user_id:
            ign_keyboard.append([InlineKeyboardButton(user[2], callback_data=user[2])])

    if len(ign_keyboard) == 0:
        bot.send_message(chat_id=user_id,
                         text="You must have an account signed up with CWAP to be able to submit results")

        return ConversationHandler.END

    ign_markup = InlineKeyboardMarkup(ign_keyboard)
    bot.send_message(chat_id=user_id,
                     text="Select your account",
                     reply_markup=ign_markup)

    return IGN


def ign(update, context):
    bot = context.bot
    query = update.callback_query
    user_id = query.from_user.id
    name = query.data
    context.user_data['IGN'] = name
    query.edit_message_text(text="Thanks! What stage did you finish on? Only enter whole numbers.")

    return STAGE


def stage(update, context):
    bot = context.bot
    user_id = update.message.from_user.id
    stage_finished = int(update.message.text)
    context.user_data['Stage'] = stage_finished
    bot.send_message(chat_id=user_id,
                     text="Thanks! What percent destroyed was stage {}? Enter as number (Ex: 50.4)"
                     .format(stage_finished))

    return DESTROY


def destroy(update, context):
    bot = context.bot
    global oldsignuplist
    user_id = update.message.from_user.id
    context.user_data['Percentage'] = float(update.message.text)
    percent_destroyed = float(update.message.text)/100
    stage_finished = context.user_data['Stage'] + percent_destroyed
    context.user_data['Stage_Finished'] = stage_finished
    local_keyboard = [[InlineKeyboardButton('Yes', callback_data='Yes'), InlineKeyboardButton('No', callback_data='No')]]
    local_markup = InlineKeyboardMarkup(local_keyboard)

    for user in oldsignuplist:
        if user[1] == user_id and user[2] == context.user_data['IGN']:
            country = user[3]
            context.user_data['Country'] = country.upper()

    bot.send_message(chat_id=user_id,
                     text="Thanks! Did this account finish number one in {}?".format(country.upper()),
                     reply_markup=local_markup)

    return LOCAL_NO


def local_no(update, context):
    query = update.callback_query
    context.user_data['Local_No_One'] = query.data
    user_confirmation(update, context)
    return USER_CHOICE


def user_confirmation(update, context):
    bot = context.bot
    user_data = context.user_data
    user_id = context.user_data['User_ID']

    confirmation_keyboard = [[InlineKeyboardButton('Confirm', callback_data='Confirm')],
                             [InlineKeyboardButton('Edit', callback_data='Edit')]]

    confirmation_markup = InlineKeyboardMarkup(confirmation_keyboard)

    bot.send_message(chat_id=user_id,
                     text="Please Confirm the following submission:\n\n"
                          "<code>IGN:</code> <b>{}</b> \n"
                          "<code>Local Leaderboard:</code> <b>{}</b> \n"
                          "<code>Stage:</code> <b>{}</b> \n"
                          "<code>Percent Destroyed:</code> <b>{}</b>\n"
                          "<code>Local Number One:</code> <b>{}</b> \n\n"
                          .format(user_data['IGN'], user_data['Country'], user_data['Stage'], user_data['Percentage'],
                                 user_data['Local_No_One']),
                     parse_mode='HTML',
                     reply_markup=confirmation_markup)

    return


def user_choice(update, context):
    bot = context.bot
    query = update.callback_query
    user_id = query.from_user.id
    the_choice = query.data
    user_data = context.user_data

    if the_choice == 'Confirm':
        confirmed(update, context)
    elif the_choice == 'Edit':
        edit_keyboard = [[InlineKeyboardButton('IGN', callback_data='IGN'), InlineKeyboardButton('Stage', callback_data='Stage'), InlineKeyboardButton('Percent Destroyed', callback_data='Destroyed')],
                         [InlineKeyboardButton('Local Leaderboard', callback_data='Local'), InlineKeyboardButton('Local Number One', callback_data='Local_no')],
                         [InlineKeyboardButton('Cancel', callback_data='Cancel')]]
        edit_markup = InlineKeyboardMarkup(edit_keyboard)
        bot.send_message(chat_id=user_id,
                         text="Select which item you want to change.",
                         reply_markup=edit_markup)
        return REDO

    return ConversationHandler.END


def confirmed(update, context):
    bot = context.bot
    query = update.callback_query
    user_id = query.from_user.id
    user_data = context.user_data

    user_results(user_data)
    bot.send_message(chat_id=user_id,
                     text="Thanks your results have been officialy submitted.")

    return


def edit_entry(update, context):
    query = update.callback_query
    response = query.data

    local_keyboard = [
        [InlineKeyboardButton('Yes', callback_data='Yes'), InlineKeyboardButton('No', callback_data='No')]]
    local_markup = InlineKeyboardMarkup(local_keyboard)

    if response == "IGN":
        query.edit_message_text(text="Enter your new IGN")
        return EDIT_IGN
    elif response == "Local":
        query.edit_message_text(text="Enter your countries two letter initials")
        return EDIT_COUNTRY
    elif response == "Stage":
        query.edit_message_text(text="Enter the stage you reached")
        return EDIT_STAGE
    elif response == "Destroyed":
        query.edit_message_text(text="Enter the amount destroyed")
        return EDIT_DESTROY
    elif response == "Local_no":
        query.edit_message_text(text="Did the account finish first in the country?",
                                reply_markup=local_markup)
        return LOCAL_NO
    elif response == "Cancel":
        user_confirmation(update, context)
        return USER_CHOICE

    return


results_handler = ConversationHandler(
        entry_points=[CommandHandler('submitresults', submitresults, (~Filters.update.edited_message))],
        states={
            IGN: [CallbackQueryHandler(ign, pass_user_data=True)],
            STAGE: [MessageHandler(Filters.text, stage, pass_user_data=True)],
            DESTROY: [MessageHandler(Filters.text, destroy, pass_user_data=True)],
            LOCAL_NO: [CallbackQueryHandler(local_no, pass_user_data=True)],
            USER_CHOICE: [CallbackQueryHandler(user_choice, pass_user_data=True)],
            REDO: [CallbackQueryHandler(edit_entry, pass_user_data=True)],
            EDIT_IGN: [MessageHandler(Filters.text, edit_ign, pass_user_data=True)],
            EDIT_COUNTRY: [MessageHandler(Filters.text, edit_leaderboard, pass_user_data=True)],
            EDIT_STAGE: [MessageHandler(Filters.text, edit_stage, pass_user_data=True)],
            EDIT_DESTROY: [MessageHandler(Filters.text, edit_destroyed, pass_user_data=True)],
            CANCEL: [CallbackQueryHandler(cancel, pass_user_data=True)],
        },
        fallbacks=[CommandHandler('cancel', cancel),
                   CallbackQueryHandler(cancel, pass_user_data=True)]
    )
dispatcher.add_handler(results_handler)

ACCOUNTS, PROCESS_CHOICE, UPDATE_SUBMISSION, CONFIRM_ENTRY, = range(4)


def editresults(update, context):
    bot = context.bot
    global resultslist
    user_id = update.message.from_user.id
    username = update.message.from_user.name
    context.user_data['Username'] = username
    context.user_data['User_ID'] = user_id
    chat_id = update.message.chat_id

    if user_id != chat_id:
        bot.send_message(chat_id=user_id,
                         text="Hey, sorry. Send /editresults again to me in this private chat. "
                              "It won't work in a group chat.")
        bot.delete_message(chat_id=chat_id,
                           message_id=update.message.message_id)
        return ConversationHandler.END

    ign_keyboard = []
    for user in resultslist:
        if user[1] == user_id:
            ign_keyboard.append([InlineKeyboardButton(user[2], callback_data=user[2])])

    ign_markup = InlineKeyboardMarkup(ign_keyboard)
    bot.send_message(chat_id=user_id,
                     text="Select the account you want to edit",
                     reply_markup=ign_markup)

    return ACCOUNTS


def the_options(update, context):
    bot = context.bot
    query = update.callback_query
    user_id = query.from_user.id
    the_old_account = query.data
    context.user_data['Old_IGN'] = the_old_account
    user_data = context.user_data

    edit_keyboard = [
        [InlineKeyboardButton('IGN', callback_data='IGN'), InlineKeyboardButton('Stage', callback_data='Stage'),
         InlineKeyboardButton('Percent Destroyed', callback_data='Percentage')],
        [InlineKeyboardButton('Local Leaderboard', callback_data='Country'),
         InlineKeyboardButton('Local Number One', callback_data='Local_No_One')],
        [InlineKeyboardButton('Cancel', callback_data='Cancel')]]
    edit_markup = InlineKeyboardMarkup(edit_keyboard)
    bot.send_message(chat_id=user_id,
                     text="Select which item you want to change.",
                     reply_markup=edit_markup)

    return PROCESS_CHOICE


def process_choice(update, context):
    bot = context.bot
    query = update.callback_query
    context.user_data['Data_To_Edit'] = query.data

    query.edit_message_text(text="Enter your new updated information.")

    return UPDATE_SUBMISSION


def update_submission(update, context):
    bot = context.bot
    global resultslist
    data_to_change = context.user_data['Data_To_Edit']
    corrected_data = update.message.text
    user_data = context.user_data

    for result in resultslist:
        if result[1] == user_data['User_ID'] and result[2] == user_data['Old_IGN']:
            user_data['Username'] = result[0]
            user_data['User_ID'] = result[1]
            user_data['IGN'] = result[2]
            user_data['Country'] = result[3]
            user_data['Stage_Finished'] = result[4]
            user_data['Stage'] = int(result[4])
            user_data['Percentage'] = round(((user_data['Stage_Finished'] - user_data['Stage']) * 100), 2)
            user_data['Local_No_One'] = result[5]

    if data_to_change == "Stage":
        context.user_data[data_to_change] = int(corrected_data)
        user_data['Stage_Finished'] = user_data['Stage'] + (user_data['Percentage'] / 100)
    elif data_to_change == "Percentage":
        context.user_data[data_to_change] = float(corrected_data)
        user_data['Stage_Finished'] = user_data['Stage'] + (user_data['Percentage'] / 100)
    else:
        context.user_data[data_to_change] = corrected_data

    user_confirmation(update, context)

    return CONFIRM_ENTRY


def edit_choice(update, context):
    bot = context.bot
    query = update.callback_query
    user_id = query.from_user.id
    the_choice = query.data
    user_data = context.user_data

    if the_choice == 'Confirm':
        edit_results(user_data)
        bot.send_message(chat_id=user_id,
                         text="Thanks your results have been updated")
    elif the_choice == 'Edit':
        edit_keyboard = [
            [InlineKeyboardButton('IGN', callback_data='IGN'), InlineKeyboardButton('Stage', callback_data='Stage'),
             InlineKeyboardButton('Percent Destroyed', callback_data='Destroyed')],
            [InlineKeyboardButton('Local Leaderboard', callback_data='Local'),
             InlineKeyboardButton('Local Number One', callback_data='Local_no')],
            [InlineKeyboardButton('Cancel', callback_data='Cancel')]]
        edit_markup = InlineKeyboardMarkup(edit_keyboard)
        bot.send_message(chat_id=user_id,
                         text="Select which item you want to change.",
                         reply_markup=edit_markup)
        return PROCESS_CHOICE

    return ConversationHandler.END


def edit_results(user_data):
    global resultslist
    user_result = []

    percent_destroyed = user_data['Percentage'] / 100
    stage_finished = user_data['Stage'] + percent_destroyed
    user_data['Stage_Finished'] = stage_finished

    for result in resultslist:
        if result[1] == user_data['User_ID'] and result[2] == user_data['Old_IGN']:
            index = resultslist.index(result)
            resultslist.remove(result)
            user_result.append(user_data['Username'])
            user_result.append(user_data['User_ID'])
            user_result.append(user_data['IGN'])
            user_result.append(user_data['Country'])
            user_result.append(user_data['Stage_Finished'])
            user_result.append(user_data['Local_No_One'])
            csv_data = "{},{},{},{},{},{},{}".format(user_data['Username'], user_data['Country'], user_data['IGN'],
                                                     user_data['Stage'], user_data['Percentage'], user_data['Stage_Finished'],
                                                     user_data['Local_No_One'])
            user_result.append(csv_data)
            resultslist.insert(index, user_result)

    with open("resultslist.txt", "wb") as file:
        pickle.dump(resultslist, file)

    return


editresults_handler = ConversationHandler(
    entry_points=[CommandHandler('editresults', editresults, (~Filters.update.edited_message))],
    states={
        ACCOUNTS: [CallbackQueryHandler(the_options, pass_user_data=True)],
        PROCESS_CHOICE: [CallbackQueryHandler(process_choice, pass_user_data=True)],
        UPDATE_SUBMISSION: [MessageHandler(Filters.text, update_submission, pass_user_data=True)],
        CONFIRM_ENTRY: [CallbackQueryHandler(edit_choice, pass_user_data=True)],
        CANCEL: [CallbackQueryHandler(cancel, pass_user_data=True)],
    },
    fallbacks=[CommandHandler('cancel', cancel),
               CallbackQueryHandler(cancel, pass_user_data=True)]
)
dispatcher.add_handler(editresults_handler)

ACCOUNT_REMOVAL = range(1)


def removeresults(update, context):
    bot = context.bot
    global resultslist
    user_id = update.message.from_user.id
    username = update.message.from_user.name
    context.user_data['Username'] = username
    context.user_data['User_ID'] = user_id
    chat_id = update.message.chat_id

    if user_id != chat_id:
        bot.send_message(chat_id=user_id,
                         text="Hey, sorry. Send /removeresults again to me in this private chat. "
                              "It won't work in a group chat.")
        bot.delete_message(chat_id=chat_id,
                           message_id=update.message.message_id)
        return ConversationHandler.END

    ign_keyboard = []
    for user in resultslist:
        if user[1] == user_id:
            ign_keyboard.append([InlineKeyboardButton(user[2]+' - '+str(user[4]), callback_data=user[2])])

    ign_keyboard.append([InlineKeyboardButton('Cancel', callback_data='Cancel')])

    ign_markup = InlineKeyboardMarkup(ign_keyboard)
    bot.send_message(chat_id=user_id,
                     text="Select the account you want to remove",
                     reply_markup=ign_markup)

    return ACCOUNT_REMOVAL


def remove_account(update, context):
    bot = context.bot
    query = update.callback_query
    account_to_remove = query.data
    user_id = context.user_data['User_ID']
    global resultslist

    for result in resultslist:
        if result[1] == user_id and result[2] == account_to_remove:
            resultslist.remove(result)

            with open("resultslist.txt", "wb") as file:
                pickle.dump(resultslist, file)

            bot.send_message(chat_id=user_id,
                             text="The account has been removed.")
            return ConversationHandler.END

    return ConversationHandler.END


removal_handler = ConversationHandler(
    entry_points=[CommandHandler('removeresults', removeresults, (~Filters.update.edited_message))],
    states={
        ACCOUNT_REMOVAL: [CallbackQueryHandler(remove_account, pass_user_data=True)],
        CANCEL: [CallbackQueryHandler(cancel, pass_user_data=True)],
    },
    fallbacks=[CommandHandler('cancel', cancel),
               CallbackQueryHandler(cancel, pass_user_data=True)]
)
dispatcher.add_handler(removal_handler)


def checkresults(update, context):
    bot=context.bot
    args=context.args
    global resultslist
    global cwap_id
    global authorized_status
    user_id = update.message.from_user.id
    user_ids = [user[1] for user in resultslist]
    username = update.message.from_user.name
    member_status = bot.get_chat_member(cwap_id, user_id).status

    if member_status not in authorized_status:
        bot.send_message(chat_id=user_id,
                         text="Hey {} this bot is only authorized for current members of CWAP\n\n"
                              "If you are interested in joining our group please contact one of our admin:"
                              "@scipio314, @jamarr91, @Pangtastic, @AndersenBB, or @Ichipmaker"
                         .format(username))

        bot.delete_message(chat_id=update.message.chat_id,
                           message_id=update.message.message_id)

        return

    if user_id not in user_ids:
        bot.send_message(chat_id=user_id,
                         text="Hey, this Telegram account doesn't have any results entered.\n"
                              "Use the /submitresults command to first submit results.")

        bot.delete_message(chat_id=update.message.chat_id,
                           message_id=update.message.message_id)

        return

    thetext = "You have entered the following results:\n\n"

    for entry in resultslist:
        if entry[1] == user_id:
            ign = entry[2]
            local_leaderboard = entry[3]
            stage_finished = entry[4]
            destroyed = stage_finished % 1
            stage = round(stage_finished - destroyed)
            destroyed_percentage = round(destroyed * 100, 2)
            local_number_one = entry[5]

            thetext += "<code>IGN:</code> <b>{}</b> \n" \
                       "<code>Local Leaderboard:</code> <b>{}</b> \n" \
                       "<code>Stage:</code> <b>{}</b> \n" \
                       "<code>Percent Destroyed:</code> <b>{}</b>\n" \
                       "<code>Local Number One:</code> <b>{}</b> \n\n"\
                .format(ign, local_leaderboard, stage, destroyed_percentage, local_number_one)

    thetext += "If there is a change needed use the /editresults command. If an account needs to be removed use " \
               "the /removeresults command. If you can't remember if you've signed up, use /checksignup command."

    bot.send_message(chat_id=user_id, text=thetext, parse_mode='HTML')

    bot.delete_message(chat_id=update.message.chat_id,
                       message_id=update.message.message_id)
    return


checkresults_handler = CommandHandler('checkresults', checkresults, (~Filters.update.edited_message))
dispatcher.add_handler(checkresults_handler)


def manualresults(update, context):
    bot=context.bot
    args=context.args
    global cwap_id
    global signuplist
    global oldsignuplist
    global resultslist
    global authorized_status
    username = update.message.from_user.name
    user_id = update.message.from_user.id
    member_status = bot.get_chat_member(cwap_id, user_id).status

    if member_status not in authorized_status:
        bot.send_message(chat_id=user_id,
                         text="Hey this bot is only authorized for current members of CWAP\n\n"
                              "If you are interested in joining our group please contact one of our admin:"
                              "@scipio314, @jamarr91, @Pangtastic, @AndersenBB, or @Ichipmaker")

        bot.delete_message(chat_id=update.message.chat_id,
                           message_id=update.message.message_id)
        return

    ign = args[0]
    stage_finished = float(args[1])
    if args[3].upper() == "YES":
        local_number_one = "Yes"
    else:
        local_number_one = "No"
    destroyed = stage_finished % 1
    stage = round(stage_finished - destroyed)
    destroyed_percentage = round(destroyed * 100, 2)
    local_leaderboard = args[2].upper()

    csv_data = "{},{},{},{},{},{},{}" \
        .format(username, local_leaderboard, ign, stage, destroyed_percentage, stage_finished, local_number_one)
    resultslist.append(
        [username, user_id, ign, local_leaderboard, stage_finished, local_number_one, csv_data])

    with open("resultslist.txt", "wb") as file:
        pickle.dump(resultslist, file)

    bot.send_message(chat_id=user_id,
                     text="Thanks! Your results have been saved with the following information:\n\n"
                          "<code>IGN:</code> <b>{}</b>\n"
                          "<code>Local Leaderboard:</code> <b>{}</b>\n"
                          "<code>Stage:</code> <b>{}</b>\n"
                          "<code>Percent Destroyed:</code> <b>{}</b>\n"
                          "<code>Local Number 1:</code> <b>{}</b>\n\n"
                          "If there is an error with that submission use the command\n"
                          "/editresults {} A XXX.XXX B C\n\n"
                          "<b>Replace A</b> with your correct in game name (no spaces).\n"
                          "<b>Replace XXX.XXX</b> with the correct stage finished.\n"
                          "<b>Replace B</b> with 'yes' if you're local number 1 and 'no' if not local number 1\n"
                          "<b>Replace C</b> with 'yes' if you want to automatically register it for next "
                          "Mega Crab or 'no' if you do not want to register it for next Mega Crab.\n\n"
                          "If you would like to sign this account up for next Mega Crab use the command:\n"
                          "/signup {} {} {} A\n "
                          "<b>Replace A</b> with 'yes' or 'no' if you want to help record videos or not\n\n"
                          "If you want to provide any feedback about the group (recordings, the livestream, or in "
                          "general) use the command /feedback to pass along any comments.\n\n"
                          "Thanks for playing with us and we are glad you can make it back for next month."
                     .format(ign, local_leaderboard, stage, destroyed_percentage, local_number_one, ign,
                             ign, local_leaderboard, stage_finished),
                     parse_mode='HTML')
    return


manualresults_handler = CommandHandler('manualresults', manualresults, (~Filters.update.edited_message))
dispatcher.add_handler(manualresults_handler)
