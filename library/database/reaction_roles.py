from library.database.manage import get_session, reaction_role_group, reaction_role_item
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta
from library import datastore as ds
from library.botapp import botapp
import logging
import hikari
import emoji
import re

class rr_errors:
    class UngroupedMessage(Exception):
        def __init__(self, *args):
            super().__init__(*args)
    class ItemNotFound(Exception):
        def __init__(self, *args):
            super().__init__(*args)
    class EmojiAlreadyAdded(Exception):
        def __init__(self, *args):
            super().__init__(*args)
    class EmojiNotPresent(Exception):
        def __init__(self, *args):
            super().__init__(*args)

def get_is_grouped(group_id:int):
    session = get_session()
    try:
        record = (
            session.query(reaction_role_group.group_id)
            .filter(reaction_role_group.group_id == group_id)
            .one_or_none()
        )
        return record is not None
    except SQLAlchemyError as err:
        logging.error("Error checking if reaction role msg is tracked by grp ID", exc_info=err)
        return False
    finally:
        session.close()

def get_is_grouped_by_msg(message_id:int, get_id:bool=False):
    session = get_session()
    try:
        record = (
            session.query(reaction_role_group)
            .filter(reaction_role_group.message_id == message_id)
            .one_or_none()
        )
        if get_id:
            return record.group_id
        else:
            return record is not None
    except SQLAlchemyError as err:
        logging.error("Error checking if reaction role msg is tracked by msg ID", exc_info=err)
        return False
    finally:
        session.close()

