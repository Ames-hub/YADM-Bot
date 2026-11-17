from library import datastore as ds

def calc_exp_earned(msg_length:int):
    # You get more points for every 50 characters in the message
    # Gets how many times the text content len goes into 50, then multiplies by 5.
    # Always returns 5 at minimum.
    value = max((msg_length // 50) * 5, 5)
    if value > 50:
        value = 50
    return value

def is_user_spamming(guild_id: int, user_id: int) -> bool:
    if not ds.d["spam_punish_cache"].get(guild_id):
        return False
    last_punish_time = ds.d["spam_punish_cache"][guild_id].get(user_id)
    if last_punish_time is not None:
        return True
    else:
        return False