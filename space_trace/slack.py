from typing import Dict

from slack_bolt import App

from space_trace import app


def get_slack_handle_table() -> Dict[str, str]:
    """Returns a dictionary that maps email adresses to Slack handles.

    TODO: Currently this will not fetch users from the racing team.

    Note: This table will be incomplete.
    """

    slack_app = App(token=app.config["SLACK_USER_TOKEN"])
    users = slack_app.client.users_list().data["members"]

    table = {}
    for user in users:
        try:
            email = user["profile"]["email"]
        except KeyError:
            continue

        handle = user["profile"]["display_name"]
        if handle == "":
            handle = user["profile"]["real_name"]
        table[email] = "@" + handle

    return table
