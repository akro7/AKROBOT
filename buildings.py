#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════╗
# ║   PBRP Recovery Builder Bot — by AKRO                   ║
# ║   Telegram Bot | GitHub Actions Integration              ║
# ╚══════════════════════════════════════════════════════════╝

import os, time, asyncio, threading, requests, json, re
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    BotCommand
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters, ConversationHandler
)
from telegram.constants import ParseMode

# ─── BOT CONFIG ────────────────────────────────────────────
BOT_TOKEN = "8556742793:AAGfe7Mq0Vdt85tOCqbVemHTBLGHWDQwdik"

# ─── CONVERSATION STATES ───────────────────────────────────
(
    ASK_GH_TOKEN, ASK_REPO, ASK_BRANCH, ASK_DEVICE_TREE,
    ASK_TREE_BRANCH, ASK_BUILD_TARGET, CONFIRM_BUILD
) = range(7)

# ─── PERSISTENT STORAGE (per user) ─────────────────────────
user_config   = {}   # {user_id: {gh_token, repo, ...}}
active_builds = {}   # {user_id: {run_id, start_time, msg_id, chat_id, ...}}

# ─── GITHUB API ────────────────────────────────────────────
GH_API = "https://api.github.com"

def gh_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

def trigger_workflow(token, repo, workflow_file, inputs: dict):
    url = f"{GH_API}/repos/{repo}/actions/workflows/{workflow_file}/dispatches"
    r = requests.post(url, headers=gh_headers(token),
                      json={"ref": "android-12.1", "inputs": inputs}, timeout=15)
    return r.status_code in (204, 201, 200)

def get_latest_run(token, repo, workflow_file):
    url = f"{GH_API}/repos/{repo}/actions/workflows/{workflow_file}/runs"
    r = requests.get(url, headers=gh_headers(token),
                     params={"per_page": 1, "event": "workflow_dispatch"},
                     timeout=15)
    if r.status_code == 200:
        runs = r.json().get("workflow_runs", [])
        return runs[0] if runs else None
    return None

def get_run_status(token, repo, run_id):
    url = f"{GH_API}/repos/{repo}/actions/runs/{run_id}"
    r = requests.get(url, headers=gh_headers(token), timeout=15)
    if r.status_code == 200:
        return r.json()
    return None

def get_run_jobs(token, repo, run_id):
    url = f"{GH_API}/repos/{repo}/actions/runs/{run_id}/jobs"
    r = requests.get(url, headers=gh_headers(token), timeout=15)
    if r.status_code == 200:
        return r.json().get("jobs", [])
    return []

def get_release_assets(token, repo, tag):
    url = f"{GH_API}/repos/{repo}/releases/tags/{tag}"
    r = requests.get(url, headers=gh_headers(token), timeout=15)
    if r.status_code == 200:
        return r.json()
    return None

def get_latest_release(token, repo):
    url = f"{GH_API}/repos/{repo}/releases/latest"
    r = requests.get(url, headers=gh_headers(token), timeout=15)
    if r.status_code == 200:
        return r.json()
    return None

# ─── HELPERS ───────────────────────────────────────────────
def fmt_duration(seconds):
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s   = divmod(rem, 60)
    if h:
        return f"{h}h {m}m {s}s"
    elif m:
        return f"{m}m {s}s"
    return f"{s}s"

def status_emoji(status, conclusion):
    if status == "completed":
        return "✅" if conclusion == "success" else "❌" if conclusion == "failure" else "⚠️"
    if status == "in_progress":
        return "🔨"
    return "⏳"

