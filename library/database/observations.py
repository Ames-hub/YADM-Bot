from library.database.manage import get_session, observation_entry
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone

def reeval_entry(msg_id:int, new_conclusion: str|None, mark_for_review:bool=True, do_confirm:bool=False, bad_msg:bool=None):
    with get_session() as session:
        result = (
            session.query(observation_entry)
            .filter(observation_entry.msg_id == msg_id)
            .one_or_none()
        )
        if not result:
            return False

        result.bot_response = new_conclusion
        result.reeval_date = datetime.now(timezone.utc)
        if do_confirm:
            result.confirmed = True  # Mark it as confirmed, as the automod decision was determined as correct.
            if not bad_msg:
                raise ValueError("Cannot confirm a message as good or bad and not set if its a bad message or not")
            result.bad_message = bool(bad_msg)
            result.needs_review = False
        if mark_for_review:
            if do_confirm:
                raise ValueError("Cannot mark for confirmation and review at the same time.")
            result.needs_review = True
            
        session.commit()
    return True

def add_entry(msg_id:int, channel_id:int, username:int, msg_content:str, bot_response:str|None):
    if not isinstance(msg_content, str) or not msg_content:
        return False
    try:
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
    except IntegrityError:
        return True  # Already added
    return True

def get_all_entries(review_flagged_only:bool=False):
    with get_session() as session:
        records = (
            session.query(observation_entry)
            .order_by(observation_entry.timestamp.desc())  # Produces newest messages first.
        )
        if review_flagged_only:
            records = records.filter(observation_entry.needs_review == True)
        data = records.all()

    return data if data else None