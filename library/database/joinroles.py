from library.database.manage import get_session, guild_join_role
from library.database.auditing import server_logs
from sqlalchemy.exc import SQLAlchemyError
from library.botapp import botapp
import logging
import hikari

class joinroles:
    def __init__(self, guild_id):
        self.guild_id = guild_id

    class errors:
        class RoleNotAdded(Exception):
            def __init__(self, *args):
                super().__init__(*args)

    def add_role(self, role_id:int): 
        session = get_session()
        try:
            record = guild_join_role(
                guild_id=self.guild_id,
                role_id=role_id
            )
            session.add(record)
            session.commit()
            return True
        except SQLAlchemyError as err:
            logging.error("Encountered an error in adding a role to the guilds join roles list!", exc_info=err)
            session.rollback()
            return False
        finally:
            session.close()

    def rm_role(self, role_id):
        session = get_session()
        try:
            record = (
                session.query(guild_join_role)
                .filter(
                    guild_join_role.guild_id == self.guild_id,
                    guild_join_role.role_id == role_id,
                )
                .one_or_none()
            )

            if not record:
                raise self.errors.RoleNotAdded

            session.delete(record)
            session.commit()
            return True
        except SQLAlchemyError as err:
            logging.error("Encountered an error trying to remove a role from the guild's join roles list.", exc_info=err)
            session.rollback()
            return False
        finally:
            session.close()

    def get_roles(self) -> list[guild_join_role]:
        session = get_session()
        try:
            records = (
                session.query(guild_join_role.role_id)
                .filter(guild_join_role.guild_id == self.guild_id)
                .all()
            )
            return records
        except SQLAlchemyError as err:
            logging.error("Error getting all a guilds join roles!", exc_info=err)
            return []  # Return an empty list if something goes wrong
        finally:
            session.close()

    async def add_roles_to_member(self, user_id:int):
        roles = self.get_roles()
        for on_join_role in roles:
            try:
                await botapp.rest.add_role_to_member(
                    self.guild_id,
                    user_id,
                    role=on_join_role.role_id
                )
            except (hikari.ForbiddenError, hikari.UnauthorizedError):
                await server_logs(self.guild_id).create_entry(
                    hikari.Embed(
                        title="Couldn't add Join-Role!",
                        description=f"When <@{user_id}> joined, I was unable to add role <@&{on_join_role.role_id}> to the member.",
                        colour=0xff0000
                    )
                    .add_field(
                        name="Troubleshooting",
                        value="Please ensure that I have permission to add that role, by moving my top role above others and the role I need to add below my role"
                    )
                )
                return False  # No permissions
            except hikari.NotFoundError:
                # If it's not found, then we remove it
                self.rm_role(on_join_role.role_id)