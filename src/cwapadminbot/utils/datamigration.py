"""A module to convert old data format to the new data format."""
import pickle
import time

import yaml
from telegram import Bot as tgbot

with open('../config.yaml', 'r') as file:
    config = yaml.safe_load(file)


def load_list(list):
    """Function to load specific list"""
    with open("../data/{}.txt".format(list), "rb") as file:
        the_list = pickle.load(file)
    return the_list


def load_all_old_lists():
    """Function to load all old data"""
    with open("../data/signuplist.txt", "rb") as file:
        signups = pickle.load(file)

    with open("../data/resultslist.txt", "rb") as file:
        results = pickle.load(file)

    with open("../data/allmemberslist.txt", "rb") as file:
        members = pickle.load(file)

    with open("../data/oldsignupslist.txt", "rb") as file:
        oldsignups = pickle.load(file)

    with open("../data/joinrequests.txt", "rb") as file:
        joinrequests = pickle.load(file)

    with open("../data/feedback.txt", "rb") as file:
        feedback = pickle.load(file)

    with open("../data/videostarspickle.txt", "rb") as file:
        videostars = pickle.load(file)

    with open("../data/requestspickle.txt", "rb") as file:
        requests = pickle.load(file)

    lists = {
        "signups": signups,
        "results": results,
        "members": members,
        "oldsignups": oldsignups,
        "joinrequests": joinrequests,
        "feedback": feedback,
        "videostars": videostars,
        "requests": requests,
    }
    return lists


def migrate_members():
    old_members = load_list(list="allmemberslist")
    new_members = {}
    new_members["all_ids"] = []
    new_members["all_usernames"] = []
    new_members["boot_ids"] = []
    bot = tgbot(token=config["TOKEN"])

    for member in old_members:
        user_id = member[1]
        username = member[0]
        # admin_usernames = ["@scipio314", "@CasselAF", "@AndersenBB", "@MrOrland", "Major_DeCoverly", "@Ichipmaker", "@Jamarr91", "@Lamm3rgeier"]

        try:
            time.sleep(2)
            status = bot.get_chat_member(config["GROUPS"]["crab_wiv_a_plan"], user_id).status
        except:
            status = "member"
            print(f"{username}")

        if status in ["creator", "administrator"]:
            admin = True
        else:
            admin = False
        new_member = {
            user_id: {
                "user_id": user_id,
                "username": username,
                "authorized": True,
                "is_admin": admin,
                "signed_up": False,
                "signup_data": [],
            }
        }

        new_members.update(new_member)
        new_members["all_ids"].append(user_id)
        new_members["all_usernames"].append(username)
        new_members["boot_ids"].append(user_id)

    with open("../data/members.txt", "wb") as file:
        pickle.dump(new_members, file)

    return new_members


def migrate_signups():
    """Migrate old signup format to the new one."""
    old_signups = load_list(list="signuplist")
    new_members = migrate_members()

    # [username, user_id, IGN, Country, Stage, Volunteer, CSV]

    for signup in old_signups:
        user_id = signup[1]
        username = signup[0]
        ign = signup[2]
        videostar = signup[5]
        csv = "{},{},{}".format(username, ign, videostar)

        signup_data = {
            "IGN": ign,
            "VIDEOSTAR": videostar,
            "CSV": csv
        }
        if user_id not in new_members["all_ids"]:
            print(f"{username}")
            continue
        new_members[user_id]["signup_data"].append(signup_data)
        new_members[user_id]["signed_up"] = True

        try:
            new_members["boot_ids"].remove(user_id)
        except ValueError:
            continue

    return new_members


if __name__ == '__main__':
    migrate_members()
