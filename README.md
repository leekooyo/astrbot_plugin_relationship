<div align="center">

# astrbot_plugin_relationship

_✨ 人际关系管理器 ✨_

[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

</div>

> 本仓库由 [leekooyo](https://github.com/leekooyo) 维护，基于 [Zhalslar 的原项目](https://github.com/Zhalslar/astrbot_plugin_relationship)；安装和更新请使用本仓库地址。原始基线见 [UPSTREAM.md](UPSTREAM.md)。

**当前版本：v3.1.3。** 版本号以 [metadata.yaml](metadata.yaml) 为准。

> **好友列表** 与 **群列表** 一次展示全部内容；长列表使用 AstrBot 默认图片模板输出一张长图。

> 此维护版的发送隔离依赖本机 AstrBot 核心提供 `astrbot.core.utils.message_send_policy`。安装到未接入该模块的 AstrBot 核心会导致插件导入失败；更新核心前请先核对此依赖。

## 简介

为 AstrBot 提供的关系管理插件，支持好友/群列表查看、好友与群邀请审核、自动处理规则、踢出与禁言通知、黑名单维护，以及聊天记录抽查等能力，方便集中管理 bot 的人际关系与群管理风险。

## 功能一览

- 好友列表与群列表查询（完整列表；长内容转为单张图片）。
- 批量退群、批量删好友（支持序号、ID、区间、@）。
- 好友申请与群邀请：自动审核规则（黑名单/自动同意/自动拒绝）与手动审核（引用申请消息后用 `同意/拒绝`）。
- 群事件通知处理：机器人实际入群、主动退群、被踢。机器人禁言/解禁由 gatekeeper 通知；普通成员事件不会推送。
- 风险控制：小群/超大群自动退群、超过最大群容量自动退群、被踢出后自动拉黑群/用户、互斥成员（`mutual_blacklist`）检测。
- 聊天记录抽查与新群自动抽查（可延迟）。

## 安装

- 在 AstrBot 中选择「通过仓库地址安装」，填写 `https://github.com/leekooyo/astrbot_plugin_relationship`。
- 或手动克隆到插件目录：

```bash
cd /AstrBot/data/plugins
git clone https://github.com/leekooyo/astrbot_plugin_relationship
```

本仓库基于 [Zhalslar 原项目](https://github.com/Zhalslar/astrbot_plugin_relationship) 独立维护，原始基线与维护差异见 [UPSTREAM.md](UPSTREAM.md)。审批员、黑名单、群号及聊天记录属于本机运行数据，不要提交到仓库。

## 配置

在 AstrBot 面板中配置：`插件管理 -> astrbot_plugin_relationship -> 操作 -> 插件配置`。

`notify_target` 默认 `admin_private`：群事件逐人私聊机器人管理员，申请消息发送给已配置的审批员（包括管理员）；选 `review_group` 时发送到 `manage_group`，未填审核群则回退私聊。群邀请申请、接口处理结果与实际入群分别通知，不能把审批成功当作已入群。`notify_bot_ban` 默认关闭，避免与 gatekeeper 的禁言通知重复。

## 指令

| 指令                                             | 说明                     | 权限             |
| :----------------------------------------------- | :----------------------- | :--------------- |
| `群列表`                                       | 查看 bot 加入的所有群    | 管理员           |
| `好友列表`                                     | 查看 bot 的所有好友      | 管理员           |
| `退群 <序号/群号/区间>`                        | 退群，支持批量与区间     | 管理员           |
| `删好友 <@QQ/序号/区间>`                       | 删除好友，支持批量与区间 | 管理员           |
| `加审批员 @QQ`（别名：加审核员）                               | 添加审核员               | 管理员 |
| `减审批员 @QQ`（别名：减审核员）                               | 移除审核员               | 管理员 |
| `同意 [备注]`                                  | 同意好友/群邀请          | 仅审核员         |
| `拉黑 [理由]` | 拒绝并拉黑申请人/邀请群 | 仅审核员 |
| `拒绝 [理由]`                                  | 拒绝好友/群邀请          | 仅审核员         |
| `抽查 [群号/@群友/QQ] [数量]`                  | 抽查聊天记录             | 管理员           |
| `推荐 [群号/@群友/@QQ]`                        | 发送该群/用户的推荐卡片  | 管理员           |

### LLM Tools（大模型工具调用）

启用 LLM 工具调用后，大模型可根据语境调用以下公开功能；涉及退群、删好友等操作时请先确认权限和目标：
- `llm_get_group_list`: 查看机器人加入的所有群聊列表。
- `llm_get_friend_list`: 查看机器人的所有好友列表。
- `llm_leave_group`: 退出指定的群聊。
- `llm_delete_friend`: 删除指定的好友。
- `llm_send_contact_card`: 主动发送好友或群聊的推荐名片。
- `llm_check_messages`: 抽查指定群聊或用户的历史聊天记录并合并转发到当前会话。

使用说明：

- `同意/拒绝` 必须**引用申请消息**使用。
- `退群/删好友` 支持空格分隔、区间（`1-5` / `1~5`）与批量输入。
- `抽查` 若未指定目标，会随机抽查一个群。

### 未提供的扩展功能

本仓库的 `core/expansion.py` 只是占位文件，没有实现扩展处理器。因此 `加好友`、`加群` 命令和对应的 `llm_add_friend_request`、`llm_add_group_request` 工具虽保留调用入口，在此公开版本中均不可用，会提示扩展模块未加载；开发者权限也不能使其生效。

## 机制说明

**申请/邀请事件**：先走自动规则（黑名单/自动同意/自动拒绝）。自动处理由 QQ 接口确认后通知结果；待人工审批的申请通知管理员或审核群，引用申请通知后用 `同意/拒绝`。接口处理失败会明确报错，不发送成功文案。

**群事件通知**：仅在机器人实际入群、主动退群或被踢时发送通知；普通成员入群、退群或被踢不会推送。机器人被踢后拉黑的是事件中的操作者；操作者无法确认时不拉黑用户。机器人禁言与解禁由 gatekeeper 负责轮询和通知。AstrBot 必须允许机器人自身 notice 进入插件，同时仍可忽略机器人自己发送的普通消息。

**新群自动抽查**：机器人实际入群且通过自动退群规则后，按配置延迟转发该群近期消息到审核群或管理员。

## 反馈与维护

此维护版的问题和改进请在本仓库提交 Issue 或 Pull Request。上游版本会在核对差异后手动合并。

## 注意事项

- 如果未配置 `manage_group` 且无管理员 ID，将无法发送审核与通知消息。
