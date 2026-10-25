---
id: wsl-external-drive-mount
title: "WSL 不热挂载新增盘符，外接 USB 盘需启动前接入或手动 mount"
category: decision
status: active
tags: [wsl, mount, environment]
created: "2026-10-25T21:53:05"
updated: "2026-10-25T21:53:05"
---

<!-- compiled_truth -->
运行环境为 WSL 2（内核 6.18.54.1），Windows 盘符只在发行版启动时枚举并挂载为 9p。发行版启动后接入的 USB 硬盘不会自动出现在 /mnt/<盘符>，该路径会继续显示 ext4 根分区上的同名普通目录内容，而不是硬盘内容。

`/etc/wsl.conf` 仅设置 systemd，`.wslconfig` 未覆盖 automount，因此排除配置禁用；`/mnt/f` 实测 dev 与 `/` 相同（ext4），C/D/E 为 9p 挂载。

照片统计脚本优先使用 E:（内置 NVMe）不受影响；要用外接 F: 时，需先接入硬盘再 `wsl --shutdown` 重启，或执行 `sudo mount -t drvfs F: /mnt/f`。

注意：`/mnt/f` 曾被当作普通目录使用并存放了 `id_rsa`/`id_rsa.pub`，挂载后会遮蔽这些文件，SSH 私钥不应放在可被盘符挂载覆盖的路径。


## Timeline

- time: 2026-10-25T21:53:05
  kind: decision
  summary: "Created this page: WSL 不热挂载新增盘符，外接 USB 盘需启动前接入或手动 mount"
  source: "2026-10-25 排查 /mnt/f 显示错误数据"
  affects: [wsl-external-drive-mount]

- time: 2026-10-25T21:53:05
  kind: decision
  summary: "确认外接盘在 WSL 启动后接入导致未挂载，记录处置方式与密钥风险"
  source: "findmnt、stat、PowerShell 磁盘接入时间对比"
  affects: [wsl-external-drive-mount]
