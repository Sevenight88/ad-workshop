# 装甲黎明工坊 · 作品仓库

这个仓库是 AD Workshop（游戏内 `Ctrl+W`）的后端。玩家在游戏里点「上传」，文件就进到这里；
其他人打开工坊就能看到、下载、载入。

仓库里唯一「生成出来的」文件是 `items/index.json`——由 GitHub Actions 自动重算，
**不要手改**，改了下次推送会被覆盖。

## 一次部署（做完就不用再管）

1. 新建一个**公开**仓库，把本目录（`repo-template`）里的全部内容放进去，推到 `main`。
2. 打开仓库的 **Settings → Actions → General → Workflow permissions**，
   选 **Read and write permissions**，保存。
   不做这一步，工作流改不了 `items/index.json`，索引永远不更新。
3. 去 **Settings → Actions** 确认工作流是启用状态。
4. 在游戏里按 `Ctrl+W` →「设置」，填三样：

   | 项 | 填什么 |
   | --- | --- |
   | 仓库 | `Sevenight88/ad-workshop` |
   | 令牌 | 仓库主人自己用：**classic PAT，只勾 `public_repo`**。（fine-grained 也行，但只限主人自己；被邀请来投稿的协作者必须用 classic——GitHub 把「协作者用 fine-grained 写入」列为已知缺口，那条路必然失败。） |
   | API 地址 / 下载地址 | 默认留空即直连 GitHub；大陆连不通时，填自己部署的 Cloudflare Worker 转发地址（部署脚本在 mod 源码的 `worker/` 目录） |

   点「保存」，再点「刷新索引」。
5. 传第一件作品：`Ctrl+U` → 左边选文件 → 右边填名字／年代／标签 → 「上传到工坊」。
   工作流大约十秒后跑完，刷新一下列表就能看到它。

## 目录长什么样

```
items/
  index.json                       ← 自动生成，客户端只读这一个
  vehicle/3f9a1c2b8d4e5f60718293a4b5c6d7e8/
    meta.json                      ← 元数据
    item.blueprint                 ← 蓝图原文（一个字都不改）
    preview.png                    ← 可选，360×135
```

`<id>` 是内容哈希的前 32 位：剔除 `header.name` 与 `header.creationDate` 之后，
把整棵 JSON 序列化再取 sha256。这意味着——

* 同一辆车**换个名字再传**，id 不变，只会覆盖 `meta.json`（名字、标签、说明、预览图）。
* 改了任何几何，id 就变了，仓库里多一件。旧的那件留着，别人已经下载的不受影响。
* 所以这个仓库天然「只增不改」，不需要谁去审核。

## 校验规则

工作流逐件检查，**坏的那件跳过**而不是让整次构建失败——一件坏文件不该让所有人的列表停更。
跳过的东西会开一个 Issue 说清楚是哪件、为什么。

被拒的常见原因：

| 现象 | 原因 |
| --- | --- |
| `type 写的是 X，却放在 Y/ 下` | 目录与 meta 对不上（手工挪过目录） |
| `id 是 X，目录却叫 Y` | 同上 |
| `sha256 不是 64 位十六进制` | meta 被手改过 |
| `缺 item.blueprint` | 只推了 meta.json |

想手工加一件作品？照着现有目录抄一份，把 `id`、`sha256` 换成真实值就行——
`sha256` 必须和客户端算的一致，否则下载时会校验失败。最省事的办法还是用游戏上传。

## 关于许可

`meta.json` 里的 `license` 是上传者选的。仓库本身不主张任何权利，
作品的权利归各自的作者。想撤下自己的作品，删掉对应目录再推一次即可。
