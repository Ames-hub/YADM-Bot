from library.database.manage import get_session, antivirus_report
from datetime import datetime
from pathlib import Path
import hashlib
import yara

rules_path = Path("library/yara-rules")
rules = yara.compile(
    filepaths={
        str(path): str(path)
        for path in rules_path.rglob("*.yar")
    }
)

class antivirus:
    """
    A basic anti-virus, meant for the link filtering check. (Which still needs to be made)
    """
    def check(file:bytes) -> bool:
        bytes_hash = hashlib.sha256(file).hexdigest()
        with get_session() as session:
            record = (
                session.query(antivirus_report)
                .filter(antivirus_report.filehash == bytes_hash)
                .one_or_none()
            )
            if record:
                return record.malicious

        result = rules.match(data=file) is True

        with get_session() as session:
            record = antivirus_report(
                filehash=bytes_hash,
                malicious=result,
                report_date=datetime.now()
            )

        return result