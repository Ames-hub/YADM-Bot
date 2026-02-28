# Nodeus Discord Bot

A comprehensive moderation and server management bot for Discord, featuring advanced text filtering, image moderation, automated punishments, and extensive customization options.

Nodeus is at its core, a moderation bot and that is what it is built for, but that's not to say it can't do anything else. This is the first moderation bot I've decided to take seriously, so here you go!

## Features

### 🛡️ **Advanced Moderation**

#### Text Content Filtering
Multiple heuristic checks to catch inappropriate language:
- **Equality Check** - Direct word matching against blacklist
- **Symbol Removal** - Detects words hidden with symbols (eg, "f!oo@b#ar")
- **Collapsed Text** - Catches exaggerated words ("foooobar" -> "foobar")
- **Spacehack Detection** - Identifies words split with spaces (eg, "fo obar")
- **Letter Stitching** - Detects spaced-out letters ("f o o b a r")
- **Reverse Text** - Catches reversed words (raboof -> foobar)
- **Similarity Matching** - 85%+ similarity threshold detection
- **Syntactic Analysis** - Context-aware detection distinguishing self-directed vs. other-directed insults

Additionally, each of these checks can be toggled on or off, so if you don't like one of the ones you see here? That's fine, just turn it off!

#### Image Moderation
**Disclaimer**: There is much discourse regarding the topic of Generative AI. We do not use Gen AI, we use Discriminative AI. Discriminative AI exists everywhere, such as for example, your phone's camera. If you've ever wondered how your phone knows when a person is in the camera's frame and focuses on them, discriminative AI is the answer.

- **Discriminative AI Powered NSFW Detection** - Local, light PyTorch model for privacy and speed
- **Perceptual Hashing** - Tracks images by hash to avoid re-scanning
- **Community Review System** - Users can upvote/downvote detections
- **Automatic Whitelisting/Blacklisting** - Based on vote thresholds

#### Spam Protection (WIP)
When this feature is fully implemented, you will have:
- Configurable spam detection and punishment
- Message deletion, warnings, mutes, kicks, or bans

### ⚖️ **Punishment System**

#### Configurable Actions Per Violation
- Delete message
- Warn member
- Mute member (temporary or permanent)
- Kick member
- Ban member (temporary or permanent)

#### Temporary Punishments
- **Temporary Mutes** - Auto-unmute when timer expires
- **Temporary Bans** - Auto-unban when timer expires

### 📋 **Warning System**
- Issue official warnings to users
- Revoke previous warnings
- Complete warning history per user/server
- Automatic DM notifications (configurable)

### 👋 **Join Roles (Auto-role)**
- Automatically assign roles to new members
- Add, remove, and list join roles via commands
- Automatic cleanup of invalid roles

### 👋 **Welcomer System**
- Customizable welcome messages
- Placeholder support: `<user_id>`, `<timestamp>`, `<display_name>`, `<username>`, `<mention>`
- Can Toggle on/off
- Posts in system channel

### **Audit Logging**
- Dedicated log channels per guild
- Comprehensive action logging
- Database archive for historical reference

### **Custom Word Lists**
- **Blacklist** - Add custom filtered words
- **Whitelist** - Exempt words from filtering
- **Preset Bad Words** - Built-in list included

### **Database Management**

#### Multi-Database Support
- **SQLite** - Development/testing
- **PostgreSQL** - Production (recommended)

#### Advanced Features
- **Docker PostgreSQL Fallback** - Auto-creates Docker PostgreSQL instance if needed
- **Backup/Restore System** - CLI tools for database backup/restore
- **Migration Tools** - Transfer data between database types

### **Security**

- **Token Encryption** - All tokens and passwords are encrypted.
- **Production Mode** - Enforces Python optimizations for stability
- **Separate Tokens** - Different tokens for production/development
- **Permission System** - Granular permission checks with cooldowns

### 🚀 **Performance**

- **uvloop Support** - Enhanced async performance on Linux
- **Guild Name Caching** - Reduces API calls
- **Efficient Database Queries** - Optimized SQLAlchemy usage
- **Modular Architecture** - Load only what you need

### **Utility Commands**

- **/uptime** - Check bot uptime
- **Auto-welcome** - Setup guide when bot joins new server
- **Comprehensive Help System** - Built into Discord's slash commands

## **Technical Stack**

- **Framework**: [Hikari](https://github.com/hikari-py/hikari) + [Lightbulb](https://github.com/tandemdude/hikari-lightbulb) + [Miru](https://github.com/hikari-py/miru)
- **Database**: SQLAlchemy ORM with SQLite/PostgreSQL
- **AI/ML**: PyTorch + TIMM for NSFW detection
- **Performance**: uvloop for Linux systems
- **Security**: Fernet encryption for sensitive data

## **Installation**

### Prerequisites
- Python 3.13
- PostgreSQL (optional, for production)
- Docker (optional, for database fallback)
- Discord Bot Token

### Environment Variables

If you wish, instead of using the programs setup wizard, you can create a .env file with the following keys and values and we will take data from here.

If you want to do this:<br>
Create a `.env` file in the root directory and fill in this data:
```env
BOT_TOKEN=your_bot_token_here
PROD_MODE=true/false
PRIMARY_MAINTAINER=123456789012345678 (your user id)
BOT_NAME=Nodeus (or whatever you want)
ALLOW_DOCKER_FALLBACK=true/false

# Database (optional)
DB_HOST=localhost
DB_PORT=5430
DB_NAME=nodeus
DB_USER=nodeus
DB_PASSWORD=secure_password
```

## **Configuration**

### Production Mode
When enabled:
- Enforces Python optimization flags (`-O` or `-OO`)
- Uses PostgreSQL database
- Stricter security enforcement
- Enhanced logging

### Development Mode
- Uses SQLite database
- More verbose logging
- Debug-friendly

## **Database Commands**

```bash
# Backup PostgreSQL to SQLite
python app.py --backup

# Restore from SQLite to PostgreSQL
python app.py --restore

# Configure existing PostgreSQL database
python app.py --setup-db
```

## **Development**

### Adding New Modules
1. Create a new package in the `modules/` directory with `__init__.py`
2. Create command files using Lightbulb's command structure
3. The bot automatically discovers and loads modules

### Running Tests
```bash
pytest
```

## **Contributing**

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## **Support**

For issues or questions:
- Open an issue on GitHub
- Contact the maintainer through Discord
