from library.database.manage import get_session, observation_entry
from datetime import datetime

def add_entry(msg_id:int, channel_id:int, username:int, msg_content:str, bot_response:str|None):
    if not isinstance(msg_content, str) or not msg_content:
        return False
    with get_session() as session:
        record = observation_entry(
            timestamp=datetime.now().timestamp(),
            msg_id=msg_id,
            username=username,
            channel_id=channel_id,
            msg_content=msg_content,
            bot_response=bot_response,
        )
        session.add(record)
        session.commit()
    return True

def get_channel_history(channel_id:int):
    with get_session() as session:
        data = (
            session.query(observation_entry)
            .filter(observation_entry.channel_id == channel_id)
            .order_by(observation_entry.timestamp.desc())  # Produces newest messages first.
            .all()
        )

    return data if data else None