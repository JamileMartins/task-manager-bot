"""Bootstrap do bot Foco — long polling (F1)."""
from __future__ import annotations

import logging

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from src.config import TELEGRAM_BOT_TOKEN
from src.db.session import create_tables
from src.handlers.capture import cb_undo_capture, handle_capture
from src.handlers.common import (
    cmd_ajuda,
    cmd_inbox,
    cmd_ping,
    cmd_reiniciar,
    cmd_start,
    error_handler,
)
from src.handlers.lists import (
    cb_archive_list,
    cb_cancel_mgmt,
    cb_do_archive,
    cb_manage_list,
    cmd_listas,
    list_conversation,
)
from src.handlers.tasks import (
    cb_back_to_lists,
    cb_complete_task,
    cb_view_inbox,
    cb_view_list,
)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Iniciando Bot Foco...")
    create_tables()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("ajuda", cmd_ajuda))
    app.add_handler(CommandHandler("help", cmd_ajuda))
    app.add_handler(CommandHandler("listas", cmd_listas))
    app.add_handler(CommandHandler("inbox", cmd_inbox))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("reiniciar", cmd_reiniciar))

    # ConversationHandler de listas (deve vir antes do capture handler)
    app.add_handler(list_conversation)

    # Callbacks de navegação e tarefas
    app.add_handler(CallbackQueryHandler(cb_view_list, pattern=r"^view_list:"))
    app.add_handler(CallbackQueryHandler(cb_view_inbox, pattern=r"^view_inbox$"))
    app.add_handler(CallbackQueryHandler(cb_complete_task, pattern=r"^complete_task:"))
    app.add_handler(CallbackQueryHandler(cb_back_to_lists, pattern=r"^back_to_lists$"))
    app.add_handler(CallbackQueryHandler(cb_undo_capture, pattern=r"^undo_task:"))

    # Callbacks de gerenciamento de listas
    app.add_handler(CallbackQueryHandler(cb_manage_list, pattern=r"^manage_list:"))
    app.add_handler(CallbackQueryHandler(cb_archive_list, pattern=r"^archive_list:"))
    app.add_handler(CallbackQueryHandler(cb_do_archive, pattern=r"^do_archive:"))
    app.add_handler(CallbackQueryHandler(cb_cancel_mgmt, pattern=r"^cancel_mgmt$"))

    # Captura por texto livre — deve ser o último handler de mensagens
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_capture))

    app.add_error_handler(error_handler)

    logger.info("Bot pronto. Iniciando long polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
