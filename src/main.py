"""Bootstrap do bot Task Manager — long polling."""
from __future__ import annotations

import logging

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from src.config import AUTHORIZED_CHAT_ID, TELEGRAM_BOT_TOKEN
from src.db.session import run_migrations
from src.handlers.blocker import (
    cb_blocker_aguardar,
    cb_blocker_archive,
    cb_blocker_cobrar,
    cb_blocker_cobrar_date,
    cb_blocker_data_date,
    cb_blocker_decidir_ok,
    cb_blocker_keep,
    cb_blocker_next_step_ok,
    cb_blocker_next_step_retry,
    cb_blocker_recurso_ok,
    cb_blocker_start,
    cb_blocker_type,
    cb_unblock,
)
from src.handlers.config_handler import (
    cb_config_back,
    cb_config_daily,
    cb_config_off_daily,
    cb_config_off_rev,
    cb_config_rev_dow,
    cb_config_set_daily,
    cb_config_set_dow,
    cb_config_set_rtime,
    cmd_config,
)
from src.handlers.rituals import (
    cb_rev_arch,
    cb_rev_date,
    cb_rev_manter,
    cb_rev_reagendar,
    cb_rev_skip,
    cb_rev_start,
    cb_rev_wait_arch,
    cb_rev_wait_cobrar,
    cb_rev_wait_destravar,
    cb_rev_wait_seguir,
    setup_jobs,
)
from src.handlers.agora import (
    cb_agora_adiar,
    cb_agora_adiar_date,
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
    cmd_amanha,
    cmd_buscar,
    cmd_casal,
    cmd_conquistas,
    cmd_hoje,
    cmd_inbox,
    cmd_ping,
    cmd_quadrantes,
    cmd_reiniciar,
    cmd_setgrupo,
    cmd_start,
    cmd_tudo,
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
from src.handlers.audio import handle_voice
from src.handlers.medicacoes import cmd_medicacoes, medicacoes_conversation
from src.handlers.task_detail import (
    cb_sub_complete,
    cb_task_detail,
    cb_task_move_to,
    cb_task_reorder,
    cb_task_set_due,
    cb_task_set_energy,
    cb_task_set_estimate,
    cb_task_set_quadrant,
    cb_task_set_recurrence,
    cb_task_start_move,
    note_conversation,
    title_conversation,
)
from src.handlers.tasks import (
    cb_back_to_lists,
    cb_complete_task,
    cb_view_inbox,
    cb_view_list,
    cmd_ver,
)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Iniciando Task Manager...")
    run_migrations()

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
    app.add_handler(CommandHandler("config", cmd_config))
    app.add_handler(CommandHandler("casal", cmd_casal))
    app.add_handler(CommandHandler("buscar", cmd_buscar))
    app.add_handler(CommandHandler("setgrupo", cmd_setgrupo))
    app.add_handler(CommandHandler("tudo", cmd_tudo))
    app.add_handler(CommandHandler("ver", cmd_ver))
    app.add_handler(CommandHandler("medicacoes", cmd_medicacoes))
    app.add_handler(CommandHandler("hoje", cmd_hoje))
    app.add_handler(CommandHandler("amanha", cmd_amanha))
    app.add_handler(CommandHandler("conquistas", cmd_conquistas))

    # ConversationHandlers (antes do capture handler)
    app.add_handler(title_conversation)
    app.add_handler(note_conversation)
    app.add_handler(list_conversation)
    app.add_handler(medicacoes_conversation)

    # Impedimentos
    app.add_handler(CallbackQueryHandler(cb_blocker_start, pattern=r"^blk_start:"))
    app.add_handler(CallbackQueryHandler(cb_blocker_type, pattern=r"^blk_t:"))
    app.add_handler(CallbackQueryHandler(cb_blocker_next_step_ok, pattern=r"^blk_nok:"))
    app.add_handler(CallbackQueryHandler(cb_blocker_next_step_retry, pattern=r"^blk_nretry:"))
    app.add_handler(CallbackQueryHandler(cb_blocker_decidir_ok, pattern=r"^blk_dok:"))
    app.add_handler(CallbackQueryHandler(cb_blocker_recurso_ok, pattern=r"^blk_rook:"))
    app.add_handler(CallbackQueryHandler(cb_blocker_aguardar, pattern=r"^blk_wait:"))
    app.add_handler(CallbackQueryHandler(cb_blocker_cobrar, pattern=r"^blk_cobrar:"))
    app.add_handler(CallbackQueryHandler(cb_blocker_cobrar_date, pattern=r"^blk_cd:"))
    app.add_handler(CallbackQueryHandler(cb_blocker_data_date, pattern=r"^blk_dd:"))
    app.add_handler(CallbackQueryHandler(cb_blocker_archive, pattern=r"^blk_arc:"))
    app.add_handler(CallbackQueryHandler(cb_blocker_keep, pattern=r"^blk_keep:"))
    app.add_handler(CallbackQueryHandler(cb_unblock, pattern=r"^unblock:"))

    # Revisão semanal
    app.add_handler(CallbackQueryHandler(cb_rev_start, pattern=r"^rv_start$"))
    app.add_handler(CallbackQueryHandler(cb_rev_skip, pattern=r"^rv_skip$"))
    app.add_handler(CallbackQueryHandler(cb_rev_reagendar, pattern=r"^rv_rg:"))
    app.add_handler(CallbackQueryHandler(cb_rev_date, pattern=r"^rv_rd:"))
    app.add_handler(CallbackQueryHandler(cb_rev_manter, pattern=r"^rv_ok:"))
    app.add_handler(CallbackQueryHandler(cb_rev_arch, pattern=r"^rv_arch:"))
    app.add_handler(CallbackQueryHandler(cb_rev_wait_cobrar, pattern=r"^rv_wc:"))
    app.add_handler(CallbackQueryHandler(cb_rev_wait_destravar, pattern=r"^rv_wu:"))
    app.add_handler(CallbackQueryHandler(cb_rev_wait_arch, pattern=r"^rv_wa:"))
    app.add_handler(CallbackQueryHandler(cb_rev_wait_seguir, pattern=r"^rv_ws:"))

    # /config
    app.add_handler(CallbackQueryHandler(cb_config_daily, pattern=r"^cfg_daily$"))
    app.add_handler(CallbackQueryHandler(cb_config_set_daily, pattern=r"^cfg_dt:"))
    app.add_handler(CallbackQueryHandler(cb_config_rev_dow, pattern=r"^cfg_rev_dow$"))
    app.add_handler(CallbackQueryHandler(cb_config_set_dow, pattern=r"^cfg_rdow:"))
    app.add_handler(CallbackQueryHandler(cb_config_set_rtime, pattern=r"^cfg_rt:"))
    app.add_handler(CallbackQueryHandler(cb_config_off_daily, pattern=r"^cfg_off_daily$"))
    app.add_handler(CallbackQueryHandler(cb_config_off_rev, pattern=r"^cfg_off_rev$"))
    app.add_handler(CallbackQueryHandler(cb_config_back, pattern=r"^cfg_back$"))

    # /agora
    app.add_handler(CallbackQueryHandler(cb_agora_tempo, pattern=r"^ag_t:"))
    app.add_handler(CallbackQueryHandler(cb_agora_energia, pattern=r"^ag_e:"))
    app.add_handler(CallbackQueryHandler(cb_agora_concluir, pattern=r"^ag_ok:"))
    app.add_handler(CallbackQueryHandler(cb_agora_outra, pattern=r"^ag_nx:"))
    app.add_handler(CallbackQueryHandler(cb_agora_adiar, pattern=r"^ag_ad:"))
    app.add_handler(CallbackQueryHandler(cb_agora_adiar_date, pattern=r"^ag_adf:"))

    # Detalhe e edição de tarefa
    app.add_handler(CallbackQueryHandler(cb_task_detail, pattern=r"^task_dt:"))
    app.add_handler(CallbackQueryHandler(cb_task_set_quadrant, pattern=r"^task_q:"))
    app.add_handler(CallbackQueryHandler(cb_task_set_energy, pattern=r"^task_e:"))
    app.add_handler(CallbackQueryHandler(cb_task_set_estimate, pattern=r"^task_m:"))
    app.add_handler(CallbackQueryHandler(cb_task_set_due, pattern=r"^task_d:"))
    app.add_handler(CallbackQueryHandler(cb_task_set_recurrence, pattern=r"^task_rec:"))
    app.add_handler(CallbackQueryHandler(cb_task_start_move, pattern=r"^task_list:"))
    app.add_handler(CallbackQueryHandler(cb_task_move_to, pattern=r"^mv:"))
    app.add_handler(CallbackQueryHandler(cb_task_reorder, pattern=r"^task_up:"))
    app.add_handler(CallbackQueryHandler(cb_task_reorder, pattern=r"^task_dn:"))
    app.add_handler(CallbackQueryHandler(cb_sub_complete, pattern=r"^sub_done:"))

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

    # Voz e áudio — antes do catch-all de texto
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))

    # Captura por texto livre — deve ser o último handler de mensagens
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_capture))

    app.add_error_handler(error_handler)

    setup_jobs(app, AUTHORIZED_CHAT_ID)

    logger.info("Bot pronto. Iniciando long polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
