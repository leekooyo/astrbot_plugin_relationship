from astrbot.api import logger
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)

from .config import PluginConfig
from .forward import ForwardTool
from .utils import get_ats, get_nickname, parse_multi_input


class NormalHandle:
    def __init__(self, config: PluginConfig):
        self.cfg = config

    async def get_group_list(self, event: AiocqhttpMessageEvent):
        items = await event.bot.get_group_list()
        if not items:
            yield event.plain_result("当前没有群。")
            return
        lines = [f"群列表 · 共 {len(items)} 项"]
        lines.extend(f"{i}. {item['group_name']}（{item['group_id']}）"
                     for i, item in enumerate(items, 1))
        lines.append("操作：/退群 <群号或序号>")
        yield event.plain_result("\n".join(lines)).use_t2i(True)

    async def get_friend_list(self, event: AiocqhttpMessageEvent):
        items = await event.bot.get_friend_list()
        if not items:
            yield event.plain_result("当前没有好友。")
            return
        lines = [f"好友列表 · 共 {len(items)} 项"]
        lines.extend(f"{i}. {item['nickname']}（{item['user_id']}）"
                     for i, item in enumerate(items, 1))
        lines.append("操作：/删好友 <QQ号或序号>")
        yield event.plain_result("\n".join(lines)).use_t2i(True)

    async def set_group_leave(self, event: AiocqhttpMessageEvent):
        """退群 <序号|群号|区间> [可批量]"""
        client = event.bot
        group_list = await client.get_group_list()

        if not group_list:
            yield event.plain_result("我还没加任何群")
            return

        raw = event.message_str
        indexes, ids = parse_multi_input(raw, total=len(group_list))

        if not indexes and not ids:
            yield event.plain_result("未指定退群目标。\n用法：/退群 <群号或序号> [更多目标]\n发送 /群列表 查看序号，多个目标用空格分隔。")
            return

        group_map = {str(g["group_id"]): g for g in group_list}
        msgs = []

        target_ids = {str(group_list[idx]["group_id"]) for idx in indexes} | set(ids)
        for gid in sorted(target_ids):
            g = group_map.get(gid)
            if not g:
                msgs.append(f"不存在群聊：{gid}")
                continue
            try:
                await client.set_group_leave(group_id=int(gid))
                msgs.append(f"退群请求已确认：{g['group_name']}({gid})")
                await ForwardTool.send_admin(event, self.cfg,
                    f"【机器人主动退群】群：{g['group_name']}({gid})\nQQ 接口已确认退群请求",
                    dedup_key=f"bot-left:{gid}", admin_only=True)
            except Exception as exc:
                msgs.append(f"退群失败：{g['group_name']}({gid})：{exc}")
                await ForwardTool.send_admin(event, self.cfg,
                    f"【机器人退群失败】群：{g['group_name']}({gid})\n原因：{exc}", admin_only=True)

        yield event.plain_result("\n".join(msgs))

    async def delete_friend(self, event: AiocqhttpMessageEvent):
        """删好友 <@昵称|QQ|序号|区间> [可批量]"""
        client = event.bot
        friend_list = await client.get_friend_list()

        if not friend_list:
            yield event.plain_result("我还没有好友")
            return

        # 先处理 @
        user_ids = set(get_ats(event))

        # 再解析文本
        raw = event.message_str
        indexes, ids = parse_multi_input(raw, total=len(friend_list))

        # 序号 → QQ
        for idx in indexes:
            user_ids.add(str(friend_list[idx]["user_id"]))

        # 直接 QQ
        user_ids |= ids

        if not user_ids:
            yield event.plain_result("未指定好友。\n用法：/删好友 <QQ号或序号> [更多目标]\n发送 /好友列表 查看序号。")
            return

        friend_map = {str(f["user_id"]): f for f in friend_list}
        msgs = []

        for uid in sorted(user_ids):
            f = friend_map.get(uid)
            if not f:
                msgs.append(f"不存在好友：{uid}")
                continue

            await client.delete_friend(user_id=int(uid))
            msgs.append(f"已删除好友：{f['nickname']}({uid})")

        yield event.plain_result("\n".join(msgs))

    async def append_manage_user(self, event: AiocqhttpMessageEvent):
        """添加审批员"""
        at_ids = get_ats(event)
        if not at_ids:
            yield event.plain_result("未指定审批员。\n用法：/加审批员 @QQ号\n示例：/加审批员 @<QQ号>\n私聊直接输入文字形式的 @QQ号 即可。")
            return
        for at_id in at_ids:
            nickname = await get_nickname(
                client=event.bot, group_id=event.get_group_id(), user_id=at_id
            )
            if self.cfg.is_manage_user(at_id):
                yield event.plain_result(f"「{nickname}」已在审批员列表中，无需重复添加。")
                continue
            self.cfg.add_manage_user(at_id)
            yield event.plain_result(f"已添加审批员「{nickname}」。")

    async def remove_manage_user(self, event: AiocqhttpMessageEvent):
        """移除审批员"""
        at_ids = get_ats(event)
        if not at_ids:
            yield event.plain_result("未指定审批员。\n用法：/减审批员 @QQ号\n示例：/减审批员 @<QQ号>\n私聊直接输入文字形式的 @QQ号 即可。")
            return
        for at_id in at_ids:
            nickname = await get_nickname(
                client=event.bot, group_id=event.get_group_id(), user_id=at_id
            )
            if not self.cfg.is_manage_user(at_id):
                yield event.plain_result(f"「{nickname}」不在审批员列表中，无需移除。")
                continue
            self.cfg.remove_manage_user(at_id)
            yield event.plain_result(f"已移除审批员「{nickname}」。")
