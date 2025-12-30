import logging
from datetime import datetime

class MarkdownFormatter(logging.Formatter):
    def format(self, record):
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        level = record.levelname
        message = record.getMessage()

        return (
            f"\n---\n"
            f"**Time:** {timestamp}\n\n"
            f"**Level:** `{level}`\n\n"
            f"```text\n{message}\n```\n"
        )


def setup_md_logger(log_file="logging.md"):
    logger = logging.getLogger("PTTAgentLogger")
    logger.setLevel(logging.INFO)

    # ⚠️ Prevent duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    # Markdown file handler
    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setFormatter(MarkdownFormatter())
    logger.addHandler(file_handler)

    # ✅ Console handler (THIS IS WHERE IT GOES)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("[%(levelname)s] %(message)s")
    )
    logger.addHandler(console_handler)

    logger.propagate = False
    return logger
