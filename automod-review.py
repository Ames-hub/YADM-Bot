print("Please select option:")
print("1 - Re-review all observations using current, modern automod.")
action = int(input(">>> "))

if action == 1:
    from library.database import observations
    from library import automod

    entries = observations.get_all_entries()

    bad_count = 0
    bad_entries = []
    for entry in entries:
        result = automod.text_check(entry.msg_content, observing=True)
        bad = result[0]
        if bad:
            bad_count += 1
            bad_entries.append(entry)
        observations.reeval_entry(entry.msg_id, result[3])

    print(f"Re-evaluated {len(entries)} from previously recorded messages. Found {bad_count} bad messages, {len(entries) - bad_count} good entries.")
    print("Print bad entries now?")
    a = input("Print? (y/n) >>> ")
    if a == "y":
        import subprocess
        for entry in bad_entries:
            entry: observations.observation_entry
            subprocess.run("clear")
            print(f"'{entry.msg_content}'")
            print(entry.bot_response.split(" | ")[0])
            input("...")
    else:
        exit(0)