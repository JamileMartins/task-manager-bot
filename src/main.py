"""Bootstrap do bot Foco — long polling."""
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
from src.handlers.agora import (
    cb_agora_adiar,
    cb_agora_concluir,
    cb_agora_energia,
    cb_agora_outra,
    cb_agora_tempo,
    cmd_agora,
)
from src.handlers.capture import (
    cb_adj_task,
    cb_adjust_capture,
    cb_approve_capture,
    cb_cancel_capture,
    cb_undo_capture,
    handle_capture,
)
from src.handlers.common import (
    cmd_ajuda,
    cmd_inbox,
    cmd_ping,
    cmd_quadrantes,
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
from src.handlers.task_detail import (
    cb_task_detail,
    cb_task_move_to,
    cb_task_reorder,
    cb_task_set_due,
    cb_task_set_energy,
    cb_task_set_estimate,
    cb_task_set_quadrant,
    cb_task_start_move,
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
    app.add_handler(CommandHandler("agora", cmd_agora))
    app.add_handler(CommandHandler("quadrantes", cmd_quadrantes))

    # ConversationHandler de listas (antes do capture handler)
    app.add_handler(list_conversation)

    # /agora
    app.add_handler(CallbackQueryHandler(cb_agora_tempo, pattern=r"^ag_t:"))
    app.add_handler(CallbackQueryHandler(cb_agora_energia, pattern=r"^ag_e:"))
    app.add_handler(CallbackQueryHandler(cb_agora_concluir, pattern=r"^ag_ok:"))
    app.add_handler(CallbackQueryHandler(cb_agora_outra, pattern=r"^ag_nx:"))
    app.add_handler(CallbackQueryHandler(cb_agora_adiar, pattern=r"^ag_ad:"))

    # Detalhe e edição de tarefa
    app.add_handler(CallbackQueryHandler(cb_task_detail, pattern=r"^task_dt:"))
    app.add_handler(CallbackQueryHandler(cb_task_set_quadrant, pattern=r"^task_q:"))
    app.add_handler(CallbackQueryHandler(cb_task_set_energy, pattern=r"^task_e:"))
    app.add_handler(CallbackQueryHandler(cb_task_set_estimate, pattern=r"^task_m:"))
    app.add_handler(CallbackQueryHandler(cb_task_set_due, pattern=r"^task_d:"))
    app.add_handler(CallbackQueryHandler(cb_task_start_move, pattern=r"^task_list:"))
    app.add_handler(CallbackQueryHandler(cb_task_move_to, pattern=r"^mv:"))
    app.add_handler(CallbackQueryHandler(cb_task_reorder, pattern=r"^task_up:"))
    app.add_handler(CallbackQueryHandler(cb_task_reorder, pattern=r"^task_dn:"))

    # Navegação e tarefas
    app.add_handler(CallbackQueryHandler(cb_view_list, pattern=r"^view_list:"))
    app.add_handler(CallbackQueryHandler(cb_view_inbox, pattern=r"^view_inbox$"))
    app.add_handler(CallbackQueryHandler(cb_complete_task, pattern=r"^complete_task:"))
    app.add_handler(CallbackQueryHandler(cb_back_to_lists, pattern=r"^back_to_lists$"))

    # Captura
    app.add_handler(CallbackQueryHandler(cb_approve_capture, pattern=r"^approve_capture$"))
    app.add_handler(CallbackQueryHandler(cb_cancel_capture, pattern=r"^cancel_capture$"))
    app.add_handler(CallbackQueryHandler(cb_adjust_capture, pattern=r"^adjust_capture$"))
    app.add_handler(CallbackQueryHandler(cb_adj_task, pattern=r"^adj:"))
    app.add_handler(CallbackQueryHandler(cb_undo_capture, pattern=r"^undo_task:"))

    # Gerenciamento de listas
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
