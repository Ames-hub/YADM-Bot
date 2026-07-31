# Nodeus Discord Bot

A comprehensive moderation and server management bot for Discord, featuring advanced text filtering, AI-powered image moderation, automated punishments, and extensive customization options.

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
| **High** | Similarity Matching | 80%+ similarity threshold (catches "baddword" vs "badword") |
| **High** | Syntactic Analysis | **Context-aware!** Distinguishes self-insults from attacks on others |

Every single check can be toggled on or off. Don't like one? Just turn it off in the menu!

### Image Moderation

> **A note on AI:** There's much discourse about Generative AI. Nodeus uses **Discriminative AI**, the same technology your phone uses to focus on faces in photos. It's lightweight, private, and runs locally. If you're heavily against AI, I ask you at least read this section before leaving.

- **Privacy-Focused** -- All image scanning happens on your machine, not the cloud, and not in some data-center.
- **Eco-Friendly** -- Being a small, discriminative AI, it does not harm the environment
- **Configurable Threshold** -- Set how confident the AI must be (0-100%) before taking action
- **Perceptual Hashing** -- Tracks images by hash to avoid re-scanning the same image
- **Community Review System** -- Users can upvote/downvote detections to improve accuracy
- **Auto Whitelisting/Blacklisting** -- Based on vote thresholds, images get automatically trusted or blocked

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

## Command Reference

All commands are slash commands -- just type `/` and start typing!

### Automod Commands
| Command | Description |
|--------|-------------|
| `/automod modules` | Enable/disable core modules (text, image, spam) |
| `/automod text settings` | Configure text filter punishments |
| `/automod text checks` | Toggle specific text detection methods |
| `/automod text words_menu` | Choose preset word lists |
| `/automod text mutelength` | Set mute duration for text violations |
| `/automod text ban_delete_time` | Set message deletion time on ban |
| `/automod imgscan settings` | Configure image filter punishments |
| `/automod imgscan threshold` | Set AI confidence threshold (0-100%) |
| `/automod imgscan mutelength` | Set mute duration for image violations |
| `/automod spam settings` | Configure spam filter punishments |
| `/automod spam toggle` | Enable/disable spam filter |
| `/automod wordlist add` | Add custom blacklisted/whitelisted word |
| `/automod wordlist remove` | Remove word from custom list |
| `/automod exempt` | Temporarily exempt user from filters |
| `/automod unexempt` | Remove exemption |

### Moderation Commands
| Command | Description |
|--------|-------------|
| `/moderation mute` | Mute a user (temporary or permanent) |
| `/moderation kick` | Kick a user from the server |
| `/moderation ban` | Ban a user (temporary or permanent) |
| `/moderation purge` | Bulk-delete messages in a channel |
| `/moderation lockdown` | Lock a channel (no messages from members) |
| `/moderation unlock` | Unlock a channel |
| `/moderation warning add` | Issue official warning to user |
| `/moderation warning revoke` | Remove a warning |
| `/moderation livelog channel` | Set audit log channel |

### Welcomer Commands
| Command | Description |
|--------|-------------|
| `/welcomer enabled` | Turn welcomer on/off |
| `/welcomer channel` | Set welcome message channel |
| `/welcomer message` | Set welcome message text |

### Join Roles Commands
| Command | Description |
|--------|-------------|
| `/joinroles add` | Add role given to new members |
| `/joinroles remove` | Stop giving a role |
| `/joinroles list` | List all join roles |

### Utility Commands
| Command | Description |
|--------|-------------|
| `/setup` | Apply recommended settings (one-time setup) |
| `/uptime` | Check how long Nodeus has been online |
| `/rtd` | Roll dice (just for fun!) |

---

## Getting Started

### 1. Invite Nodeus
Invite the bot with this link:
https://discord.com/oauth2/authorize?client_id=1461801438446616618

### 2. Run One-Time Setup
In any channel, have an administrator run: `/setup`

Nodeus will:
- Create a dedicated logs channel
- Enable text, image, and spam filters
- Set sensible default punishments
- Enable preset word lists (swears, slurs, NSFW)
- Configure audit logging

### 3. Customize (Optional)
Use the interactive menus to tweak anything to your liking!
The menus are found under `/automod (automod category) settings`

---

## Self-Hosting

Nodeus supports self-hosting for those who want full control over their setup. If you'd like to run your own instance, follow these steps:
(If you need help, google "how to run python program with venv" or contact me on discord, @friendlyfox.exe)

1. Clone the repository.
2. Download python3.13
3. Create a venv
4. Install requirements.txt with pip
5. Run app.py with python, using the venv.
6. Optionally, hook this up to a panel like Pufferpanel for ease of management. From there, its done!

### Database Options
- **Development/Small Servers**: SQLite (built-in, no setup required)
- **Production/Large Servers**: PostgreSQL (recommended for better performance)

### Security Features
- **Token Encryption** -- All tokens and passwords are encrypted at rest
- **Production Mode** -- Enables Python optimizations and stricter security
- **Separate Tokens** -- Different tokens for production and development

---

## Questions & Answers

**Q: Does Nodeus use generative AI?**
A: No! Nodeus uses **discriminative AI** for image detection, the same technology your phone uses to recognize faces. It's lightweight, private, and runs locally.

**Q: Will Nodeus work on large servers?**
A: Yes! With PostgreSQL and production mode enabled, Nodeus can handle hundreds of servers and thousands of messages efficiently.

**Q: Can I use my own banned word list?**
A: Absolutely! Use `/automod wordlist add` to add custom words. You can also choose which preset lists to use.

**Q: What happens if I don't want a specific check?**
A: Just turn it off! Use `/automod text checks` to toggle any detection method on or off.

**Q: Does Nodeus store message content?**
A: Only violations are stored (for audit purposes). Normal messages are processed in memory and discarded.
When using the official instance, if you consent to it and are *SPECIFICALLY ASKED BY THE PROJECT MAINTAINER*, Nodeus will store all messages created on the server for manual review to check automod quality.

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