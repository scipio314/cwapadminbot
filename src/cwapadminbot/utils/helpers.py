"""This module contains helper functions."""
import pickle


def _dump(members):
    with open("members.txt", "wb") as file:
        pickle.dump(members, file)


def loadlists():
    """Function to load all data"""
    with open("signups.txt", "rb") as file:
        signups = pickle.load(file)

    with open("results.txt", "rb") as file:
        results = pickle.load(file)

    with open("members.txt", "rb") as file:
        members = pickle.load(file)

    with open("oldsignups.txt", "rb") as file:
        oldsignups = pickle.load(file)

    with open("joinrequests.txt", "rb") as file:
        joinrequests = pickle.load(file)

    with open("feedback.txt", "rb") as file:
        feedback = pickle.load(file)

    with open("videostarspickle.txt", "rb") as file:
        videostars = pickle.load(file)

    lists = {
        "signups": signups,
        "results": results,
        "members": members,
        "oldsignups": oldsignups,
        "joinrequests": joinrequests,
        "feedback": feedback,
        "videostars": videostars,
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

    members.update(new_member)

    _dump(members)


def remove_member(user_id):
    """Remove a CWAP member from data."""
    lists = loadlists()

    username = lists["members"][user_id]["username"]

    lists["members"]["all_ids"].remove(user_id)
    lists["members"]["all_usernames"].remove(username)

    if user_id in lists["members"]["boot_ids"]:
        lists["members"]["boot_ids"].remove(user_id)

    lists["members"].pop(user_id, None)

    members = lists["members"]

    _dump(members)


def signup_user(user_data):
    """Log signup data for user."""
    user_id = user_data['User_ID']
    lists = loadlists()
    members = lists["members"]

    if user_id not in members["all_ids"]:
        add_member(user_data['Username'], user_id)
        lists = loadlists()
        members = lists["members"]

    members[user_id]["signed_up"] = True
    members["boot_ids"].remove(user_id)

    csv = "{},{},{}".format(user_data['Username'], user_data['IGN'], user_data['VIDEOSTAR'])

    signup_data = {
        "IGN": user_data['IGN'],
        "VIDEOSTAR": user_data["VIDEOSTAR"],
        "CSV": csv
    }
    members[user_id]["signup_data"].append(signup_data)
    _dump(members)


def _in_group(context, user_id, group_id):
    """Checks if member is in the tutorial room."""
    bot = context.bot
    try:
        status = bot.get_chat_member(group_id, user_id).status
    except:
        return False
    member_status = ['creator', 'administrator', 'member']
    return status in member_status
