# 038 线上部署问答与前端缓存修复

## 背景

服务器已完成知识库向量化，但线上问答出现“回复失败”，管理后台和聊天页还显示旧版页面。

## 问题定位

1. DeepSeek 兼容接口可达，但线上开启 `CHAT_THINKING=adaptive` 后，当前模型通道持续返回思考字段，应用流式链路无法及时得到正文。
2. FastAPI 的页面和静态资源没有明确的禁缓存响应头，浏览器可能继续使用旧 HTML、CSS 或 JavaScript。
3. 线上知识库本身已完成 19 块入库，评测数据接口已返回 300 条数据，数据未更新与页面缓存/展示认知混在一起。

## 方案

- 线上 `.env` 将 `CHAT_THINKING` 调整为 `disabled`，`CHAT_REASONING_SPLIT` 调整为 `false`。
- 为前端页面和 `/static/*` 增加 `Cache-Control: no-store`，部署后刷新即可获取当前版本。
- 将 `.env.example` 的默认配置同步为稳定的 DeepSeek 兼容配置，避免后续复制配置再次触发相同问题。

## 验收

- `/api/chat` 能返回 `delta`、`done` 和 `[DONE]` 事件。
- 知识库问题能够返回 citations 和基于知识库的答案。
- `/api/admin/overview` 返回 19 个知识块、0 个待向量化块、300 条评测集。
- 页面和静态资源响应 `Cache-Control: no-store`。
