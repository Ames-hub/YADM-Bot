from library.database import observations
from datetime import datetime, timedelta
from library import automod
import subprocess

def clean_whitelist_file():
    """
    This function removes duplicates from the library/preset_word_whitelist.txt file, and removes exact matches from the whitelist if they are in
    The bad words list.
    """
    bad_word_list = automod.get_bad_word_list(guild_id=None)
    old_whitelist = automod.PRESET_WORD_WHITELIST
    new_whitelist = []
    removal_list = []
    progress_indicator = 0
    for word in old_whitelist:
        print(f"Beginning to clean whitelist file. This can take a while as we scan through all {len(old_whitelist)} entries.")
        print(f"Progress: {progress_indicator}/{len(old_whitelist)}")
        progress_indicator += 1
        subprocess.run("clear")
        if word in bad_word_list:
            removal_list.append(word, "Bad Word")
            continue  # Do not add it
        elif word in new_whitelist:
            removal_list.append((word, "Duplicate"))  
            continue  # Do not add it, as its a duplicate.
        else:
            new_whitelist.append(word)

    with open("library/preset_word_whitelist.txt", "w") as f:
        f.write("\n".join(new_whitelist))

    for item in removal_list:
        print(f"REMOVED: \"{item[0]}\" due to \"{item[1]}\"")
    print(f"Whitelist cleaned, removed {len(removal_list)} items.")
    return True

def review_bad_messages(bad_entries: list[observations.observation_entry]):
    progress = 1
    bad_entries_count = len(bad_entries)
    for entry in bad_entries:
        subprocess.run("clear")
        print(f"MSG ID: {entry.msg_id}\n\n'{entry.msg_content}' ({progress}/{bad_entries_count})")
        if entry.bot_response:
            print(entry.bot_response.split(" | ")[0])
        progress += 1
        if entry.confirmed:
            print(f"! This message was previously marked as {'rule-violating!' if entry.bad_message else 'clean!'} !")
            if entry.bad_message and entry.bot_response == None:
                # This means it was confirmed bad, but now the bot response has been removed, indicating it was false-negatived.
                print("This message was false-negatived!")
            elif entry.bad_message is False and entry.bot_response is not None:
                # This means it was confirmed good, but now the bot has re-scanned and did something to it, meaning it was false-positived.
                print("This message was false-positived!")
            input("...")  # Wait to continue
            continue
        else:
            if "equality Check" in entry.bot_response:
                # Equality check can quite literally not be wrong. Its too basic to fail. So, we auto-confirm the item.
                observations.reeval_entry(
                    entry.msg_id,
                    new_conclusion=entry.bot_response,
                    mark_for_review=False,
                    do_confirm=True,
                    bad_msg=True
                )
                print("Auto-assigned as bad, due to equality check being incapable of false-positives.")
                continue
            while True:  # Retry logic
                print(f"\nAction taken: {"RULE-BREAKING" if entry.bot_response else "CLEAN"}")
                confirmed = input("Correct? (y/n) >>> ").lower()
                if confirmed == "y":
                    bad_msg = True if entry.bot_response else False
                    observations.reeval_entry(
                        entry.msg_id,
                        new_conclusion=entry.bot_response,
                        mark_for_review=False,
                        do_confirm=True,
                        bad_msg=bad_msg
                    )
                    break
                elif confirmed == "n":
                    bad_msg = True if entry.bot_response else False
                    observations.reeval_entry(
                        entry.msg_id,
                        new_conclusion=entry.bot_response,
                        mark_for_review=False,
                        do_confirm=True,
                        bad_msg=bad_msg
                    )
                    break
                else:
                    print("Wrong answer!")
                    continue


while True:
    print("Please select option:")
    print("0 - Exit")
    print("1 - Re-review all observations using current, modern automod.")
    print("2 - Check a specific line of text.")
    print("3 - Review flagged for review messages.")
    print("4 - Clean the whitelist file of bad entries.")
    action = int(input(">>> "))

    if action == 0:
        break
    elif action == 1:
        entries = observations.get_all_entries()

        bad_count = 0
        bad_entries: list[observations.observation_entry] = []
        start_time = datetime.now().timestamp()
        for entry in entries:
            result = automod.text_check(entry.msg_content, observing=True)
            bad = result[0]
            if bad:
                check_name = result[1]
                flagged_word = result[2]

                bad_count += 1
                bad_entries.append(entry)
                success = observations.reeval_entry(
                    msg_id=entry.msg_id,
                    new_conclusion=f"Message was detected as bad by {check_name} Check, catching \"{flagged_word}\" | {result[3]}",
                    mark_for_review=True,
                )
                if not success:
                    input(f"FAILED TO UPDATE ROW FOR MSG ID {entry.msg_id}")
                continue
            success = observations.reeval_entry(entry.msg_id, None, mark_for_review=False)
            if not success:
                input(f"FAILED TO UPDATE ROW FOR MSG ID {entry.msg_id}")

        end_time = datetime.now().timestamp()
        run_time = timedelta(seconds=(datetime.fromtimestamp(end_time) - datetime.fromtimestamp(start_time)).total_seconds())

        print(f"Re-evaluated {len(entries)} from previously recorded messages in {run_time}.")
        print(f"Found {bad_count} bad messages, {len(entries) - bad_count} good entries.")
        print("Print bad entries now?")
        a = input("Print? (y/n) >>> ")
        if a == "y":
            review_bad_messages(bad_entries)
        else:
            exit(0)
    elif action == 2:
        print("\n")
        print(automod.text_check(input("test-data >>> ")))
    elif action == 3:
        bad_entries = observations.get_all_entries(review_flagged_only=True)
        if not bad_entries:
            print("No bad entries.")
            continue
        review_bad_messages(bad_entries)
    elif action == 4:
        clean_whitelist_file()
        print("Whitelist file cleaned.")