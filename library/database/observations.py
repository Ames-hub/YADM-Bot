from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from library.database.manage import get_session, observation_entry
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import letter
from datetime import datetime, timezone
from reportlab.lib.units import inch
from reportlab.lib import colors
import io

def reeval_entry(msg_id:int, new_conclusion: str|None):
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
        session.commit()
    return True

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

def get_all_entries():
    with get_session() as session:
        data = (
            session.query(observation_entry)
            .order_by(observation_entry.timestamp.desc())  # Produces newest messages first.
            .all()
        )

    return data if data else None

def generate_automod_report() -> io.BytesIO:
    """
    Query every row in observation_logs, split into flagged (bot_response
    is not NULL) and unflagged (bot_response is NULL) entries, and render
    a two-section PDF report.

    `session` must be an active SQLAlchemy Session (however your
    get_session() hands one back — sync Session, or a context-managed one).

    Returns an io.BytesIO buffer containing the generated PDF, positioned at 0.
    """
    with get_session() as session:
        all_entries = (
            session.query(observation_entry)
            .all()
        )

    flagged = []
    unflagged = []
    for entry in all_entries:
        if entry.bot_response is not None:
            flagged.append(entry)
        else:
            unflagged.append(entry)

    buffer = io.BytesIO()

    styles = getSampleStyleSheet()
    
    # Add custom styles for better text wrapping
    styles.add(ParagraphStyle(
        name='TableCell',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        alignment=TA_LEFT,
        wordWrap='CJK',  # Enables better word wrapping
        allowWidows=0,
        allowOrphans=0,
    ))
    
    styles.add(ParagraphStyle(
        name='TableHeader',
        parent=styles['Heading4'],
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        wordWrap='CJK',
    ))

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        title="Automod QA Report",
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )

    story = []

    story.append(Paragraph("Automod QA Report Summary", styles["Title"]))
    story.append(Paragraph(
        f"Generated {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        styles["Normal"],
    ))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(
        f"Total logged messages: {len(all_entries)} &nbsp;|&nbsp; "
        f"Flagged: {len(flagged)} &nbsp;|&nbsp; Not flagged: {len(unflagged)}",
        styles["Normal"],
    ))
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph(f"Caught Attempts ({len(flagged)})", styles["Heading2"]))
    story.append(Spacer(1, 0.1 * inch))
    if flagged:
        story.append(_build_table(flagged, styles))
    else:
        story.append(Paragraph("No flagged messages logged.", styles["Normal"]))

    story.append(PageBreak())

    story.append(Paragraph(f"Not Flagged ({len(unflagged)})", styles["Heading2"]))
    story.append(Spacer(1, 0.1 * inch))
    if unflagged:
        story.append(_build_table(unflagged, styles))
    else:
        story.append(Paragraph("No unflagged messages logged.", styles["Normal"]))

    doc.build(story)
    buffer.seek(0)
    return buffer


def _build_table(entries, styles):
    """Build a formatted table with proper text wrapping."""
    table_data = []
    
    # Headers
    headers = ["ID", "Timestamp", "User", "Message", "Bot Response"]
    table_data.append([Paragraph(h, styles["TableHeader"]) for h in headers])
    
    # Data rows
    for entry in entries:
        entry: observation_entry
        # Format the bot_response nicely if it's a dictionary
        bot_response_text = ""
        if entry.bot_response:
            if isinstance(entry.bot_response, dict):
                bot_response_text = _format_bot_response(entry.bot_response)
            else:
                bot_response_text = str(entry.bot_response)

        row = [
            Paragraph(str(entry.msg_id), styles["TableCell"]),
            Paragraph(datetime.fromtimestamp(entry.timestamp).strftime('%Y-%m-%d %H:%M'), styles["TableCell"]),
            Paragraph(entry.username or "N/A", styles["TableCell"]),
            Paragraph(entry.msg_content or "", styles["TableCell"]),
            Paragraph(bot_response_text, styles["TableCell"]),
        ]
        table_data.append(row)
    
    # Create table with column widths
    col_widths = [
        0.8 * inch,   # ID
        1.2 * inch,   # Timestamp
        1.0 * inch,   # User
        2.5 * inch,   # Message
        2.5 * inch,   # Bot Response
    ]
    
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    
    # Style the table
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.gray),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('WORDWRAP', (0, 0), (-1, -1), True),  # Explicitly enable wordwrap
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    return table


def _format_bot_response(response_dict):
    """Format a bot_response dictionary into a readable HTML string."""
    if not response_dict:
        return ""
    
    # Check if it's a direct action string
    if isinstance(response_dict, str):
        return response_dict
    
    # Handle the nested dictionary structure
    if isinstance(response_dict, dict):
        parts = []
        
        # Add action if present
        if "action" in response_dict:
            parts.append(f"<b>Action:</b> {response_dict['action']}")
        
        # Check for nested report
        if "report" in response_dict:
            report = response_dict["report"]
            if isinstance(report, dict):
                for check_name, check_data in report.items():
                    if isinstance(check_data, dict):
                        # Only show checks that failed or have important info
                        if check_data.get('bad'):
                            parts.append(f"<b>{check_name.capitalize()}:</b> ❌")
                            # Add specific details
                            if 'word' in check_data and check_data['word']:
                                parts.append(f"&nbsp;&nbsp;&nbsp;Flagged word: <i>{check_data['word']}</i>")
                            if 'type' in check_data:
                                # Handle syntactic type which might be a tuple
                                type_info = check_data['type']
                                if isinstance(type_info, tuple) and len(type_info) > 0:
                                    # Try to extract context info
                                    if len(type_info) > 0 and isinstance(type_info[0], dict):
                                        context = type_info[0].get('context', '')
                                        if context:
                                            parts.append(f"&nbsp;&nbsp;&nbsp;Context: <i>{context}</i>")
                            if 'sim' in check_data:
                                parts.append(f"&nbsp;&nbsp;&nbsp;Similarity: {check_data['sim']:.2f}")
                    elif isinstance(check_data, tuple):
                        # Handle tuple cases
                        for item in check_data:
                            if isinstance(item, dict) and 'context' in item:
                                parts.append(f"<b>{check_name.capitalize()}:</b> <i>{item.get('context', '')}</i>")
            else:
                parts.append(str(report))
        else:
            # If no 'report' key, display the dict as formatted string
            for key, value in response_dict.items():
                if key != 'action':
                    parts.append(f"<b>{key.capitalize()}:</b> {value}")
        
        return "<br/>".join(parts) if parts else str(response_dict)
    
    return str(response_dict)