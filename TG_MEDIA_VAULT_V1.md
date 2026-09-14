# TG Media Vault V1

Windows-first Telegram media archive MVP built on top of `telegram_media_downloader`.

> 适用范围：用于归档你本人有权访问和保存的 Telegram 频道、群组或会话媒体。TG Media Vault 不用于绕过 Telegram 的内容保护、受限保存或其他访问控制。

## 现在这版能做什么

- 首次登录 Telegram：手机号 + 验证码 + 可选两步验证密码
- 登录成功后保存本机 Session，后续启动可直接复用
- 自动读取当前 Telegram 账号可访问的频道 / 群组，不需要手填 Chat ID
- 媒体分类：图片、视频、GIF / 动图、文件
- 时间范围：全部、最近 7 天、30 天、90 天
- 自定义本地保存目录
- SQLite 下载历史与去重
- 中断恢复：下载先写入 `.part` 临时文件，完整后再落到正式文件名
- 并发下载与失败重试
- Windows 单文件 EXE 构建流程

## 1. 获取 Telegram API ID / API Hash

Telegram 客户端登录需要你自己的 API ID 和 API Hash。

1. 打开 `https://my.telegram.org/apps`
2. 使用你的 Telegram 手机号登录
3. 创建一个 Telegram Application
4. 记录页面显示的：
   - `api_id`
   - `api_hash`

这两个值只用于建立你自己的 Telegram 客户端 Session。不要把它们提交到公开仓库。

## 2. Windows 直接运行 EXE

如果使用 GitHub Actions 构建出的版本：

1. 在对应的 GitHub Actions `TG Media Vault Windows Build` 运行中下载 artifact：`TGMediaVault-Windows`
2. 解压 ZIP
3. 运行 `TGMediaVault.exe`
4. 程序会启动本地 TG Media Vault 页面

V1 当前为本机应用模式，数据默认保存在当前 Windows 用户目录中。

## 3. 第一次连接 Telegram

在 `1. 连接 Telegram` 区域：

1. 填入 `API ID`
2. 填入 `API Hash`
3. 输入 Telegram 手机号（包含国家区号，例如 `+65...`）
4. 点击 `连接 / 获取验证码`
5. Telegram 会向你的 Telegram 客户端发送登录验证码
6. 填入验证码
7. 如果账号开启了 Telegram 两步验证，再填入两步验证密码
8. 点击 `完成登录`

登录成功后，页面状态会显示 `已连接`，并自动读取可访问的频道和群组。

Session 默认保存在：

```text
%USERPROFILE%\.tg-media-vault\sessions\
```

设置默认保存在：

```text
%USERPROFILE%\.tg-media-vault\settings.yaml
```

归档数据库默认保存在：

```text
%USERPROFILE%\.tg-media-vault\vault.sqlite3
```

## 4. 选择频道并扫描

在 `2. 选择频道并扫描` 区域：

1. 从下拉列表选择频道 / 群组
2. 选择需要的媒体类型：
   - 图片
   - 视频
   - GIF / 动图
   - 文件
3. 选择时间范围
4. 设置保存位置
5. 设置并发下载数量；默认值建议先保持不变
6. 点击 `扫描媒体`

扫描阶段只读取媒体元数据，不会立即下载。

扫描完成后会显示：

- 图片数量
- 视频数量
- GIF 数量
- 文件数量
- 已归档数量
- 本轮待归档数量

## 5. 开始归档

扫描完成后，在 `3. 开始归档` 点击 `开始下载`。

默认目录结构类似：

```text
TG Media Vault\
  频道名称 [ChatID]\
    photo\
    video\
    gif\
    file\
```

文件名会包含 Telegram Message ID，避免同名覆盖。

下载过程中：

- 当前文件先写入 `.part`
- 下载完整后再原子替换成正式文件
- 如果程序中途退出，不会把半截文件误判为已完成
- SQLite 会记录已成功归档的消息
- 再次扫描时会跳过仍然存在的已归档文件
- 如果你手动删除了本地文件，对应失效记录会在后续扫描中被清理，从而允许重新归档

## 6. Windows 源码模式

如果不使用 EXE，也可以在 Windows 直接运行源码版。

第一次：

```bat
setup_vault_windows.bat
```

以后启动：

```bat
run_vault_windows.bat
```

源码 UI 需要 Python 3.10 或更高版本。

## 7. 当前 V1 边界

V1 重点是把核心链路跑稳：

`登录 → 自动读取频道 → 扫描 → 去重 → 下载 → 归档`

暂未作为 V1 硬目标的功能包括：

- 自动后台持续监听新媒体
- NAS / 云盘同步
- AI 自动分类、标签与搜索
- 多账号切换
- 原生 Windows 文件夹选择器
- 完整桌面壳 / 安装程序

这些更适合作为 V1.1 / V2 继续迭代。

## 8. 首次 Smoke Test 建议

第一次不要直接拿大型频道全量归档。

建议：

1. 选择一个你自己有权保存内容的小频道 / 群组
2. 时间范围选择 `最近 7 天`
3. 先只勾选 `图片`
4. 扫描确认数量正常
5. 下载 5–20 个媒体文件
6. 检查本地文件是否可正常打开
7. 再次扫描，确认这些文件被识别为已归档
8. 关闭应用并重新打开，确认 Telegram Session 可复用
9. 再逐步测试视频、GIF、大文件和更长时间范围

如果这 9 项全部通过，V1 就具备进入更大频道测试的基础。
