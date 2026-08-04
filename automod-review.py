from library import automod

print("Please select option:")
print("1 - Re-review all observations using current, modern automod.")
print("2 - Check a specific line of text")
action = int(input(">>> "))

if action == 1:
    from library.database import observations

    entries = observations.get_all_entries()

    bad_count = 0
    bad_entries = []
    for entry in entries:
        result = automod.text_check(entry.msg_content, observing=True)
        bad = result[0]
        if bad:
            check_name = result[1]
            flagged_word = result[2]

            bad_count += 1
            bad_entries.append(entry)
            success = observations.reeval_entry(entry.msg_id, f"Message was detected as bad by {check_name} Check, catching \"{flagged_word}\" | {result[3]}")
            if not success:
                input(f"FAILED TO UPDATE ROW FOR MSG ID {entry.msg_id}")
            continue
        success = observations.reeval_entry(entry.msg_id, None)
        if not success:
            input(f"FAILED TO UPDATE ROW FOR MSG ID {entry.msg_id}")

    print(f"Re-evaluated {len(entries)} from previously recorded messages. Found {bad_count} bad messages, {len(entries) - bad_count} good entries.")
    print("Print bad entries now?")
    a = input("Print? (y/n) >>> ")
    if a == "y":
        import subprocess
        for entry in bad_entries:
            entry: observations.observation_entry
            subprocess.run("clear")
            print(f"'{entry.msg_content}'")
            if entry.bot_response:
                print(entry.bot_response.split(" | ")[0])
            input("...")
    else:
        exit(0)
elif action == 2:
    print("\n")
    print(automod.text_check(input("test-data >>> ")))