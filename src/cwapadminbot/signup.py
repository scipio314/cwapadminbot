IGN_SIGNUP, COUNTRY_SIGNUP, STAGE_SIGNUP, DESTROY_SIGNUP, VIDEOSTAR_SIGNUP, CANCEL, AUTOSIGNUP_SIGNUP, SIGNUP_CONFIRM_SIGNUP, PROCESS_EDIT_SIGNUP, EDIT_INFORMATION_SIGNUP = range(10)


def cancel(update, context):
    return ConversationHandler.END


def save_signup(user_data):
    global signuplist
    user_signup = []
    # csv_data = "{},{},{},{},{},{}".format(username, ign, local_leaderboard, final_finish, video_star, task_force)
    #     signuplist.append(
    #         [username, user_id, ign, local_leaderboard, final_finish, video_star, task_force, csv_data])
    user_signup.append(user_data['Username'])
    user_signup.append(user_data['User_ID'])
    user_signup.append(user_data['IGN'])
    user_signup.append(user_data['Country'])
    user_signup.append(user_data['Stage_Finished'])
    user_signup.append(user_data['VIDEOSTAR'])
    user_signup.append('Unassigned')
    csv_data = "{},{},{},{},{},{}".format(user_data['Username'], user_data['IGN'], user_data['Country'],
                                          user_data['Stage_Finished'], user_data['VIDEOSTAR'], 'Unassigned')

    user_signup.append(csv_data)
    signuplist.append(user_signup)

    with open("signuplist.txt", "wb") as file:
        pickle.dump(signuplist, file)

    return


def signup(update, context):
    bot = context.bot
    global signuplist
    global resultslist
    global authorized_status
    global cwap_id
    global tutorial_id
    username = update.message.from_user.name
    user_id = update.message.from_user.id
    context.user_data['Username'] = username
    context.user_data['User_ID'] = user_id
    chat_id = update.message.chat_id
    user_data = context.user_data
    member_status = bot.get_chat_member(cwap_id, user_id).status
    tutorial_member_status = bot.get_chat_member(tutorial_id, user_id).status

    if user_id != chat_id:
        bot.send_message(chat_id=user_id,
                         text="Hey, sorry. Send /signup again to me in this private chat. "
                              "It won't work in a group chat.")
        bot.delete_message(chat_id=chat_id,
                           message_id=update.message.message_id)
        return ConversationHandler.END

    if member_status not in authorized_status and tutorial_member_status not in authorized_status:
        return

    ign_keyboard = []
    for result in resultslist:
        if result[1] == user_id:
            ign_keyboard.append([InlineKeyboardButton(result[2], callback_data=result[2])])

    if len(ign_keyboard) == 0:
        bot.send_message(chat_id=user_id,
                         text="What is the account name?")
        return IGN_SIGNUP
    else:
        ign_keyboard.append([InlineKeyboardButton('Other', callback_data='Other')])
        ign_markup = InlineKeyboardMarkup(ign_keyboard)
        bot.send_message(chat_id=user_id,
                         text="Select your account",
                         reply_markup=ign_markup)

    return AUTOSIGNUP_SIGNUP


def auto_signup(update, context):
    bot = context.bot
    global resultslist
    query = update.callback_query
    user_id = query.from_user.id
    username = query.from_user.name
    user_data = context.user_data
    name = query.data
    user_data['Old_IGN'] = name

    if name == "Other":
        bot.send_message(chat_id=user_id,
                         text="What is the account name?")
        return IGN_SIGNUP

    for result in resultslist:
        if result[2] == name:
            user_data['IGN'] = name
            user_data['Country'] = result[3]
            user_data['Stage_Finished'] = result[4]

    volunteer_keyboard = [
        [InlineKeyboardButton('Yes', callback_data='Yes'), InlineKeyboardButton('No', callback_data='No')]]
    volunteer_markup = InlineKeyboardMarkup(volunteer_keyboard)

    bot.send_message(chat_id=user_id,
                     text="Are you interested in volunteering to record and upload attacks to Telegram? "
                          "Uploading 10 videos guarantees a place next Mega Crab.",
                     reply_markup=volunteer_markup)

    return VIDEOSTAR_SIGNUP


def signup_ign(update, context):
    bot = context.bot
    name = update.message.text
    context.user_data['IGN'] = name
    user_id = update.message.from_user.id

    bot.send_message(chat_id=user_id,
                     text="What is the accounts local leaderboard? (Enter the two letter initials)")

    return COUNTRY_SIGNUP


def signup_country(update, context):
    bot = context.bot
    local_leaderboard = update.message.text.upper()
    context.user_data['Country'] = local_leaderboard
    user_id = update.message.from_user.id

    bot.send_message(chat_id=user_id,
                     text="What stage did you finish on? Only enter whole numbers.")

    return STAGE_SIGNUP


