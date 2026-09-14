"""TG Media Vault V1 graphical interface.

Run with:
    python vault_ui.py
"""

from datetime import datetime, timedelta, timezone

try:
    from nicegui import ui
except ImportError as exc:  # pragma: no cover - manual entry point
    raise SystemExit(
        "NiceGUI is required. Install with: pip install -r requirements-webui.txt"
    ) from exc

from telethon.errors import (
    PasswordHashInvalidError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
)

from tg_media_vault.archive_service import ArchiveProgress, ArchiveService
from tg_media_vault.dialogs import list_media_dialogs
from tg_media_vault.scanner import scan_chat
from tg_media_vault.settings import (
    DATABASE_PATH,
    AppSettings,
    load_settings,
    save_settings,
    session_path,
)
from tg_media_vault.telegram_session import TelegramSession
from tg_media_vault.vault_db import VaultDatabase


settings = load_settings()
database = VaultDatabase(DATABASE_PATH)
state = {
    "session": None,
    "session_credentials": None,
    "phone_code_hash": None,
    "dialogs": {},
    "scan_result": None,
    "account_id": None,
}


ui.add_css(
    """
    body { background: #f6f7f9; }
    .vault-shell { max-width: 1180px; margin: 0 auto; padding: 28px 24px 48px; }
    .vault-card { background: white; border: 1px solid #e5e7eb; border-radius: 18px;
                  padding: 22px; box-shadow: 0 8px 30px rgba(15, 23, 42, .05); }
    .muted { color: #6b7280; font-size: 13px; }
    .metric { min-width: 145px; padding: 14px 16px; border-radius: 14px;
              background: #f8fafc; border: 1px solid #eef2f7; }
    """
)