def build_status_text(cfg, run, elapsed, jobs=None):
    status     = run.get("status", "unknown")
    conclusion = run.get("conclusion")
    run_id     = run.get("id")
    run_url    = run.get("html_url", "")
    repo       = cfg.get("repo", "")

    s_emoji = status_emoji(status, conclusion)

    # current step
    step_line = ""
    if jobs:
        for job in jobs:
            if job.get("status") == "in_progress":
                for step in job.get("steps", []):
                    if step.get("status") == "in_progress":
                        step_line = f"\n⚙️ *Step:* `{step['name']}`"
                        break
                break

    progress_bar = ""
    if status == "in_progress":
        bars = min(int(elapsed / 60), 20)
        progress_bar = "\n`[" + "█" * bars + "░" * (20 - bars) + "]`"

    text = (
        f"╔══ 🏗️ *PBRP Build Monitor* ══╗\n"
        f"┃\n"
        f"┃  {s_emoji} *Status:* `{status}`"
        + (f" → `{conclusion}`" if conclusion else "")
        + f"\n┃  ⏱️ *Elapsed:* `{fmt_duration(elapsed)}`"
        + f"\n┃  🔗 *Repo:* `{repo}`"
        + f"\n┃  🆔 *Run:* `{run_id}`"
        + step_line
        + progress_bar
        + f"\n┃\n╚═══════════════════════════╝\n"
        f"\n[🔍 View on GitHub]({run_url})"
    )
    return text

