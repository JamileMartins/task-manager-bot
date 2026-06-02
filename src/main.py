"""Bootstrap do bot Task Manager — long polling."""
from __future__ import annotations

import asyncio
import logging

from telegram import BotCommand, MenuButtonCommands, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    TypeHandler,
    filters,
)

from src.config import BOT_TOKENS, TELEGRAM_BOT_TOKEN
from src.db.session import run_migrations
from src.handlers import notify
from src.handlers.blocker import (
    cb_blocker_aguardar,
    cb_blocker_archive,
    cb_blocker_cobrar,
    cb_blocker_cobrar_date,
    cb_blocker_data_date,
    cb_blocker_decidir_ok,
    cb_blocker_dep_page,
    cb_blocker_dep_pick,
    cb_blocker_keep,
    cb_blocker_next_step_ok,
    cb_blocker_next_step_retry,
    cb_blocker_nota_skip,
    cb_blocker_nota_start,
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
    cb_overdue_adiar,
    cb_overdue_arch,
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
    cb_set_energia_dia,
    setup_jobs,
)
from src.handlers.agora import (
    cb_agora_adiar,
    cb_agora_adiar_date,
    cb_agora_concluir,
    cb_agora_energia,
    cb_agora_outra,
    cb_agora_pular,
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
    cb_noop,
    cmd_ajuda,
    cmd_amanha,
    cmd_buscar,
    cmd_casal,
    cmd_conquistas,
    cmd_exportar,
    cmd_hoje,
    cmd_inbox,
    cmd_pausar,
    cmd_ping,
    cmd_progresso,
    cmd_projetos,
    cmd_proximos,
    cmd_quadrantes,
    cmd_reiniciar,
    cmd_retomar,
    cmd_setgrupo,
    cmd_start,
    cmd_tudo,
    error_handler,
)
from src.handlers.foco import (
    cb_foco_cancelar,
    cb_foco_ciclo,
    cb_foco_descanso,
    cb_foco_encerrar,
    cb_foco_pular,
    cmd_foco,
    cmd_parar_foco,
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
from src.handlers.couple import (
    cmd_casal_convidar,
    cmd_casal_entrar,
    cmd_casal_status,
)
from src.handlers.medicacoes import cmd_medicacoes, medicacoes_conversation
from src.handlers.ordem import cmd_ordem
from src.handlers.task_detail import (
    cb_sub_complete,
    cb_task_assign,
    cb_task_detail,
    cb_task_set_category,
    cb_task_set_couple,
    cb_task_move_force,
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
    cb_view_casal,
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

_BOT_COMMANDS = [
    BotCommand("agora",      "Escolhe UMA tarefa para agora"),
    BotCommand("hoje",       "Focos e prazos de hoje"),
    BotCommand("amanha",     "Tarefas com prazo amanhã"),
    BotCommand("proximos",   "Agenda dos próximos dias"),
    BotCommand("inbox",      "Caixa de entrada"),
    BotCommand("listas",     "Ver e gerenciar listas"),
    BotCommand("tudo",       "Todas as tarefas abertas"),
    BotCommand("progresso",  "Progresso por lista"),
    BotCommand("conquistas", "Histórico de conclusões"),
    BotCommand("exportar",   "Tarefas abertas em texto"),
    BotCommand("foco",       "Iniciar pomodoro (padrão 50+15 min)"),
    BotCommand("medicacoes", "Checklist de medicações"),
    BotCommand("casal",      "Tarefas compartilhadas com seu par"),
    BotCommand("ordem",      "Cadeias de dependência em ordem de execução"),
    BotCommand("buscar",     "Buscar tarefa por palavra"),
    BotCommand("pausar",     "Silenciar notificações por N dias"),
    BotCommand("retomar",    "Reativar notificações"),
    BotCommand("config",     "Configurações do bot"),
    BotCommand("ajuda",      "Tudo que o bot sabe fazer"),
    BotCommand("ping",       "Verificar se está funcionando"),
]


async def _setup_menu(app: Application) -> None:
    await app.bot.set_my_commands(_BOT_COMMANDS)
    await app.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    logger.info("Menu de comandos registrado no Telegram.")


def _register_handlers(app: Application) -> None:
    # Tracking de qual bot atende cada chat (para notificações de casal) — grupo -1 roda primeiro.
    app.add_handler(TypeHandler(Update, notify.track_bot), group=-1)

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
    app.add_handler(CommandHandler("casal_convidar", cmd_casal_convidar))
    app.add_handler(CommandHandler("casal_entrar", cmd_casal_entrar))
    app.add_handler(CommandHandler("casal_status", cmd_casal_status))
    app.add_handler(CommandHandler("buscar", cmd_buscar))
    app.add_handler(CommandHandler("setgrupo", cmd_setgrupo))
    app.add_handler(CommandHandler("tudo", cmd_tudo))
    app.add_handler(CommandHandler("ver", cmd_ver))
    app.add_handler(CommandHandler("medicacoes", cmd_medicacoes))
    app.add_handler(CommandHandler("hoje", cmd_hoje))
    app.add_handler(CommandHandler("amanha", cmd_amanha))
    app.add_handler(CommandHandler("conquistas", cmd_conquistas))
    app.add_handler(CommandHandler("exportar", cmd_exportar))
    app.add_handler(CommandHandler("proximos", cmd_proximos))
    app.add_handler(CommandHandler("progresso", cmd_progresso))
    app.add_handler(CommandHandler("projetos", cmd_projetos))
    app.add_handler(CommandHandler("pausar", cmd_pausar))
    app.add_handler(CommandHandler("retomar", cmd_retomar))
    app.add_handler(CommandHandler("foco", cmd_foco))
    app.add_handler(CommandHandler("parar_foco", cmd_parar_foco))
    app.add_handler(CommandHandler("ordem", cmd_ordem))
    app.add_handler(CallbackQueryHandler(cb_noop, pattern=r"^noop$"))

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
    app.add_handler(CallbackQueryHandler(cb_blocker_nota_start, pattern=r"^blk_nota_s:"))
    app.add_handler(CallbackQueryHandler(cb_blocker_nota_skip, pattern=r"^blk_nota_skip:"))
    app.add_handler(CallbackQueryHandler(cb_blocker_dep_pick, pattern=r"^blk_dep:"))
    app.add_handler(CallbackQueryHandler(cb_blocker_dep_page, pattern=r"^blk_tp:"))
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

    # Energia do dia
    app.add_handler(CallbackQueryHandler(cb_set_energia_dia, pattern=r"^edia:"))

    # Prazo vencido
    app.add_handler(CallbackQueryHandler(cb_overdue_adiar, pattern=r"^od_adiar:"))
    app.add_handler(CallbackQueryHandler(cb_overdue_arch, pattern=r"^od_arch:"))

    # Pomodoro
    app.add_handler(CallbackQueryHandler(cb_foco_cancelar, pattern=r"^foco_cancel$"))
    app.add_handler(CallbackQueryHandler(cb_foco_descanso, pattern=r"^foco_descanso:"))
    app.add_handler(CallbackQueryHandler(cb_foco_pular, pattern=r"^foco_pular$"))
    app.add_handler(CallbackQueryHandler(cb_foco_ciclo, pattern=r"^foco_ciclo:"))
    app.add_handler(CallbackQueryHandler(cb_foco_encerrar, pattern=r"^foco_encerrar$"))

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
    app.add_handler(CallbackQueryHandler(cb_agora_pular, pattern=r"^ag_pular:"))
    app.add_handler(CallbackQueryHandler(cb_agora_adiar, pattern=r"^ag_ad:"))
    app.add_handler(CallbackQueryHandler(cb_agora_adiar_date, pattern=r"^ag_adf:"))

    # Detalhe e edição de tarefa
    app.add_handler(CallbackQueryHandler(cb_task_detail, pattern=r"^task_dt:"))
    app.add_handler(CallbackQueryHandler(cb_task_set_category, pattern=r"^task_cat:"))
    app.add_handler(CallbackQueryHandler(cb_task_set_couple, pattern=r"^task_couple:"))
    app.add_handler(CallbackQueryHandler(cb_task_assign, pattern=r"^task_assign:"))
    app.add_handler(CallbackQueryHandler(cb_task_set_quadrant, pattern=r"^task_q:"))
    app.add_handler(CallbackQueryHandler(cb_task_set_energy, pattern=r"^task_e:"))
    app.add_handler(CallbackQueryHandler(cb_task_set_estimate, pattern=r"^task_m:"))
    app.add_handler(CallbackQueryHandler(cb_task_set_due, pattern=r"^task_d:"))
    app.add_handler(CallbackQueryHandler(cb_task_set_recurrence, pattern=r"^task_rec:"))
    app.add_handler(CallbackQueryHandler(cb_task_start_move, pattern=r"^task_list:"))
    app.add_handler(CallbackQueryHandler(cb_task_move_to, pattern=r"^mv:"))
    app.add_handler(CallbackQueryHandler(cb_task_move_force, pattern=r"^mv_force:"))
    app.add_handler(CallbackQueryHandler(cb_task_reorder, pattern=r"^task_up:"))
    app.add_handler(CallbackQueryHandler(cb_task_reorder, pattern=r"^task_dn:"))
    app.add_handler(CallbackQueryHandler(cb_sub_complete, pattern=r"^sub_done:"))

    # Navegação e tarefas
    app.add_handler(CallbackQueryHandler(cb_view_list, pattern=r"^view_list:"))
    app.add_handler(CallbackQueryHandler(cb_view_inbox, pattern=r"^view_inbox$"))
    app.add_handler(CallbackQueryHandler(cb_view_casal, pattern=r"^view_casal$"))
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


def _build_app(token: str, *, with_menu: bool) -> Application:
    builder = Application.builder().token(token)
    if with_menu:
        builder = builder.post_init(_setup_menu)
    app = builder.build()
    _register_handlers(app)
    return app


async def _run_multiple(apps: list[Application]) -> None:
    """Roda vários Applications (um por token) no mesmo event loop (modo casal multi-bot)."""
    for app in apps:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
    logger.info("Todos os %d bots em polling.", len(apps))
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        for app in apps:
            await app.updater.stop()
            await app.stop()
            await app.shutdown()


def main() -> None:
    logger.info("Iniciando Task Manager...")
    run_migrations()

    # App principal: menu + jobs. Apps extras (um por parceiro) só recebem updates;
    # jobs ficam só no principal para não duplicar resumos/lembretes.
    primary = _build_app(BOT_TOKENS[0], with_menu=True)
    setup_jobs(primary)

    if len(BOT_TOKENS) == 1:
        logger.info("Bot pronto (1 token). Iniciando long polling...")
        primary.run_polling(drop_pending_updates=True)
        return

    extras = [_build_app(t, with_menu=False) for t in BOT_TOKENS[1:]]
    logger.info("Modo casal multi-bot: %d bots.", len(BOT_TOKENS))
    asyncio.run(_run_multiple([primary, *extras]))


if __name__ == "__main__":
    main()
