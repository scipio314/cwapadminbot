"""This module contains helper functions."""
import pickle
import uuid


def _dump(name, data):
    with open("./data/{}.txt".format(name), "wb") as file:
        pickle.dump(data, file)


def loadlists():
    """Function to load all data"""
    with open("./data/members.txt", "rb") as file:
        members = pickle.load(file)

    with open("./data/signups.txt", "rb") as file:
        signups = pickle.load(file)

    with open("./data/joinrequests.txt", "rb") as file:
        joinrequests = pickle.load(file)

    with open("./data/feedback.txt", "rb") as file:
        feedback = pickle.load(file)

    with open("./data/videostarspickle.txt", "rb") as file:
        videostars = pickle.load(file)

    lists = {
        "members": members,
        "joinrequests": joinrequests,
        "feedback": feedback,
        "videostars": videostars,
        "signups": signups,
    }
    return lists


def add_member(username, user_id):
    """Add a new CWAP member to data."""
    lists = loadlists()

    members = lists["members"]

    if user_id in members["all_ids"]:
        return

    members["all_ids"].append(user_id)
    members["all_usernames"].append(username)
    members["boot_ids"].append(user_id)

    new_member = {
        user_id: {
            "user_id": user_id,
            "username": username,
            "authorized": True,
            "is_admin": False,
            "signed_up": False,
            "signup_data": [],
        }
    }

    members["users"].update(new_member)

    _dump(name="members", data=members)


def remove_member(user_id):
    """Remove a CWAP member from data."""
    lists = loadlists()
    signups = lists["signups"]
    all_signup_ids = lists["signups"].keys()
    users = lists["members"]["users"]

    username = users[user_id]["username"]

    lists["members"]["all_ids"].remove(user_id)
    lists["members"]["all_usernames"].remove(username)

    if user_id in lists["members"]["boot_ids"]:
        lists["members"]["boot_ids"].remove(user_id)

    if user_id in lists["members"]["signup_ids"]:
        user_signup_ids = []
        for signup in lists["members"][user_id]["signup_data"]:
            user_signup_ids.append(signup["UUID"])

        signups = [signups.pop(signup_id, None) for signup_id in all_signup_ids if signup_id in user_signup_ids]
        lists["members"]["signup_ids"].remove(user_id)

    users.pop(user_id, None)

    _dump(name="members", data=users)
    _dump(name="signups", data=signups)


def signup_user(user_data):
    """Log signup data for user."""
    user_id = user_data['User_ID']
    lists = loadlists()
    members = lists["members"]
    signups = lists["signups"]

    if user_id not in members["all_ids"]:
        add_member(user_data['Username'], user_id)
        lists = loadlists()
        members = lists["members"]

    members["users"][user_id]["signed_up"] = True
    if user_id in members["boot_ids"]:
        members["boot_ids"].remove(user_id)

    if user_id not in members["signup_ids"]:
        members["signup_ids"].append(user_id)

    csv = "{},{},{}".format(user_data['Username'], user_data['IGN'], user_data['VIDEOSTAR'])
    signup_id = uuid.uuid4()

    signup_data = {
        "IGN": user_data['IGN'],
        "VIDEOSTAR": user_data["VIDEOSTAR"],
        "CSV": csv,
        "UUID": signup_id,
    }
    members["users"][user_id]["signup_data"].append(signup_data)
    signups[signup_id] = signup_data
    _dump(name="members", data=members)
    _dump(name="signups", data=signups)


def _in_group(context, user_id, group_id):
    """Checks if member is in the tutorial room."""
    bot = context.bot
    try:
        status = bot.get_chat_member(group_id, user_id).status
    except:
        return False
    member_status = ['creator', 'administrator', 'member']
    return status in member_status


def _authorized(user_id):
    members = loadlists()["members"]
    try:
        authorized = members["users"][user_id]["authorized"]
    except KeyError:
        authorized = False
    return authorized


def _admin(user_id):
    members = loadlists()["members"]
    try:
        admin = members["users"][user_id]["is_admin"]
    except KeyError:
        admin = False
    return admin
