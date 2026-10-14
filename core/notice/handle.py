import asyncio

from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)

from ..config import PluginConfig
from ..forward import ForwardTool
from .decision import NoticeDecision
from .model import NoticeMessage


class NoticeHandle:
    def __init__(self, config: PluginConfig):
        self.cfg = config

    async def handle(self, event: AiocqhttpMessageEvent):
        raw = getattr(event.message_obj, "raw_message", {})
        if not isinstance(raw, dict):
            return
        notice = NoticeMessage.from_raw(raw)

        if not notice.is_self_notice():
            return

        if (notice.post_type == "notice" and notice.notice_type == "group_decrease"
                and notice.sub_type == "leave" and notice.user_id == notice.self_id):
            await ForwardTool.send_admin(event, self.cfg,
                f"【机器人实际退群】群号：{notice.group_id}",
                dedup_key=f"bot-left:{notice.group_id}", admin_only=True)
            return

        decision = NoticeDecision(event.bot, notice, self.cfg)
        try:
            result = await decision.decide()
        except Exception as exc:
            if notice.notice_type == "group_increase":
                await ForwardTool.send_admin(event, self.cfg,
                    f"【机器人实际入群】群号：{notice.group_id}\n入群后规则检查失败：{exc}", admin_only=True)
            elif notice.notice_type == "group_decrease":
                await ForwardTool.send_admin(event, self.cfg,
                    f"【机器人被踢出群】群号：{notice.group_id}\n通知详情读取失败：{exc}", admin_only=True)
            return

        # 操作者提示
        if result.operator_reply:
            yield event.plain_result(result.operator_reply)

        if result.check_group and result.admin_reply and not result.leave_group:
            await ForwardTool.send_admin(event, self.cfg, result.admin_reply, admin_only=True)
            result.admin_reply = ""

        # 查群
        if (
            self.cfg.check.check_new_group
            and result.check_group
            and (self.cfg.manage_group or self.cfg.admin_id)
        ):
            # 延迟
            if self.cfg.check.delay > 0:
                await asyncio.sleep(self.cfg.check.delay)
            # 转发
            use_group = (self.cfg.raw_data().get("notify_target", "admin_private") == "review_group"
                         and bool(self.cfg.manage_group))
            fgid = int(self.cfg.manage_group) if use_group else None
            fuid = None if use_group else (int(self.cfg.admin_id) if self.cfg.admin_id else None)
            await ForwardTool.source_forward(
                client=event.bot,
                count=self.cfg.check.count,
                source_group_id=int(event.get_group_id()),
                source_user_id=int(event.get_sender_id()),
                forward_group_id=fgid,
                forward_user_id=fuid,
                batch_size=self.cfg.check.batch_size,
            )

        # 拉黑群聊
        if result.black_group:
            self.cfg.add_black_group(notice.group_id)

        # 拉黑用户
        if result.black_user:
            if notice.operator_id and notice.operator_id != notice.self_id:
                self.cfg.add_block_user(notice.operator_id)
            else:
                result.admin_reply += "\n无法确认踢人者，未拉黑用户"

        # 退群
        if result.leave_group:
            await asyncio.sleep(5)
            try:
                await event.bot.set_group_leave(group_id=int(notice.group_id))
                result.admin_reply += "\n退群请求已由 QQ 接口确认"
            except Exception as exc:
                result.admin_reply += f"\n退群失败：{exc}"

        if result.admin_reply and not (
            notice.notice_type == "group_ban" and not self.cfg.raw_data().get("notify_bot_ban", False)
        ):
            await ForwardTool.send_admin(event, self.cfg, result.admin_reply, admin_only=True)

        event.stop_event()
