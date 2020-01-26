"""This module contains helper functions."""
import pickle


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

    all_ids = lists["members"]["all_ids"]

    if user_id in all_ids:
        return

    lists["members"]["all_ids"].append(user_id)
    lists["members"]["all_usernames"].append(username)

    all_members = {
        user_id: {
            "user_id": user_id,
            "username": username,
            "authorized": True,
        }
    }

    with open("all_members.txt", "wb") as file:
        pickle.dump(all_members, file)
    return


def remove_member(user_id):
    """Remove a CWAP member from data."""
    lists = loadlists()

    all_ids = lists["members"]["all_ids"]

    if user_id not in all_ids:
        return

    username = lists["members"][user_id]["username"]

    lists["members"]["all_ids"].remove(user_id)
    lists["members"]["all_usernames"].remove(username)
    lists["members"]["boot_ids"].remove(user_id)

    lists["members"].pop(user_id, None)

    all_members = lists["members"]

    with open("all_members.txt", "wb") as file:
        pickle.dump(all_members, file)
    return
