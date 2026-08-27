# Nodeus Discord Bot

A comprehensive moderation and server management bot for Discord, featuring advanced text filtering, Ethical AI-powered image moderation, automated punishments, and extremely extensive customization options.

Nodeus is, at its core, a moderation bot. That's what it's built for. But that's not to say it can't do anything else! This is the first moderation bot I've decided to take seriously, so here you go!

---

## Features at a Glance

| Category | What Nodeus Does |
|----------|------------------|
| **Text Automod** | 8 different checks to catch bad words, even clever evasion attempts. Context-aware filtering understands the difference between "Omg I'm an idiot" and "Omg you're an idiot"! |
| **Image Filtering** | Privacy-focused AI that detects NSFW images locally. You control the sensitivity! |
| **Spam Protection** | Automatically detects and stops message spam with configurable actions. |
| **Moderation Commands** | Mute, kick, ban, purge, lockdown, warnings -- all with temporary options and auto-expiry. |
| **Welcomer** | Greet new members with custom messages and placeholders. |
| **Join Roles** | Automatically assign roles to new members as soon as they join. |
| **Audit Logging** | Detailed logs in a dedicated channel, plus database archives. |
| **Interactive Menus** | Configure everything with buttons, no complicated commands to remember! |
| **Easy Setup** | Run `/setup` once and Nodeus applies recommended settings, tweak them anytime later. |

---

## Advanced Moderation Features

### Text Content Filtering

Nodeus uses **8 different heuristic checks** to catch inappropriate language, even when users try to be clever and evade the system:

| Check Level | Name | What It Catches |
|-------------|------|-----------------|
| **Low** | Equality Check | Direct word matching against a blacklist |
| **Low** | Symbol Check | Words hidden with symbols (eg, "f!oo@b#ar") and basic leetspeak |
| **Low** | Collapsed Check | Exaggerated words ("sweeeeeeeaarr" -> "swear") |
| **Medium** | Spacehack Detection | Words split with spaces (eg, "s w e a r") |
| **Medium** | Letter Stitching | Spaced-out letters reassembled into words |
| **Medium** | Reverse Check | Reversed words ("ruls" -> "slur") |
| **High** | Similarity Matching | 85%+ similarity threshold (catches "baddword" vs "badword") |
| **High** | Syntactic Analysis | **Context-aware!** Distinguishes self-insults from attacks on others. Not AI, but borderline. |

Every single check can be toggled on or off. Don't like one? Just turn it off in the menu!

### Image Moderation

> **A note on AI:** There's much discourse about Generative AI. Nodeus uses **Discriminative AI**, the same technology your phone uses to focus on faces in photos. It's lightweight, private, and runs locally. If you're heavily against AI, I ask you at least read this section before leaving.

- **Privacy-Focused** -- All image scanning happens on your machine, not the cloud, and not in some data-center.
- **Eco-Friendly** -- Being a small, discriminative AI, it does not harm the environment in any way worse than simply browsing tiktok or whatever.
- **Configurable Threshold** -- Set how confident the AI must be (0-100%) before taking action
- **Perceptual Hashing** -- Tracks images by hash to avoid re-scanning the same image
- **Community Review System** -- Users can upvote/downvote detections to improve accuracy
- **Auto Whitelisting/Blacklisting** -- Based on vote thresholds, images get automatically trusted or blocked because yes, the AI can hallucinate, so we ensure that the opinion of the people is greater than the opinion of the AIs. 

### Spam Protection

Nodeus includes a spam detection system with configurable punishments that works out of the box. Future updates will bring expanded options including per-channel exceptions, configurable message frequency thresholds, and duplicate content detection.

---

## Punishment System

### Configurable Actions Per Violation

For **each category** (text, images, spam), you can independently decide what happens:

| Action | Description |
|--------|-------------|
| Delete Message | Remove the offending message |
| Warn Member | Issue an official warning (stored in database) |
| Mute Member | Temporarily or permanently mute |
| Kick Member | Remove from server |
| Ban Member | Temporarily or permanently ban |
| Announce Violation | Send a message to the user (configurable per action) |

### Temporary Punishments
- **Temporary Mutes** -- Auto-unmute when timer expires
- **Temporary Bans** -- Auto-unban when timer expires
- **Cooldowns** -- Short mutes for spam without full punishment

### Exemption System
Need to let someone bypass the filters temporarily? Use `/automod exempt` to give them a pass, perfect for trusted users.

---

## Warning System

- Issue official warnings to users with `/moderation warning add`
- Revoke warnings if needed with `/moderation warning revoke`
- Complete warning history per user and per server
- Automatic DM notifications (configurable)
- Warnings are logged in both Discord channel and database archive

---

## Welcomer & Join Roles

### Welcomer System
- Customizable welcome messages
- Placeholder support: `<mention>`, `<username>`, `<display_name>`, `<user_id>`, `<timestamp>`
- Toggle on/off with `/welcomer enabled`
- Choose any channel with `/welcomer channel`

### Join Roles (Auto-role)
- Automatically assign roles to new members
- Add roles with `/joinroles add`
- Remove roles with `/joinroles remove`
- List all join roles with `/joinroles list`
- Automatic cleanup of invalid/deleted roles

---

## Audit Logging

- **Dedicated log channel** -- All moderation actions posted here
- **Comprehensive coverage** -- Mutes, bans, kicks, warnings, setting changes, and more
- **Database archive** -- All logs saved for historical reference
- **Color-coded embeds** -- Red for bad, green for good, orange for warnings

---

## Interactive Configuration