@ui.page("/")
def index():
    ui.page_title("TG Media Vault")

    with ui.column().classes("vault-shell w-full gap-5"):
        with ui.row().classes("items-center justify-between w-full"):
            with ui.column().classes("gap-0"):
                ui.label("TG Media Vault").classes("text-2xl font-bold")
                ui.label("Telegram 媒体归档 · V1.1").classes("muted")
            connection_badge = ui.badge("未连接", color="grey")

        # ------------------------------------------------------------------
        # Connection / authentication
        # ------------------------------------------------------------------
        with ui.column().classes("vault-card w-full gap-4"):
            ui.label("1. 连接 Telegram").classes("text-lg font-semibold")
            ui.label(
                "首次使用需要 Telegram API ID / API Hash。登录成功后 Session 会保存在本机用户目录。"
            ).classes("muted")

            with ui.row().classes("w-full gap-3"):
                api_id_input = ui.input(
                    "API ID", value=str(settings.api_id or "")
                ).classes("grow")
                api_hash_input = ui.input(
                    "API Hash", value=settings.api_hash, password=True
                ).classes("grow")

            with ui.row().classes("w-full gap-3"):
                phone_input = ui.input("手机号，例如 +65... ").classes("grow")
                code_input = ui.input("验证码").classes("grow")
                password_input = ui.input(
                    "两步验证密码（如启用）", password=True
                ).classes("grow")

            auth_status = ui.label("等待连接").classes("muted")

        # ------------------------------------------------------------------
        # Channel / scan controls
        # ------------------------------------------------------------------
        with ui.column().classes("vault-card w-full gap-4"):
            ui.label("2. 选择频道并扫描").classes("text-lg font-semibold")
            channel_select = ui.select(
                options=[], label="频道 / 群组"
            ).classes("w-full")

            with ui.row().classes("w-full gap-3 items-end"):
                media_types_select = ui.select(
                    options={
                        "photo": "图片",
                        "video": "视频",
                        "gif": "GIF / 动图",
                        "file": "文件",
                    },
                    value=["photo", "video", "gif", "file"],
                    multiple=True,
                    label="媒体类型",
                ).classes("grow")
                time_range_select = ui.select(
                    options={
                        "all": "全部",
                        "7": "最近 7 天",
                        "30": "最近 30 天",
                        "90": "最近 90 天",
                    },
                    value="all",
                    label="时间范围",
                ).classes("w-52")

            output_input = ui.input(
                "保存位置", value=settings.normalized_download_directory()
            ).classes("w-full")

            with ui.row().classes("gap-3"):
                concurrency_input = ui.number(
                    "并发下载", value=settings.max_concurrent_downloads, min=1, max=8
                ).classes("w-40")
                scan_button = ui.button("扫描媒体", icon="search")

            with ui.row().classes("w-full gap-3 flex-wrap"):
                photo_metric = _metric("图片", "0")
                video_metric = _metric("视频", "0")
                gif_metric = _metric("GIF", "0")
                file_metric = _metric("文件", "0")
                archived_metric = _metric("已归档", "0")

            scan_status = ui.label("尚未扫描").classes("muted")

        # ------------------------------------------------------------------
        # Archive controls / progress
        # ------------------------------------------------------------------
        with ui.column().classes("vault-card w-full gap-4"):
            ui.label("3. 开始归档").classes("text-lg font-semibold")
            overall_progress = ui.linear_progress(value=0).classes("w-full")
            file_progress = ui.linear_progress(value=0).classes("w-full")
            progress_label = ui.label("等待任务").classes("muted")
            with ui.row().classes("gap-3"):
                archive_button = ui.button("开始下载", icon="download")
                refresh_button = ui.button(
                    "刷新频道", icon="refresh", color="grey"
                ).props("outline")

        # ------------------------------------------------------------------
        # Recent archive history
        # ------------------------------------------------------------------
        with ui.column().classes("vault-card w-full gap-4"):
            with ui.row().classes("items-center justify-between w-full"):
                ui.label("4. 最近归档").classes("text-lg font-semibold")
                history_button = ui.button(
                    "刷新历史", icon="history", color="grey"
                ).props("outline")
            history_status = ui.label("登录后显示最近 100 条归档记录").classes(
                "muted"
            )
            history_table = ui.table(
                columns=[
                    {
                        "name": "downloaded_at",
                        "label": "时间",
                        "field": "downloaded_at",
                        "align": "left",
                    },
                    {
                        "name": "chat",
                        "label": "频道 / 群组",
                        "field": "chat",
                        "align": "left",
                    },
                    {
                        "name": "media_type",
                        "label": "类型",
                        "field": "media_type",
                        "align": "left",
                    },
                    {
                        "name": "file_name",
                        "label": "文件",
                        "field": "file_name",
                        "align": "left",
                    },
                    {
                        "name": "size",
                        "label": "大小",
                        "field": "size",
                        "align": "right",
                    },
                ],
                rows=[],
                row_key="key",
                pagination=10,
            ).classes("w-full")

        def invalidate_scan(message="条件已变化，请重新扫描"):
            state["scan_result"] = None
            photo_metric.set_text("0")
            video_metric.set_text("0")
            gif_metric.set_text("0")
            file_metric.set_text("0")
            archived_metric.set_text("0")
            scan_status.set_text(message)
            overall_progress.set_value(0)
            file_progress.set_value(0)
            progress_label.set_text("等待任务")

        async def ensure_session():
            raw_api_id = str(api_id_input.value or "").strip()
            api_hash = str(api_hash_input.value or "").strip()
            if not raw_api_id or not api_hash:
                ui.notify("请先填写 API ID 和 API Hash", type="warning")
                return None
            try:
                api_id = int(raw_api_id)
            except ValueError:
                ui.notify("API ID 必须是数字", type="negative")
                return None

            credentials = (api_id, api_hash)
            existing = state.get("session")
            if existing is None or state.get("session_credentials") != credentials:
                if existing is not None:
                    try:
                        await existing.disconnect()
                    except Exception:
                        pass
                state["session"] = TelegramSession(
                    api_id=api_id,
                    api_hash=api_hash,
                    session_path=session_path(),
                )
                state["session_credentials"] = credentials
                state["phone_code_hash"] = None
                state["dialogs"] = {}
                state["account_id"] = None
                channel_select.set_options([])
                channel_select.value = None
                connection_badge.set_text("未连接")
                connection_badge.props("color=grey")
                auth_status.set_text("连接参数已更新，请重新连接 Telegram")
                invalidate_scan("连接参数已更新，请重新扫描")

            current_settings = AppSettings(
                api_id=api_id,
                api_hash=api_hash,
                download_directory=str(output_input.value or "").strip(),
                max_concurrent_downloads=max(
                    1, int(concurrency_input.value or 4)
                ),
            )
            save_settings(current_settings)
            return state["session"]

        async def refresh_history():
            account_id = state.get("account_id")
            if not account_id:
                history_table.rows = []
                history_table.update()
                history_status.set_text("登录后显示最近 100 条归档记录")
                return

            title_by_id = {
                str(item.id): item.title for item in state.get("dialogs", {}).values()
            }
            history = database.recent_downloads(str(account_id), limit=100)
            history_table.rows = [
                {
                    "key": "{0}:{1}".format(item.chat_id, item.message_id),
                    "downloaded_at": item.downloaded_at,
                    "chat": title_by_id.get(item.chat_id, item.chat_id),
                    "media_type": item.media_type,
                    "file_name": item.file_name,
                    "size": _format_bytes(item.file_size),
                }
                for item in history
            ]
            history_table.update()
            history_status.set_text("最近 {0} 条归档记录".format(len(history)))

        async def refresh_dialogs():
            session = await ensure_session()
            if session is None:
                return
            if not await session.is_authorized():
                connection_badge.set_text("未登录")
                connection_badge.props("color=orange")
                auth_status.set_text("请发送验证码并完成登录")
                return

            dialogs = await list_media_dialogs(session.client)
            lookup = {
                "{0} · {1}".format(item.title, item.id): item for item in dialogs
            }
            state["dialogs"] = lookup
            channel_select.set_options(list(lookup.keys()))
            state["account_id"] = await session.account_id()
            connection_badge.set_text("已连接")
            connection_badge.props("color=positive")
            auth_status.set_text("已登录，读取到 {0} 个频道/群组".format(len(dialogs)))
            if dialogs and channel_select.value not in lookup:
                channel_select.value = next(iter(lookup))
            await refresh_history()

        async def connect_or_send_code():
            session = await ensure_session()
            if session is None:
                return
            if await session.is_authorized():
                await refresh_dialogs()
                return

            phone = str(phone_input.value or "").strip()
            if not phone:
                ui.notify("请输入手机号", type="warning")
                return
            try:
                state["phone_code_hash"] = await session.send_code(phone)
            except Exception as exc:  # Telethon reports provider/network errors here
                ui.notify("发送验证码失败：{0}".format(exc), type="negative")
                return
            auth_status.set_text("验证码已发送，请填写验证码后点击“完成登录”")
            ui.notify("验证码已发送", type="positive")

        async def finish_login():
            session = await ensure_session()
            if session is None:
                return
            phone = str(phone_input.value or "").strip()
            code = str(code_input.value or "").strip()
            if not phone or not code:
                ui.notify("请填写手机号和验证码", type="warning")
                return
            try:
                await session.sign_in_code(
                    phone=phone,
                    code=code,
                    phone_code_hash=state.get("phone_code_hash"),
                )
            except SessionPasswordNeededError:
                password = str(password_input.value or "")
                if not password:
                    ui.notify("该账号启用了两步验证，请输入密码", type="warning")
                    return
                try:
                    await session.sign_in_password(password)
                except PasswordHashInvalidError:
                    ui.notify("两步验证密码不正确", type="negative")
                    return
                except Exception as exc:
                    ui.notify("两步验证失败：{0}".format(exc), type="negative")
                    return
            except PhoneCodeExpiredError:
                ui.notify("验证码已过期，请重新获取", type="negative")
                return
            except PhoneCodeInvalidError:
                ui.notify("验证码不正确", type="negative")
                return
            except Exception as exc:
                ui.notify("登录失败：{0}".format(exc), type="negative")
                return
            await refresh_dialogs()
            ui.notify("Telegram 登录成功", type="positive")

        with ui.row().classes("gap-3"):
            ui.button("连接 / 获取验证码", on_click=connect_or_send_code).props(
                "outline"
            )
            ui.button("完成登录", on_click=finish_login)

        async def run_scan():
            session = await ensure_session()
            if session is None or not await session.is_authorized():
                ui.notify("请先登录 Telegram", type="warning")
                return
            selected_label = channel_select.value
            dialog = state.get("dialogs", {}).get(selected_label)
            if dialog is None:
                ui.notify("请选择频道或群组", type="warning")
                return

            selected_types = list(media_types_select.value or [])
            if not selected_types:
                ui.notify("至少选择一种媒体类型", type="warning")
                return

            start_date = None
            range_value = str(time_range_select.value or "all")
            if range_value != "all":
                start_date = datetime.now(timezone.utc) - timedelta(
                    days=int(range_value)
                )

            scan_button.disable()
            scan_status.set_text("正在扫描…")
            try:
                result = await scan_chat(
                    client=session.client,
                    account_id=str(state["account_id"] or await session.account_id()),
                    chat_id=dialog.id,
                    database=database,
                    media_types=selected_types,
                    start_date=start_date,
                )
                state["scan_result"] = result
                photo_metric.set_text(str(result.counts.get("photo", 0)))
                video_metric.set_text(str(result.counts.get("video", 0)))
                gif_metric.set_text(str(result.counts.get("gif", 0)))
                file_metric.set_text(str(result.counts.get("file", 0)))
                archived_metric.set_text(str(result.already_archived))
                scan_status.set_text(
                    "{0}：发现 {1} 个待归档媒体，已跳过 {2} 个历史项目".format(
                        result.title, len(result.items), result.already_archived
                    )
                )
            except Exception as exc:
                scan_status.set_text("扫描失败")
                ui.notify("扫描失败：{0}".format(exc), type="negative")
            finally:
                scan_button.enable()

        async def run_archive():
            result = state.get("scan_result")
            if result is None or not result.items:
                ui.notify("请先扫描，并确保有待归档媒体", type="warning")
                return
            session = await ensure_session()
            if session is None or not await session.is_authorized():
                ui.notify("请先登录 Telegram", type="warning")
                return

            output_dir = str(output_input.value or "").strip()
            if not output_dir:
                ui.notify("请选择或输入保存位置", type="warning")
                return

            archive_button.disable()
            overall_progress.set_value(0)
            file_progress.set_value(0)

            def on_progress(progress: ArchiveProgress):
                overall_progress.set_value(
                    min(1.0, progress.index / max(1, progress.total_items))
                )
                if progress.total_bytes > 0:
                    file_progress.set_value(
                        min(1.0, progress.current_bytes / progress.total_bytes)
                    )
                else:
                    file_progress.set_value(0)
                progress_label.set_text(
                    "[{0}/{1}] {2} · {3}".format(
                        progress.index,
                        progress.total_items,
                        progress.status,
                        progress.item.file_name,
                    )
                )

            service = ArchiveService(
                client=session.client,
                database=database,
                account_id=str(state["account_id"] or await session.account_id()),
                root_directory=output_dir,
                max_concurrent_downloads=max(
                    1, int(concurrency_input.value or 4)
                ),
            )
            try:
                summary = await service.archive_items(
                    chat_id=result.chat_id,
                    chat_title=result.title,
                    items=result.items,
                    progress_hook=on_progress,
                )
                overall_progress.set_value(1)
                progress_label.set_text(
                    "完成：下载 {0} · 跳过 {1} · 失败 {2}".format(
                        summary.downloaded, summary.skipped, summary.failed
                    )
                )
                ui.notify(
                    "归档完成：{0} 个成功，{1} 个失败".format(
                        summary.downloaded, summary.failed
                    ),
                    type="positive" if summary.failed == 0 else "warning",
                )
                await refresh_history()
                # Re-scan so newly persisted SQLite rows are immediately reflected.
                await run_scan()
            except Exception as exc:
                ui.notify("下载任务失败：{0}".format(exc), type="negative")
            finally:
                archive_button.enable()

        channel_select.on_value_change(
            lambda _: invalidate_scan("频道已变化，请重新扫描")
        )
        media_types_select.on_value_change(
            lambda _: invalidate_scan("媒体类型已变化，请重新扫描")
        )
        time_range_select.on_value_change(
            lambda _: invalidate_scan("时间范围已变化，请重新扫描")
        )
        scan_button.on("click", run_scan)
        archive_button.on("click", run_archive)
        refresh_button.on("click", refresh_dialogs)
        history_button.on("click", refresh_history)

        # If credentials + an authorized session already exist, connect quietly.
        if settings.api_id and settings.api_hash:
            ui.timer(0.5, refresh_dialogs, once=True)


def _metric(label: str, initial: str):
    with ui.column().classes("metric gap-0"):
        ui.label(label).classes("muted")
        value = ui.label(initial).classes("text-xl font-semibold")
    return value


def _format_bytes(size: int) -> str:
    value = float(max(0, int(size)))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return "{0:.1f} {1}".format(value, unit)
        value /= 1024
    return "0 B"


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="TG Media Vault", port=8081, dark=False, show=True, reload=False)
