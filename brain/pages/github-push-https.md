---
id: github-push-https
title: "GitHub 推送使用 HTTPS，SSH 443 会挂起"
category: decision
status: active
tags: [git, github, environment]
created: "2026-10-25T22:14:04"
updated: "2026-10-25T22:14:04"
---

<!-- compiled_truth -->
本机通过 `~/.ssh/config` 把 github.com 指向 `ssh.github.com:443`。SSH 认证可以成功，但 `git-receive-pack` 发出后无响应，`git push` 会一直挂起直到超时；HTTPS 的 `git ls-remote` 和 `git push` 均正常。

因此推送 GitHub 时使用 HTTPS remote，并依赖 `gh auth setup-git` 提供的凭据助手。不要在挂起时反复重试 SSH，先确认是否卡在 `git-receive-pack`。

本次仓库：https://github.com/wlonestar/exposure-plot （public，默认分支 main）。


## Timeline

- time: 2026-10-25T22:14:04
  kind: decision
  summary: "Created this page: GitHub 推送使用 HTTPS，SSH 443 会挂起"
  source: "2026-10-25 首次推送 exposure-plot"
  affects: [github-push-https]

- time: 2026-10-25T22:14:04
  kind: decision
  summary: "记录 SSH 443 推送挂起、改用 HTTPS 的事实与处置"
  source: "git push 超时与 gh api 验证"
  affects: [github-push-https]