def signup_stage(update, context):
    bot = context.bot
    user_id = update.message.from_user.id
    stage_finished = int(update.message.text)
    context.user_data['Stage'] = stage_finished
    bot.send_message(chat_id=user_id,
                     text="Thanks! What percent destroyed was stage {}? Enter as number (Ex: 50.4)"
                     .format(stage_finished))

    return DESTROY_SIGNUP


def signup_destroy(update, context):
    bot = context.bot
    global oldsignuplist
    user_id = update.message.from_user.id
    context.user_data['Percentage'] = float(update.message.text)
    percent_destroyed = float(update.message.text) / 100
    stage_finished = context.user_data['Stage'] + percent_destroyed
    context.user_data['Stage_Finished'] = stage_finished
    volunteer_keyboard = [
        [InlineKeyboardButton('Yes', callback_data='Yes'), InlineKeyboardButton('No', callback_data='No')]]
    volunteer_markup = InlineKeyboardMarkup(volunteer_keyboard)

    bot.send_message(chat_id=user_id,
                     text="Are you interested in volunteering to record and upload attacks to Telegram? "
                          "Uploading 10 videos guarantees a place next Mega Crab.",
                     reply_markup=volunteer_markup)

    return VIDEOSTAR_SIGNUP


def signup_volunteer(update, context):
    query = update.callback_query
    context.user_data['VIDEOSTAR'] = query.data
    signup_confirmation(update, context)
    return SIGNUP_CONFIRM_SIGNUP


def signup_confirmation(update, context):
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
                          "<code>Previous Finish:</code> <b>{}</b> \n"
                          "<code>Recording Volunteer:</code> <b>{}</b> \n\n"
                     .format(user_data['IGN'], user_data['Country'], user_data['Stage_Finished'], user_data['VIDEOSTAR']),
                     parse_mode='HTML',
                     reply_markup=confirmation_markup)

    return


def user_confirm(update, context):
    bot = context.bot
    query = update.callback_query
    user_id = query.from_user.id
    the_choice = query.data
    user_data = context.user_data

    if the_choice == 'Confirm':
        save_signup(user_data)
        bot.send_message(chat_id=user_id,
                         text="Thanks your signup has been saved.")
    elif the_choice == 'Edit':
        edit_keyboard = [
            [InlineKeyboardButton('IGN', callback_data='IGN'), InlineKeyboardButton('Stage', callback_data='Stage'),
             InlineKeyboardButton('Percent Destroyed', callback_data='Percentage')],
            [InlineKeyboardButton('Local Leaderboard', callback_data='Country'),
             InlineKeyboardButton('Recording Volunteer', callback_data='VIDEOSTAR')],
            [InlineKeyboardButton('Cancel', callback_data='Cancel')]]
        edit_markup = InlineKeyboardMarkup(edit_keyboard)
        bot.send_message(chat_id=user_id,
                         text="Select which item you want to change.",
                         reply_markup=edit_markup)
        return PROCESS_EDIT_SIGNUP

    return ConversationHandler.END


def process_edit(update, context):
    bot = context.bot
    query = update.callback_query
    context.user_data['Data_To_Edit'] = query.data

    query.edit_message_text(text="Enter your new updated information.")

    return EDIT_INFORMATION_SIGNUP


def update_signup(update, context):
    bot = context.bot
    global resultslist
    data_to_change = context.user_data['Data_To_Edit']
    corrected_data = update.message.text
    user_data = context.user_data

    # for result in resultslist:
    #     if result[1] == user_data['User_ID'] and result[2] == user_data['Old_IGN']:
    #         user_data['Username'] = result[0]
    #         user_data['User_ID'] = result[1]
    #         user_data['IGN'] = result[2]
    #         user_data['Country'] = result[3]
    #         user_data['Stage_Finished'] = result[4]
    #         user_data['Stage'] = int(result[4])
    #         user_data['Percentage'] = round(((user_data['Stage_Finished'] - user_data['Stage']) * 100), 2)
    #         user_data['Local_No_One'] = result[5]

    if data_to_change == "Stage":
        user_data['Stage'] = int(user_data['Stage_Finished'])
        user_data['Percentage'] = round(((user_data['Stage_Finished'] - user_data['Stage']) * 100), 2)
        context.user_data[data_to_change] = int(corrected_data)
        user_data['Stage_Finished'] = user_data['Stage'] + (user_data['Percentage'] / 100)
    elif data_to_change == "Percentage":
        user_data['Stage'] = int(user_data['Stage_Finished'])
        user_data['Percentage'] = round(((user_data['Stage_Finished'] - user_data['Stage']) * 100), 2)
        context.user_data[data_to_change] = float(corrected_data)
        user_data['Stage_Finished'] = user_data['Stage'] + (user_data['Percentage'] / 100)
    else:
        context.user_data[data_to_change] = corrected_data

    signup_confirmation(update, context)

    return SIGNUP_CONFIRM_SIGNUP