# ─── COMMANDS ──────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.effective_user.first_name

    text = (
        f"```\n"
        f"╔═══════════════════════════════╗\n"
        f"║   🖤 A34 🏂 Builder Bot - AKRO  ║\n"
        f"║   ALL Recovery Project  ║\n"
        f"╚═══════════════════════════════╝\n"
        f"```\n"
        f"👋 مرحباً *{name}*!\n\n"
        f"أنا بوت بناء ريكفري *PBRP* الاحترافي.\n"
        f"أبني ريكفري معدّل وأرسله ليك فور اكتماله! 🚀\n\n"
        f"*الأوامر المتاحة:*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔧 /setup — إعداد GitHub Token والريبو\n"
        f"🏗️ /build — بدء بناء ريكفري جديد\n"
        f"📊 /status — حالة البناء الحالية\n"
        f"⛔ /cancel — إلغاء البناء الجاري\n"
        f"📦 /release — آخر ريكفري جاهز\n"
        f"ℹ️ /config — عرض الإعدادات الحالية\n"
        f"🗑️ /reset — مسح الإعدادات\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🚦 *ابدأ بـ /setup لإعداد GitHub*"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ──────────────────────────────────────────────────────────
# SETUP CONVERSATION
# ──────────────────────────────────────────────────────────

async def cmd_setup(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔑 *إعداد GitHub Token*\n\n"
        "أرسل GitHub Personal Access Token\n"
        "_(يحتاج صلاحية: `repo` + `actions`_)\n\n"
        "للحصول على token:\n"
        "GitHub → Settings → Developer settings\n"
        "→ Personal access tokens → Generate new token",
        parse_mode=ParseMode.MARKDOWN
    )
    return ASK_GH_TOKEN

async def recv_gh_token(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    token = update.message.text.strip()

    # Validate token
    r = requests.get(f"{GH_API}/user", headers=gh_headers(token), timeout=10)
    if r.status_code != 200:
        await update.message.reply_text(
            "❌ *Token غير صالح!*\nتأكد من صحة الـ token وأنه يملك صلاحيات `repo` و `actions`.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ASK_GH_TOKEN

    gh_user = r.json().get("login", "Unknown")
    user_config.setdefault(uid, {})["gh_token"] = token
    user_config[uid]["gh_user"] = gh_user

    # Delete the token message for security
    try:
        await update.message.delete()
    except:
        pass

    await update.message.reply_text(
        f"✅ *Token صالح!* مرحباً `{gh_user}` 👤\n\n"
        f"🏗️ أرسل اسم الريبو بالصيغة:\n`owner/repository-name`\n\n"
        f"مثال: `akro7/pbrp-builder`",
        parse_mode=ParseMode.MARKDOWN
    )
    return ASK_REPO

async def recv_repo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    repo = update.message.text.strip()

    if not re.match(r'^[\w.-]+/[\w.-]+$', repo):
        await update.message.reply_text("❌ صيغة غير صحيحة. مثال: `akro7/pbrp-builder`",
                                         parse_mode=ParseMode.MARKDOWN)
        return ASK_REPO

    token = user_config[uid]["gh_token"]
    r = requests.get(f"{GH_API}/repos/{repo}", headers=gh_headers(token), timeout=10)
    if r.status_code != 200:
        await update.message.reply_text(
            "❌ *الريبو غير موجود أو لا يملك صلاحية وصول.*\nتحقق من الاسم.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ASK_REPO

    user_config[uid]["repo"] = repo
    repo_data = r.json()

    # Check for workflow files
    wf_url = f"{GH_API}/repos/{repo}/actions/workflows"
    wf_r = requests.get(wf_url, headers=gh_headers(token), timeout=10)
    workflows = []
    if wf_r.status_code == 200:
        workflows = wf_r.json().get("workflows", [])

    if workflows:
        kb = []
        for wf in workflows[:8]:
            kb.append([InlineKeyboardButton(
                f"📋 {wf['name']}",
                callback_data=f"setwf:{wf['path'].split('/')[-1]}"
            )])
        await update.message.reply_text(
            f"✅ ريبو موجود: `{repo}`\n\n🗂️ اختر ملف الـ Workflow:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(kb)
        )
    else:
        user_config[uid]["workflow"] = "build.yml"
        await update.message.reply_text(
            f"✅ الإعداد اكتمل!\n\n"
            f"🏗️ الريبو: `{repo}`\n"
            f"📋 Workflow: `build.yml`\n\n"
            f"الآن يمكنك استخدام /build لبدء البناء! 🚀",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END

    return ASK_REPO  # wait for callback

async def callback_set_workflow(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    wf = query.data.split(":", 1)[1]
    user_config.setdefault(uid, {})["workflow"] = wf
    repo = user_config[uid].get("repo", "?")

    await query.edit_message_text(
        f"✅ *الإعداد اكتمل!*\n\n"
        f"👤 GitHub: `{user_config[uid].get('gh_user', '?')}`\n"
        f"🏗️ الريبو: `{repo}`\n"
        f"📋 Workflow: `{wf}`\n\n"
        f"الآن يمكنك استخدام /build لبدء البناء! 🚀",
        parse_mode=ParseMode.MARKDOWN
    )

async def cmd_cancel_conv(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ تم الإلغاء.")
    return ConversationHandler.END

# ──────────────────────────────────────────────────────────
# BUILD COMMAND
# ──────────────────────────────────────────────────────────

BUILD_DEFAULTS = {
    "manifest_branch": "android-12.1",
    "device_tree": "https://github.com/akro7/twrp-a34x",
    "device_tree_branch": "android-12.1",
    "build_target": "pbrp"
}

async def cmd_build(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if uid not in user_config or "gh_token" not in user_config[uid]:
        await update.message.reply_text(
            "⚠️ لم يتم الإعداد بعد!\nاستخدم /setup أولاً.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    cfg = user_config[uid]
    cfg.setdefault("build", BUILD_DEFAULTS.copy())
    b = cfg["build"]

    kb = [
        [InlineKeyboardButton("📱 MANIFEST BRANCH", callback_data="bld:none")],
        [
            InlineKeyboardButton("🔵 12.1" + (" ✓" if b["manifest_branch"] == "android-12.1" else ""),
                                 callback_data="bld:mb:android-12.1"),
            InlineKeyboardButton("🟡 11.0" + (" ✓" if b["manifest_branch"] == "android-11.0" else ""),
                                 callback_data="bld:mb:android-11.0"),
            InlineKeyboardButton("🟠 10.0" + (" ✓" if b["manifest_branch"] == "android-10.0" else ""),
                                 callback_data="bld:mb:android-10.0"),
        ],
        [InlineKeyboardButton("🎯 BUILD TARGET", callback_data="bld:none")],
        [
            InlineKeyboardButton("🖤 PBRP" + (" ✓" if b["build_target"] == "pbrp" else ""),
                                 callback_data="bld:bt:pbrp"),
            InlineKeyboardButton("📀 recoveryimage" + (" ✓" if b["build_target"] == "recoveryimage" else ""),
                                 callback_data="bld:bt:recoveryimage"),
        ],
        [InlineKeyboardButton("🌳 Device Tree", callback_data="bld:set_tree")],
        [InlineKeyboardButton(
            f"🔗 {b['device_tree'][:40]}...",
            callback_data="bld:none"
        )],
        [InlineKeyboardButton("━━━━━━━━━━━━━━━━━━━━", callback_data="bld:none")],
        [InlineKeyboardButton("🚀 ابدأ البناء الآن!", callback_data="bld:start")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="bld:cancel")],
    ]

    text = (
        f"🏗️ *إعداد بناء PBRP Recovery*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 Manifest: `{b['manifest_branch']}`\n"
        f"🎯 Target:   `{b['build_target']}`\n"
        f"🌳 Tree:     `{b['device_tree']}`\n"
        f"🌿 Branch:   `{b['device_tree_branch']}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"اختر خياراتك ثم ابدأ البناء ⬇️"
    )

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(kb))

async def callback_build(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data  # "bld:..."

    cfg = user_config.setdefault(uid, {})
    cfg.setdefault("build", BUILD_DEFAULTS.copy())
    b = cfg["build"]

    parts = data.split(":", 2)
    action = parts[1] if len(parts) > 1 else ""

    if action == "none":
        return
    elif action == "cancel":
        await query.edit_message_text("❌ تم الإلغاء.")
        return
    elif action == "mb":
        b["manifest_branch"] = parts[2]
    elif action == "bt":
        b["build_target"] = parts[2]
    elif action == "set_tree":
        await query.edit_message_text(
            "🌳 أرسل رابط Device Tree:\n"
            "مثال: `https://github.com/akro7/twrp-a34x`",
            parse_mode=ParseMode.MARKDOWN
        )
        ctx.user_data["awaiting"] = "device_tree"
        return
    elif action == "start":
        await start_build(query, ctx, uid)
        return

    # Refresh keyboard
    kb = build_keyboard(b)
    text = (
        f"🏗️ *إعداد بناء PBRP Recovery*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 Manifest: `{b['manifest_branch']}`\n"
        f"🎯 Target:   `{b['build_target']}`\n"
        f"🌳 Tree:     `{b['device_tree']}`\n"
        f"🌿 Branch:   `{b['device_tree_branch']}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"اختر خياراتك ثم ابدأ البناء ⬇️"
    )
    try:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                       reply_markup=InlineKeyboardMarkup(kb))
    except:
        pass

def build_keyboard(b):
    return [
        [InlineKeyboardButton("📱 MANIFEST BRANCH", callback_data="bld:none")],
        [
            InlineKeyboardButton("🔵 12.1" + (" ✓" if b["manifest_branch"] == "android-12.1" else ""),
                                 callback_data="bld:mb:android-12.1"),
            InlineKeyboardButton("🟡 11.0" + (" ✓" if b["manifest_branch"] == "android-11.0" else ""),
                                 callback_data="bld:mb:android-11.0"),
            InlineKeyboardButton("🟠 10.0" + (" ✓" if b["manifest_branch"] == "android-10.0" else ""),
                                 callback_data="bld:mb:android-10.0"),
        ],
        [InlineKeyboardButton("🎯 BUILD TARGET", callback_data="bld:none")],
        [
            InlineKeyboardButton("🖤 PBRP" + (" ✓" if b["build_target"] == "pbrp" else ""),
                                 callback_data="bld:bt:pbrp"),
            InlineKeyboardButton("📀 recoveryimage" + (" ✓" if b["build_target"] == "recoveryimage" else ""),
                                 callback_data="bld:bt:recoveryimage"),
        ],
        [InlineKeyboardButton("🌳 تغيير Device Tree", callback_data="bld:set_tree")],
        [InlineKeyboardButton("━━━━━━━━━━━━━━━━━━━━", callback_data="bld:none")],
        [InlineKeyboardButton("🚀 ابدأ البناء الآن!", callback_data="bld:start")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="bld:cancel")],
    ]

async def start_build(query, ctx, uid):
    cfg = user_config[uid]
    b   = cfg["build"]

    token    = cfg["gh_token"]
    repo     = cfg["repo"]
    workflow = cfg.get("workflow", "build.yml")

    wf_inputs = {
        "MANIFEST_BRANCH":    b["manifest_branch"],
        "DEVICE_TREE":        b["device_tree"],
        "DEVICE_TREE_BRANCH": b["device_tree_branch"],
        "BUILD_TARGET":       b["build_target"]
    }

    await query.edit_message_text(
        "⏳ *جاري تشغيل GitHub Actions...*",
        parse_mode=ParseMode.MARKDOWN
    )

    ok = trigger_workflow(token, repo, workflow, wf_inputs)
    if not ok:
        await query.edit_message_text(
            "❌ *فشل تشغيل الـ Workflow!*\n\n"
            "تحقق من:\n"
            "• صلاحيات الـ token (`actions:write`)\n"
            "• اسم ملف الـ workflow\n"
            "• وجود branch `main` في الريبو",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Wait for run to appear
    await asyncio.sleep(4)
    run = None
    for _ in range(10):
        run = get_latest_run(token, repo, workflow)
        if run:
            break
        await asyncio.sleep(3)

    if not run:
        await query.edit_message_text(
            "❌ لم يتم العثور على الـ run. تحقق من GitHub Actions يدوياً.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    run_id    = run["id"]
    start_ts  = time.time()
    chat_id   = query.message.chat_id

    # Store active build
    active_builds[uid] = {
        "run_id":    run_id,
        "start_ts":  start_ts,
        "chat_id":   chat_id,
        "msg_id":    query.message.message_id,
        "token":     token,
        "repo":      repo,
        "workflow":  workflow,
        "cfg":       cfg.copy(),
    }

    msg = await query.edit_message_text(
        build_status_text(cfg, run, 0),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔍 GitHub", url=run.get("html_url", "")),
            InlineKeyboardButton("🔄 تحديث", callback_data=f"refresh:{uid}")
        ]])
    )
    active_builds[uid]["msg_id"] = msg.message_id

    # Start background monitor
    threading.Thread(target=monitor_build, args=(ctx.application, uid), daemon=True).start()

# ─── BACKGROUND BUILD MONITOR ──────────────────────────────

def monitor_build(app, uid):
    import asyncio as _aio

    loop = _aio.new_event_loop()
    _aio.set_event_loop(loop)

    async def _monitor():
        info      = active_builds.get(uid)
        if not info:
            return

        token     = info["token"]
        repo      = info["repo"]
        run_id    = info["run_id"]
        chat_id   = info["chat_id"]
        msg_id    = info["msg_id"]
        cfg       = info["cfg"]
        start_ts  = info["start_ts"]
        last_text = ""
        interval  = 20  # seconds between updates

        while True:
            await _aio.sleep(interval)

            run = get_run_status(token, repo, run_id)
            if not run:
                continue

            elapsed = time.time() - start_ts
            jobs    = get_run_jobs(token, repo, run_id)
            text    = build_status_text(cfg, run, elapsed, jobs)

            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔍 GitHub", url=run.get("html_url", "")),
                InlineKeyboardButton("🔄 تحديث", callback_data=f"refresh:{uid}")
            ]])

            if text != last_text:
                try:
                    await app.bot.edit_message_text(
                        chat_id=chat_id, message_id=msg_id,
                        text=text, parse_mode=ParseMode.MARKDOWN,
                        reply_markup=kb
                    )
                    last_text = text
                except Exception as e:
                    pass

            if run.get("status") == "completed":
                await build_finished(app, uid, run, elapsed)
                break

            # Adaptive interval: faster at start, slower mid-build
            if elapsed < 300:
                interval = 20
            elif elapsed < 1800:
                interval = 30
            else:
                interval = 60

    loop.run_until_complete(_monitor())
    loop.close()

async def build_finished(app, uid, run, elapsed):
    info    = active_builds.get(uid, {})
    chat_id = info.get("chat_id")
    msg_id  = info.get("msg_id")
    token   = info.get("token", "")
    repo    = info.get("repo", "")
    cfg     = info.get("cfg", {})

    conclusion = run.get("conclusion", "unknown")
    run_url    = run.get("html_url", "")

    if conclusion == "success":
        # Try to get release assets
        release = get_latest_release(token, repo)
        assets_text = ""
        dl_buttons = []

        if release:
            assets = release.get("assets", [])
            for asset in assets:
                name = asset["name"]
                url  = asset["browser_download_url"]
                size = asset["size"] // (1024 * 1024)
                assets_text += f"\n📦 `{name}` — *{size} MB*"
                if len(dl_buttons) < 3:
                    dl_buttons.append([InlineKeyboardButton(
                        f"⬇️ {name[:30]}", url=url
                    )])

        kb_rows = dl_buttons + [[InlineKeyboardButton("🔍 View Release", url=release.get("html_url", run_url) if release else run_url)]]

        text = (
            f"╔══ ✅ *BUILD COMPLETE!* ══╗\n"
            f"┃\n"
            f"┃  🎉 *PBRP Built Successfully!*\n"
            f"┃  ⏱️ الوقت: `{fmt_duration(elapsed)}`\n"
            f"┃  📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"┃\n"
            + (f"┃ *الملفات:*{assets_text}\n┃\n" if assets_text else "")
            + f"╚══════════════════════════╝"
        )
    else:
        reason = run.get("conclusion", "unknown")
        text = (
            f"╔══ ❌ *BUILD FAILED* ══╗\n"
            f"┃\n"
            f"┃  ❌ فشل البناء: `{reason}`\n"
            f"┃  ⏱️ الوقت: `{fmt_duration(elapsed)}`\n"
            f"┃  📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"┃\n"
            f"┃  🔍 تحقق من logs في GitHub Actions\n"
            f"╚═══════════════════════╝"
        )
        kb_rows = [[InlineKeyboardButton("🔍 View Logs", url=run_url)]]

    try:
        await app.bot.edit_message_text(
            chat_id=chat_id, message_id=msg_id,
            text=text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(kb_rows)
        )
    except:
        try:
            await app.bot.send_message(
                chat_id=chat_id, text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except:
            pass

    # Notify
    emoji = "✅" if conclusion == "success" else "❌"
    try:
        await app.bot.send_message(
            chat_id=chat_id,
            text=f"{emoji} البناء انتهى في `{fmt_duration(elapsed)}`!\n" +
                 ("⬆️ روابط التحميل فوق 👆" if conclusion == "success" else "⬆️ راجع الأخطاء فوق 👆"),
            parse_mode=ParseMode.MARKDOWN
        )
    except:
        pass

    active_builds.pop(uid, None)

# ─── REFRESH CALLBACK ──────────────────────────────────────

async def callback_refresh(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🔄 جاري التحديث...")
    uid = int(query.data.split(":", 1)[1])

    info = active_builds.get(uid)
    if not info:
        await query.answer("لا يوجد بناء نشط.")
        return

    token   = info["token"]
    repo    = info["repo"]
    run_id  = info["run_id"]
    cfg     = info["cfg"]
    elapsed = time.time() - info["start_ts"]

    run  = get_run_status(token, repo, run_id)
    jobs = get_run_jobs(token, repo, run_id)
    if not run:
        return

    text = build_status_text(cfg, run, elapsed, jobs)
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔍 GitHub", url=run.get("html_url", "")),
        InlineKeyboardButton("🔄 تحديث", callback_data=f"refresh:{uid}")
    ]])
    try:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    except:
        pass

# ─── STATUS COMMAND ────────────────────────────────────────

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    info = active_builds.get(uid)

    if not info:
        await update.message.reply_text(
            "📭 لا يوجد بناء نشط حالياً.\n\nاستخدم /build لبدء بناء جديد.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    token   = info["token"]
    repo    = info["repo"]
    run_id  = info["run_id"]
    cfg     = info["cfg"]
    elapsed = time.time() - info["start_ts"]

    run  = get_run_status(token, repo, run_id)
    jobs = get_run_jobs(token, repo, run_id)
    if not run:
        await update.message.reply_text("⚠️ فشل جلب حالة البناء.")
        return

    text = build_status_text(cfg, run, elapsed, jobs)
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔍 GitHub", url=run.get("html_url", "")),
        InlineKeyboardButton("🔄 تحديث", callback_data=f"refresh:{uid}")
    ]])
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