Forget complicated commands! Nodeus uses **button-based menus** for all configuration:

| Command | What You Can Configure |
|--------|----------------------|
| `/automod modules` | Turn on/off text, image, and spam filters |
| `/automod text settings` | Configure punishments for text violations |
| `/automod text checks` | Enable/disable specific detection methods |
| `/automod text words_menu` | Choose which preset word lists to use |
| `/automod imgscan settings` | Configure image filter punishments |
| `/automod spam settings` | Configure spam filter punishments |

Just click the buttons to toggle settings!

---

## Self-Hosting

Nodeus supports self-hosting for those who want full control over their setup. If you'd like to run your own instance, follow these steps below.


***Before we get into that though, I want to make it clear that if you need help with install at any point in this guide, feel free to message me on discord! My discord handle is "@friendlyfox.exe" I'm happy to help!***
<hr>

That being said, here's the steps:


1. Clone the repository.
2. Download python3.13
3. Create a venv
4. Install requirements.txt with pip
5. Run bot.py with python, using the venv.
6. Optionally, hook this up to a panel like Pufferpanel for ease of management. From there, its done!

### With Docker

1. Clone the repository
2. Download python3.13-bookworm image for docker with `docker pull python:3.13-bookworm`
3. Create a docker network named "nodeus-network" 
4. *(If intending to use Postgre or the Web UI)*
   Create a docker container named "nodeus-bot" with python3.13-bookworm image, which is connected to the network "nodeus-network"
5. Copy the cloned repo to this docker container
6. Install requirements.txt with pip
7. Run bot.py with python

### Installing WebUI
To install the WebUI, you will want to

1. Go to https://discord.com/developers/applications
2. Click on your bot
3. Find the client ID and client secret, and find your bot token.
4. Add a redirect URI to https://example-domain/auth/discord/callback
5. Clone the repository
6. Download python3.13-bookworm image for docker with `docker pull python:3.13-bookworm`
7. Create a docker container named "nodeus-webui" with python3.13-bookworm image, which is connected to the network "nodeus-network"
8. Copy the cloned repo to this docker container
9. Install requirements.txt with pip
10. With Docker, create a postgres docker container named "nodeus-pg" connected to the "nodeus-network" from before that restarts unless stopped.
11. Run `webui.py --setup-db` with python in the container you just created
12. Provide the details of the database to the application, then confirm the database could be reached (It'll tell you)
12. Run `webui.py` with python
13. Provide the Client ID, Client Secret and Bot Token to the WebUI.

Great, that is now done. But there's a second part.
Now that you have a docker container with the WebUI installed inside, we'll want to make sure the separate docker container
that had the actual Discord Bot installed inside is also attempting to communicate to the PostgreSQL DB.

Go into the terminal of that docker container, which should be named "nodeus-bot", and stop the bot process.
Then run:
```
python bot.py --setup-db
```
And then fill in the details of the database, and ensure that it can connect. It'll tell you if it can, once you've provided the details.

**Last step!**
In the bot's docker container, find "settings.json" and toggle the setting "prod_mode" from "false", to "true". (case sensitive)

And it's done! The WebUI and the Bot should be operating in harmony, how lovely.

### Database Options
- **Development/Small Servers**: SQLite (built-in, no setup required)
- **Production/Large Servers**: PostgreSQL (recommended for better performance, required for using the WebUI if you want to avoid weird, unsupported setups.)

### Security Features
- **Token Encryption** -- All tokens and passwords are encrypted.
- **Production Mode** -- Enables Python optimizations and stricter security
- **Separate Tokens** -- Different tokens for production and development

---

## Questions & Answers

**Q: Does Nodeus use generative AI?**
A: No! Nodeus uses **discriminative AI** for image detection, the same technology your phone uses to recognize faces. It's lightweight, private, and runs locally.

**Q: Will Nodeus work on large servers?**
A: Yes! With PostgreSQL and production mode enabled, Nodeus can handle hundreds of servers and thousands of messages efficiently. In fact, under testing, Nodeus could read, and check one thousand messages against all 8 security layers in a little under 8 seconds.

**Q: Can I use my own banned word list?**
A: Absolutely! Use `/automod wordlist add` to add custom words. You can also choose which preset lists to use.

**Q: What happens if I don't want a specific check?**
A: Just turn it off! Use `/automod text checks` to toggle any detection method on or off.

**Q: Does Nodeus store message content?**
A: Only violations are stored (for audit purposes). Normal messages are processed in memory and discarded.

However, when using the official instance, if you consent to it and are *SPECIFICALLY ASKED BY THE PROJECT MAINTAINER*, Nodeus will store all messages created on the server for manual review to check automod quality. Nodeus will not store messages like this unless you are okay with it. Messages not flagged by the automod will not be inspected, so most mundane messages are not reviewed.

---

## Need Help?

If you run into any issues:
- Contact the bot developer (usually listed on the bot's profile)
- Open an issue on GitHub (if you're self-hosting)

---

## Acknowledgements

Nodeus was built with love using:
- [Hikari](https://github.com/hikari-py/hikari) -- Discord API framework
- [Lightbulb](https://github.com/tandemdude/hikari-lightbulb) -- Command handler
- [Miru](https://github.com/hikari-py/miru) -- Interactive components
- [SQLAlchemy](https://www.sqlalchemy.org/) -- Database ORM
- [PyTorch](https://pytorch.org/) & [TIMM](https://github.com/rwightman/pytorch-image-models) -- AI image detection

Special thanks to the open-source community for making projects like this possible.