async def create_group(guild_id:int, channel_id:int, embed_title:str, embed_desc:str):
    session = get_session()
    try:
        record = reaction_role_group(
            guild_id=guild_id,
            channel_id=channel_id,
            embed_title=embed_title,
            embed_desc=embed_desc
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record.group_id
    except SQLAlchemyError as err:
        logging.error("Encountered an error in tracking a new reaction role message!", exc_info=err)
        session.rollback()
        return False
    finally:
        session.close()

def get_group(group_id:int, guild_id:int=None) -> reaction_role_group:
    session = get_session()
    try:
        records = (
            session.query(reaction_role_group)
            .filter(reaction_role_group.group_id == group_id)
        )
        if guild_id:
            records = records.filter(reaction_role_group.guild_id == guild_id)
        return records.one_or_none()
    except SQLAlchemyError as err:
        logging.error("Error getting the reaction role list", exc_info=err)
        return []  # Return an empty list if something goes wrong
    finally:
        session.close()

custom_emoji_pattern = re.compile(r"<(a?):(\w+):(\d+)>")
emoji_id_pattern = re.compile(r"\d{17,20}")

def is_unicode_emoji(text: str) -> bool:
    # emoji.is_emoji correctly handles sequences and modifiers
    return emoji.is_emoji(text)

def get_emoji_type(text):
    custom = custom_emoji_pattern.fullmatch(text)
    if custom:
        animated, name, emoji_id = custom.groups()
        return {
            "type": "custom",
            "animated": bool(animated),
            "name": name,
            "id": int(emoji_id)
        }

    if is_unicode_emoji(text):
        return {
            "type": "unicode",
            "animated": False,
            "emoji": text
        }

    raw_id = emoji_id_pattern.fullmatch(text)
    if raw_id:
        return {
            "type": "custom",
            "animated": False,
            "name": None,
            "id": int(text)
        }

    return None

class rr_group:
    def __init__(self, group_id:int):
        if not get_is_grouped(group_id):
            raise rr_errors.UngroupedMessage()

        self.group_id = group_id
        self.group = get_group(group_id)

        self.message_id = self.group.message_id
        self.guild_id = self.group.guild_id
        self.channel_id = self.group.channel_id

    def _generate_embed(self):
        reaction_roles_txt = ""
        for item in self.get_items():
            if item.description == None:
                description = ""
            else:
                description = f"{item.description}\n"

            emoji_data = get_emoji_type(item.trigger_emoji_id)
            if emoji_data['type'] == "custom":
                if item.is_animated:
                    reaction_roles_txt += f"{description}<a:{item.trigger_emoji_name}:{item.trigger_emoji_id}> — <@&{item.reaction_role_id}>\n\n"
                else:
                    reaction_roles_txt += f"{description}<:{item.trigger_emoji_name}:{item.trigger_emoji_id}> — <@&{item.reaction_role_id}>\n\n"
            else:
                reaction_roles_txt += f"{description}{item.trigger_emoji_id} — <@&{item.reaction_role_id}>\n\n"

        embed = hikari.Embed(
            title=self.group.embed_title,
            description=self.group.embed_desc + "\n\n" + reaction_roles_txt,
            colour=0xff00ff
        )

        return embed

    def set_channel(self, channel_id:int):
        channel_id = int(channel_id)
        session = get_session()
        try:
            record = (
                session.query(reaction_role_group)
                .filter(reaction_role_group.group_id == self.group_id)
                .one_or_none()
            )

            if record:
                record.channel_id = channel_id
            else:
                raise rr_errors.ItemNotFound()

            session.commit()
            return True
        except SQLAlchemyError as err:
            logging.error(
                "Error updating reaction role group's channel!",
                exc_info=err
            )
            session.rollback()
            return False
        finally:
            session.close()

    async def publish(self):
        embed = self._generate_embed()

        try:
            message = await botapp.rest.create_message(
                self.group.channel_id,
                embed
            )
        except (hikari.ForbiddenError, hikari.UnauthorizedError):
            return False
        
        self.set_message_id(message.id)
        self.message_id = int(message.id)

        all_reaction_roles = self.get_items()
        for rr in all_reaction_roles:
            try:
                emoji_type = get_emoji_type(rr.trigger_emoji_id)['type']
                if emoji_type == "custom":
                    await botapp.rest.add_reaction(
                        self.channel_id,
                        self.message_id,
                        emoji=rr.trigger_emoji_id,
                        emoji_id=rr.trigger_emoji_id
                    )
                else:
                    await botapp.rest.add_reaction(
                        self.channel_id,
                        self.message_id,
                        emoji=rr.trigger_emoji_id,
                    )
            except (hikari.ForbiddenError, hikari.UnauthorizedError):
                return False
            
        session = get_session()
        try:
            records = (
                session.query(reaction_role_item)
                .filter(reaction_role_item.group_id == self.group_id)
                .all()
            )

            for record in records:
                record.message_id = self.message_id

            session.commit()
            return True
        except SQLAlchemyError as err:
            logging.error(
                "Error updating reaction role group's channel!",
                exc_info=err
            )
            session.rollback()
            return False
        finally:
            session.close()

    async def give_member_role(self, user_id:int, emoji):
        item = self.fetch_item(emoji)
        
        try:
            user = await botapp.rest.fetch_member(self.guild_id, user_id)
        except (hikari.ForbiddenError, hikari.UnauthorizedError):
            return False
        
        if item.reaction_role_id in user.role_ids:
            return False

        try:
            await botapp.rest.add_role_to_member(
                item.guild_id,
                user_id,
                item.reaction_role_id,
                reason="User used a reaction role"
            )
        except (hikari.ForbiddenError, hikari.UnauthorizedError):
            return False

        if ds.d["rr_role_names_cache"].get(item.reaction_role_id, None) is None:
            try:
                role = await botapp.rest.fetch_role(
                    item.guild_id,
                    item.reaction_role_id
                )
                role_name = role.name
                ds.d["rr_role_names_cache"][item.reaction_role_id] = {
                    "time": datetime.now(),
                    "name": role_name
                }
            except (hikari.ForbiddenError, hikari.UnauthorizedError):
                return False
        else:
            if ds.d["rr_role_names_cache"][item.reaction_role_id]['time'] > datetime.now() - timedelta(hours=6):
                # Still use it, but expire the cache.
                del ds.d["rr_role_names_cache"][item.reaction_role_id]
            role_name = ds.d["rr_role_names_cache"][item.reaction_role_id]['name']

        try:
            await user.send(
                hikari.Embed(
                    title="Reaction Role Added",
                    description=f"The role {role_name} has been added to your profile when you reacted with \"{item.trigger_emoji_name}\".",
                    colour=0x00ff00
                )
            )
        except (hikari.ForbiddenError, hikari.UnauthorizedError):
            return False

        return True
    
    async def take_member_role(self, user_id:int, emoji):
        item = self.fetch_item(emoji)
        
        try:
            user = await botapp.rest.fetch_member(self.guild_id, user_id)
        except (hikari.ForbiddenError, hikari.UnauthorizedError):
            return False
        
        if not item.reaction_role_id in user.role_ids:
            return False
        
        if not item.allow_unreact:
            await user.send(
                hikari.Embed(
                    title="Sticky Role!",
                    description=(
                        f"You just tried to remove the reaction role under \"{item.trigger_emoji_name}\"\n"
                        "This role is sticky, and cannot be removed normally."
                    ),
                    colour=0xff0000
                )
            )
            return

        try:
            await botapp.rest.remove_role_from_member(
                item.guild_id,
                user_id,
                item.reaction_role_id,
                reason="User unreacted to a reaction role"
            )
        except (hikari.ForbiddenError, hikari.UnauthorizedError):
            return False

        if ds.d["rr_role_names_cache"].get(item.reaction_role_id, None) is None:
            try:
                role = await botapp.rest.fetch_role(
                    item.guild_id,
                    item.reaction_role_id
                )
                role_name = role.name
                ds.d["rr_role_names_cache"][item.reaction_role_id] = {
                    "time": datetime.now(),
                    "name": role_name
                }
            except (hikari.ForbiddenError, hikari.UnauthorizedError):
                return False
        else:
            if ds.d["rr_role_names_cache"][item.reaction_role_id]['time'] > datetime.now() - timedelta(hours=6):
                # Still use it, but expire the cache.
                del ds.d["rr_role_names_cache"][item.reaction_role_id]
            role_name = ds.d["rr_role_names_cache"][item.reaction_role_id]['name']

        try:
            await user.send(
                hikari.Embed(
                    title="Reaction Role Removed",
                    description=f"The role \"{role_name}\" has been removed from your profile after you removed your \"{item.trigger_emoji_name}\" reaction.",
                    colour=0xff0000
                )
            )
        except (hikari.ForbiddenError, hikari.UnauthorizedError):
            return False

        return True

    def set_message_id(self, message_id:int):
        message_id = int(message_id)
        session = get_session()
        try:
            record = (
                session.query(reaction_role_group)
                .filter(reaction_role_group.group_id == self.group_id)
                .one_or_none()
            )

            if record:
                record.message_id = message_id
            else:
                raise rr_errors.ItemNotFound()

            session.commit()
            return True
        except SQLAlchemyError as err:
            logging.error(
                "Error updating reaction role group's message ID!",
                exc_info=err
            )
            session.rollback()
            return False
        finally:
            session.close()

    def end_tracking(self):
        session = get_session()
        try:
            record = (
                session.query(reaction_role_group)
                .filter(
                    reaction_role_group.guild_id == self.guild_id,
                    reaction_role_group.channel_id == self.channel_id,
                    reaction_role_group.message_id == self.message_id
                )
                .one_or_none()
            )

            if not record:
                raise rr_errors.ItemNotFound()  # Nothing to delete

            session.delete(record)
            session.commit()
            return True
        except SQLAlchemyError as err:
            logging.error("Error ending reaction role (rr) tracking!", exc_info=err)
            session.rollback()
            return False
        finally:
            session.close()

    def add_item(self, emoji_id:str, emoji_name:str, is_animated:bool, reaction_role: hikari.Role|int, allow_remove:bool, description:str):
        if isinstance(reaction_role, hikari.Role):
            role_id = int(reaction_role.id)
        else:
            role_id = int(reaction_role)

        existing_items = self.get_items()
        if emoji_id in [rr.trigger_emoji_id for rr in existing_items]:
            raise rr_errors.EmojiAlreadyAdded()

        session = get_session()
        try:
            record = reaction_role_item(
                group_id=self.group_id,
                guild_id=self.guild_id,
                message_id=self.message_id,

                trigger_emoji_id=emoji_id,
                trigger_emoji_name=emoji_name,
                is_animated=is_animated,

                reaction_role_id=role_id,
                allow_unreact=allow_remove,
                description=description
            )
            session.add(record)
            session.commit()
            return True
        except SQLAlchemyError as err:
            logging.error("Error adding reaction role msg ID to db to be tracked!", exc_info=err)
            session.rollback()
            return False
        finally:
            session.close()

    def rm_item(self, emoji):
        session = get_session()
        existing_items = self.get_items()

        emoji_data = get_emoji_type(emoji)

        listed_existing_items = [rr.trigger_emoji_id for rr in existing_items]
        if emoji_data['type'] == 'custom':
            if emoji_data['id'] in listed_existing_items is not True:
                raise rr_errors.EmojiNotPresent()
        else:
            if not emoji in listed_existing_items:
                raise rr_errors.EmojiNotPresent()

        try:
            record = (
                session.query(reaction_role_item)
                .filter(
                    reaction_role_item.group_id == self.group_id,
                )
            )
            if emoji_data['type'] == "custom":
                record = record.filter(reaction_role_item.trigger_emoji_id == emoji_data['id'])
            else:
                record = record.filter(reaction_role_item.trigger_emoji_id == emoji_data['emoji'])
            
            record = record.one_or_none()

            if not record:
                raise rr_errors.ItemNotFound()  # Nothing to delete

            session.delete(record)
            session.commit()
            return True
        except SQLAlchemyError as err:
            logging.error("Error removing item from reaction role in db!", exc_info=err)
            session.rollback()
            return False
        finally:
            session.close()

    def get_items(self) -> list[reaction_role_item]:
        session = get_session()
        try:
            records = (
                session.query(reaction_role_item)
                .filter(reaction_role_item.group_id == self.group_id)
            )
            if self.guild_id:
                records.filter(reaction_role_item.guild_id == self.guild_id)

            records = records.all()

            return records
        except SQLAlchemyError as err:
            logging.error("Error getting the reaction role list", exc_info=err)
            return []  # Return an empty list if something goes wrong
        finally:
            session.close()

    def fetch_item(self, emoji) -> reaction_role_item:
        session = get_session()
        try:
            records = (
                session.query(reaction_role_item)
                # TODO: Changed this to accept "group id" and not "message id". Need to check if that still lets it work.
                .filter(reaction_role_item.group_id == self.group_id)
                .filter(reaction_role_item.trigger_emoji_id == emoji)
            )

            records = records.one_or_none()

            return records
        except SQLAlchemyError as err:
            logging.error("Error getting a reaction role item", exc_info=err)
            return None
        finally:
            session.close()