# ─── CANCEL BUILD ──────────────────────────────────────────

async def cmd_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    info = active_builds.get(uid)

    if not info:
        await update.message.reply_text("📭 لا يوجد بناء نشط لإلغائه.")
        return

    token  = info["token"]
    repo   = info["repo"]
    run_id = info["run_id"]

    url = f"{GH_API}/repos/{repo}/actions/runs/{run_id}/cancel"
    r = requests.post(url, headers=gh_headers(token), timeout=10)

    if r.status_code == 202:
        active_builds.pop(uid, None)
        await update.message.reply_text("⛔ *تم إلغاء البناء بنجاح.*", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"❌ فشل الإلغاء (HTTP {r.status_code}).")

# ─── RELEASE COMMAND ───────────────────────────────────────

async def cmd_release(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    cfg = user_config.get(uid)
    if not cfg or "gh_token" not in cfg:
        await update.message.reply_text("⚠️ استخدم /setup أولاً.")
        return

    token = cfg["gh_token"]
    repo  = cfg.get("repo", "")
    if not repo:
        await update.message.reply_text("⚠️ لم تحدد الريبو. استخدم /setup.")
        return

    release = get_latest_release(token, repo)
    if not release:
        await update.message.reply_text("📭 لا توجد إصدارات حالياً.")
        return

    assets = release.get("assets", [])
    assets_text = ""
    dl_buttons  = []

    for asset in assets:
        name = asset["name"]
        url  = asset["browser_download_url"]
        size = asset["size"] // (1024 * 1024)
        assets_text += f"\n📦 `{name}` — *{size} MB*"
        if len(dl_buttons) < 5:
            dl_buttons.append([InlineKeyboardButton(f"⬇️ {name[:35]}", url=url)])

    tag  = release.get("tag_name", "?")
    body = release.get("body", "")[:200]
    date = release.get("published_at", "")[:10]

    text = (
        f"📦 *آخر إصدار PBRP*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏷️ Tag: `{tag}`\n"
        f"📅 Date: `{date}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
        + assets_text
        + f"\n━━━━━━━━━━━━━━━━━━━━━"
    )

    dl_buttons.append([InlineKeyboardButton("🔗 View on GitHub", url=release.get("html_url", ""))])
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(dl_buttons))