signup_handler = ConversationHandler(
        entry_points=[CommandHandler('signup', signup, (~Filters.update.edited_message))],
        states={
            IGN_SIGNUP: [MessageHandler(Filters.text, signup_ign, pass_user_data=True)],
            COUNTRY_SIGNUP: [MessageHandler(Filters.text, signup_country, pass_user_data=True)],
            STAGE_SIGNUP: [MessageHandler(Filters.text, signup_stage, pass_user_data=True)],
            DESTROY_SIGNUP: [MessageHandler(Filters.text, signup_destroy, pass_user_data=True)],
            VIDEOSTAR_SIGNUP: [CallbackQueryHandler(signup_volunteer, pass_user_data=True)],
            SIGNUP_CONFIRM_SIGNUP: [CallbackQueryHandler(user_confirm, pass_user_data=True)],
            AUTOSIGNUP_SIGNUP: [CallbackQueryHandler(auto_signup, pass_user_data=True)],
            PROCESS_EDIT_SIGNUP: [CallbackQueryHandler(process_edit, pass_user_data=True)],
            EDIT_INFORMATION_SIGNUP: [MessageHandler(Filters.text, update_signup, pass_user_data=True)],
        },
    fallbacks=[CommandHandler('cancel', cancel),
               CallbackQueryHandler(cancel, pass_user_data=True)]
    )
dispatcher.add_handler(signup_handler)

ACCOUNT_REMOVAL = range(1)


def removesignup(update, context):
    bot = context.bot
    global signuplist
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
    for user in signuplist:
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
    global signuplist

    for result in signuplist:
        if result[1] == user_id and result[2] == account_to_remove:
            signuplist.remove(result)
            with open("signuplist.txt", "wb") as file:
                pickle.dump(signuplist, file)

            bot.send_message(chat_id=user_id,
                             text="The account has been removed.")

            return ConversationHandler.END

    return ConversationHandler.END


removesignup_handler = ConversationHandler(
    entry_points=[CommandHandler('removesignup', removesignup, (~Filters.update.edited_message))],
    states={
        ACCOUNT_REMOVAL: [CallbackQueryHandler(remove_account, pass_user_data=True)],
        CANCEL: [CallbackQueryHandler(cancel, pass_user_data=True)],
    },
    fallbacks=[CommandHandler('cancel', cancel),
               CallbackQueryHandler(cancel, pass_user_data=True)]
)
dispatcher.add_handler(removesignup_handler)


def checksignup(update, context):
    bot=context.bot
    args=context.args
    global signuplist
    global cwap_id
    global authorized_status
    global admin_status
    global tutorial_id
    global oldsignuplist
    user_id = update.message.from_user.id
    user_ids = [user[1] for user in signuplist]
    username = update.message.from_user.name
    member_status = bot.get_chat_member(cwap_id, user_id).status
    tutorial_status = bot.get_chat_member(tutorial_id, user_id).status

    if member_status not in authorized_status and tutorial_status not in authorized_status:
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
                         text="Hey, this Telegram account doesn't have any accounts signed up.\n"
                              "Use the /signup command to enter an account.")

        bot.delete_message(chat_id=update.message.chat_id,
                           message_id=update.message.message_id)

        return

    thetext = "You are signed up with the following accounts:\n\n"

    for entry in signuplist:
        if entry[1] == user_id:
            if entry[5]:
                volunteer_recorder = "Yes"
            else:
                volunteer_recorder = "No"

            thetext += "<code>IGN:</code> <b>{}</b> \n" \
                       "<code>Local Leaderboard:</code> <b>{}</b> \n" \
                       "<code>Previous Finish:</code> <b>{}</b> \n" \
                       "<code>Volunteer Recorder:</code> <b>{}</b> \n\n"\
                .format(entry[2], entry[3], entry[4], volunteer_recorder)

    thetext += "If there is a change needed use the /editsignup command. If an account needs to be removed use " \
               "the /removesignup command.\n\n" \
               "Stay tuned for task force assignments"

    bot.send_message(chat_id=user_id, text=thetext, parse_mode='HTML')

    bot.delete_message(chat_id=update.message.chat_id,
                       message_id=update.message.message_id)

    return


checksignup_handler = CommandHandler('checksignup', checksignup, (~Filters.update.edited_message))
dispatcher.add_handler(checksignup_handler)