# ─── CONFIG COMMAND ────────────────────────────────────────

async def cmd_config(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    cfg = user_config.get(uid, {})
    b   = cfg.get("build", BUILD_DEFAULTS)

    text = (
        f"⚙️ *الإعدادات الحالية*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 GitHub User: `{cfg.get('gh_user', 'غير محدد')}`\n"
        f"🏗️ Repo: `{cfg.get('repo', 'غير محدد')}`\n"
        f"📋 Workflow: `{cfg.get('workflow', 'غير محدد')}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 Manifest: `{b.get('manifest_branch', '?')}`\n"
        f"🎯 Target: `{b.get('build_target', '?')}`\n"
        f"🌳 Tree: `{b.get('device_tree', '?')}`\n"
        f"🌿 Branch: `{b.get('device_tree_branch', '?')}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def cmd_reset(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_config.pop(uid, None)
    active_builds.pop(uid, None)
    await update.message.reply_text("🗑️ تم مسح جميع الإعدادات.\nاستخدم /setup للبدء من جديد.")

# ─── TEXT HANDLER (for mid-conversation inputs) ────────────

async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    awaiting = ctx.user_data.get("awaiting")

    if awaiting == "device_tree":
        url = update.message.text.strip()
        if not url.startswith("http"):
            await update.message.reply_text("❌ رابط غير صحيح.")
            return
        user_config.setdefault(uid, {}).setdefault("build", BUILD_DEFAULTS.copy())
        user_config[uid]["build"]["device_tree"] = url
        ctx.user_data.pop("awaiting", None)
        await update.message.reply_text(
            f"✅ Device Tree: `{url}`\n\nأرسل /build مجدداً لاستكمال الإعداد.",
            parse_mode=ParseMode.MARKDOWN
        )

# ─── MAIN ──────────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Setup conversation
    setup_conv = ConversationHandler(
        entry_points=[CommandHandler("setup", cmd_setup)],
        states={
            ASK_GH_TOKEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_gh_token)],
            ASK_REPO:     [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_repo)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel_conv)],
        allow_reentry=True
    )

    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("build",   cmd_build))
    app.add_handler(CommandHandler("status",  cmd_status))
    app.add_handler(CommandHandler("cancel",  cmd_cancel))
    app.add_handler(CommandHandler("release", cmd_release))
    app.add_handler(CommandHandler("config",  cmd_config))
    app.add_handler(CommandHandler("reset",   cmd_reset))
    app.add_handler(setup_conv)

    app.add_handler(CallbackQueryHandler(callback_build,        pattern=r"^bld:"))
    app.add_handler(CallbackQueryHandler(callback_refresh,      pattern=r"^refresh:"))
    app.add_handler(CallbackQueryHandler(callback_set_workflow, pattern=r"^setwf:"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🤖 PBRP Builder Bot is RUNNING...")
    print(f"📡 Bot Token: {BOT_TOKEN[:20]}...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
