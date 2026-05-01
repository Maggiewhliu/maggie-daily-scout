#!/usr/bin/env python3
"""Maggie Daily Scout v3
每日 GitHub + AI 自動化案例 → 商業分析 → 三平台分版文案（Threads/Substack/Medium）→ Notion
"""
import os, json, urllib.request, urllib.error, urllib.parse
from datetime import datetime, timezone, timedelta

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
NOTION_PAGE_ID = "34c7266f944c80b5aef2dca4cba2e6af"
TPE = timezone(timedelta(hours=8))
TODAY = datetime.now(TPE).strftime("%Y-%m-%d")
WEEKDAY_TW = ["一", "二", "三", "四", "五", "六", "日"][datetime.now(TPE).weekday()]


def http_request(url, headers=None, data=None, method="GET"):
    req = urllib.request.Request(url, headers=headers or {}, method=method)
    if data:
        req.data = json.dumps(data).encode("utf-8")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP {e.code}: {e.read().decode()[:300]}")
        return None
    except Exception as e:
        print(f"❌ {e}")
        return None


def fetch_github_trending():
    """爬 AI / LLM / Agent / Automation 四類熱門 repo"""
    print("📊 爬 GitHub Trending...")
    week_ago = (datetime.now(TPE) - timedelta(days=7)).strftime("%Y-%m-%d")
    queries = [
        f"created:>{week_ago} topic:ai language:Python",
        f"created:>{week_ago} topic:llm",
        f"created:>{week_ago} topic:agent",
        f"created:>{week_ago} topic:automation",
        f"created:>{week_ago} topic:no-code",
    ]
    seen, repos = set(), []
    for q in queries:
        url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(q)}&sort=stars&order=desc&per_page=5"
        result = http_request(url, headers={"Accept": "application/vnd.github+json"})
        if not result or "items" not in result:
            continue
        for r in result["items"]:
            if r["full_name"] in seen:
                continue
            seen.add(r["full_name"])
            repos.append({
                "name": r["full_name"], "url": r["html_url"],
                "desc": (r.get("description") or "")[:200],
                "stars": r["stargazers_count"], "lang": r.get("language") or "—",
            })
    repos.sort(key=lambda x: x["stars"], reverse=True)
    return repos[:8]


def fetch_anthropic_skills():
    print("🛠️  爬 Claude Skills...")
    week_ago = (datetime.now(TPE) - timedelta(days=7)).strftime("%Y-%m-%d")
    url = f"https://api.github.com/search/repositories?q=claude-skill+OR+anthropic-skill+pushed:>{week_ago}&sort=stars&order=desc&per_page=5"
    result = http_request(url, headers={"Accept": "application/vnd.github+json"})
    if not result or "items" not in result:
        return []
    return [{"name": r["full_name"], "url": r["html_url"],
             "desc": (r.get("description") or "")[:200],
             "stars": r["stargazers_count"]} for r in result["items"]]


def fetch_automation_cases():
    """爬 AI 自動化、no-code、indie hackers 類型案例 repo"""
    print("⚡ 爬 AI 自動化案例...")
    month_ago = (datetime.now(TPE) - timedelta(days=30)).strftime("%Y-%m-%d")
    queries = [
        f"pushed:>{month_ago} topic:make-automation",
        f"pushed:>{month_ago} topic:n8n",
        f"pushed:>{month_ago} topic:zapier",
        f"pushed:>{month_ago} topic:workflow-automation",
    ]
    seen, cases = set(), []
    for q in queries:
        url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(q)}&sort=stars&order=desc&per_page=3"
        result = http_request(url, headers={"Accept": "application/vnd.github+json"})
        if not result or "items" not in result:
            continue
        for r in result["items"]:
            if r["full_name"] in seen:
                continue
            seen.add(r["full_name"])
            cases.append({
                "name": r["full_name"], "url": r["html_url"],
                "desc": (r.get("description") or "")[:200],
                "stars": r["stargazers_count"],
            })
    cases.sort(key=lambda x: x["stars"], reverse=True)
    return cases[:5]


def call_claude(prompt, max_tokens=2500):
    result = http_request(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        data={"model": "claude-opus-4-5", "max_tokens": max_tokens,
              "messages": [{"role": "user", "content": prompt}]},
        method="POST",
    )
    if not result:
        return None
    return result["content"][0]["text"]


def analyze_opportunities(repos, skills, cases):
    """區塊一：開源 + 案例的商機分析"""
    print("🧠 商機分析中...")
    items = "## GitHub Trending\n"
    for r in repos:
        items += f"- **{r['name']}** ({r['stars']}★, {r['lang']}): {r['desc']}\n"
    items += "\n## Claude Skills\n"
    for s in skills:
        items += f"- **{s['name']}** ({s['stars']}★): {s['desc']}\n"
    items += "\n## AI 自動化案例\n"
    for c in cases:
        items += f"- **{c['name']}** ({c['stars']}★): {c['desc']}\n"
    
    prompt = f"""你是 Maggie 的 AI 情報員 Chris。

Maggie 個人品牌定位（已避開電通敏感業務線）：
- Business Strategy & AI Automation Builder
- 三大內容軸：商業策略 × AI 自動化 × 投資思維
- 公開平台：Threads（短觀點）、Substack（深度）、Medium（深度）
- 法務避雷區：Retail Media、Media Bridge、客戶名、內部專案、集團產品線

今天爬到：

{items}

請挑 5 個最有商機的，格式（繁中、簡短）：
- **[名字]** ({{星數}}★) — 一句話它是什麼
  - **對 Maggie**：一句話商機（接「個人品牌內容素材」/「AI 自動化展示」/「投資洞察」哪一塊）

只挑真有商機的。別講廢話。"""

    return call_claude(prompt, max_tokens=1500) or "（API 失敗）"


def generate_personal_notes(repos, cases, opp_analysis):
    """區塊二：個人版策略筆記（不公開）"""
    print("📓 生成個人版策略筆記...")
    
    items_summary = "\n".join([f"- {r['name']}: {r['desc'][:80]}" for r in repos[:3]])
    cases_summary = "\n".join([f"- {c['name']}: {c['desc'][:80]}" for c in cases[:3]])
    
    prompt = f"""你是 Maggie 的私人策略顧問。今天 {TODAY}（週{WEEKDAY_TW}）。

Maggie 現況（私下版本，不會公開）：
- 本業：dentsu Group Commercial Product Strategy
- 個人品牌轉型期：從廣告 senior 走向 AI Automation Builder
- Maggie Stock AI 暫緩上線（避免抄襲 + 法務雙重風險）
- 已上線自動化：Chris（這個腳本）
- 暫停中：Alex / Bella / Luna
- 要規避：電通法務（Retail Media / Media Bridge / 內部資訊）
- 痛點：時間、token 成本、變現速度

今日情報：
GitHub: {items_summary}
案例: {cases_summary}

寫 3 點「只給 Maggie 自己看」的策略觀察，每點：
- 連結到她的本業 / 個人品牌 / 投資
- 可以是「不能公開但要知道」的內部視角
- 直接、不客套、像顧問講悄悄話

格式（嚴格遵守）：
**1. [一句話標題]**
[2-3 句具體觀察]

**2. [一句話標題]**
[2-3 句具體觀察]

**3. [一句話標題]**
[2-3 句具體觀察]

別寫開頭介紹、別寫結尾，直接從 1 開始。"""

    return call_claude(prompt, max_tokens=1500) or "（API 失敗）"


def generate_threads_post(opp_analysis):
    """區塊三：Threads 文案（500 字元）"""
    print("📱 生成 Threads 文案...")
    
    prompt = f"""你是 Maggie，幫她寫一篇 Threads 貼文。

Maggie 風格：
- Business Strategy & AI Automation Builder
- 「商業變現是技術，自由生活是藝術」
- 真實、有觀點、不油膩、不像在賣課
- 寫給：30-45 歲對 AI / 商業 / 投資有興趣的人
- 法務避雷：不能提電通、客戶、內部專案、Retail Media、Media Bridge

今日情報摘要：
{opp_analysis[:1000]}

從中挑「對讀者最有 aha moment」的角度，寫一篇 Threads。

嚴格規定：
- 繁中
- **不超過 450 字元**（Threads 上限 500，預留空間）
- 開頭一句要勾人（不要「今天分享...」這種廢話）
- 中間 2-3 個短段落（每段 1-2 句）
- 結尾一句金句或反問
- 不要 hashtag
- 不要 emoji（除非真的必要）

直接寫文案，不要標題、不要說明、不要「以下是文案」這種前綴。"""

    return call_claude(prompt, max_tokens=800) or "（API 失敗）"


def generate_substack_post(opp_analysis, personal_notes):
    """區塊四：Substack 文案（1500 字）"""
    print("📝 生成 Substack 文案...")
    
    prompt = f"""你是 Maggie，幫她寫一篇 Substack 文章。

Maggie 風格：
- Business Strategy & AI Automation Builder
- 三軸：商業策略 × AI 自動化 × 投資思維
- 評論者視角，不是內部人視角
- 法務避雷：電通、客戶、內部資訊、Retail Media、Media Bridge

今日素材：
[商機分析]
{opp_analysis[:1500]}

[私人觀察 — 可以參考切角，但不要直接寫進文章]
{personal_notes[:1000]}

寫一篇深度文章。

嚴格規定：
- 繁中
- **800-1500 字**（重點是讀完不費力）
- 結構：
  ## [標題：吸引人、有觀點，不要太教學感]
  
  [導言 2-3 句，從一個現象 / 數據 / 觀察切入]
  
  ### [小標 1：一個觀察]
  [2-3 段論述]
  
  ### [小標 2：一個延伸]
  [2-3 段論述]
  
  ### [收尾：給讀者帶走什麼]
  [1 段]
- 不要列點過多，要有論述感
- SEO 友善：標題和小標自然包含「AI 自動化 / 商業策略 / 投資」等關鍵字
- 結尾不要 CTA、不要訂閱呼籲（之後再補）

直接從 ## 標題開始，不要任何前綴或說明。"""

    return call_claude(prompt, max_tokens=3500) or "（API 失敗）"


def generate_medium_post(opp_analysis, personal_notes):
    """區塊五：Medium 文案（1500 字 / 英文版本適合 Medium 受眾）"""
    print("📰 生成 Medium 文案...")
    
    prompt = f"""You are Maggie, a Business Strategy & AI Automation Builder.

Style:
- Three pillars: Business Strategy × AI Automation × Investment Thinking
- Critic's perspective, not insider's perspective
- Audience: international readers on Medium (English readers, professionals)
- Legal sensitivity: avoid mentioning dentsu, clients, internal projects, Retail Media, Media Bridge

Today's material:
[Market analysis]
{opp_analysis[:1500]}

[Private observations — for inspiration, do NOT include directly]
{personal_notes[:1000]}

Write a Medium article.

Strict rules:
- **English**
- **800-1500 words**
- Structure:
  # [Title: catchy, opinion-driven, not too tutorial-ish]
  
  [Intro 2-3 sentences, hook with an observation/data point]
  
  ## [Subhead 1: an observation]
  [2-3 paragraphs of argument]
  
  ## [Subhead 2: an extension]
  [2-3 paragraphs of argument]
  
  ## [Takeaway]
  [1 paragraph]
- Avoid excessive bullet points; favor narrative
- SEO-friendly: title and subheads naturally include "AI automation / business strategy / investment"
- No CTA or subscription pitch at the end

Start directly from the # title. No preamble."""

    return call_claude(prompt, max_tokens=3500) or "（API 失敗）"


def parse_rich_text(text):
    """處理 **bold** 標記"""
    parts = []
    remaining = text[:1900]
    while "**" in remaining:
        before, _, after = remaining.partition("**")
        if before:
            parts.append({"type": "text", "text": {"content": before}})
        bold_text, _, remaining = after.partition("**")
        if bold_text:
            parts.append({
                "type": "text", "text": {"content": bold_text},
                "annotations": {"bold": True}
            })
    if remaining:
        parts.append({"type": "text", "text": {"content": remaining}})
    return parts if parts else [{"type": "text", "text": {"content": text[:1900]}}]


def text_to_notion_blocks(text):
    """把 markdown 轉 Notion blocks"""
    blocks = []
    for line in text.split("\n"):
        line = line.rstrip()
        if not line:
            continue
        if line.startswith("# "):
            blocks.append({"object": "block", "type": "heading_2",
                "heading_2": {"rich_text": parse_rich_text(line[2:])}})
        elif line.startswith("## "):
            blocks.append({"object": "block", "type": "heading_3",
                "heading_3": {"rich_text": parse_rich_text(line[3:])}})
        elif line.startswith("### "):
            blocks.append({"object": "block", "type": "heading_3",
                "heading_3": {"rich_text": parse_rich_text(line[4:])}})
        elif line.startswith("  - "):
            blocks.append({"object": "block", "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": parse_rich_text("  " + line[4:])}})
        elif line.startswith("- "):
            blocks.append({"object": "block", "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": parse_rich_text(line[2:])}})
        else:
            blocks.append({"object": "block", "type": "paragraph",
                "paragraph": {"rich_text": parse_rich_text(line)}})
    return blocks


def code_block(content, language="markdown"):
    """Notion code block（方便一鍵複製）"""
    return {
        "object": "block", "type": "code",
        "code": {
            "rich_text": [{"type": "text", "text": {"content": content[:1990]}}],
            "language": language,
        }
    }


def write_to_notion(opp, personal, threads, substack, medium, repos, skills, cases):
    print("📤 寫進 Notion...")
    
    blocks = [
        {"object": "block", "type": "divider", "divider": {}},
        {"object": "block", "type": "heading_1",
         "heading_1": {"rich_text": [{"type": "text",
            "text": {"content": f"🌅 {TODAY}（週{WEEKDAY_TW}）每日情報 + 三平台文案"}}]}},
        {"object": "block", "type": "callout",
         "callout": {"rich_text": [{"type": "text",
            "text": {"content": f"GitHub {len(repos)}｜Skills {len(skills)}｜自動化案例 {len(cases)}｜每日 09:00"}}],
                     "icon": {"type": "emoji", "emoji": "🤖"}}},
        
        # === 1. 開源商機 ===
        {"object": "block", "type": "heading_2",
         "heading_2": {"rich_text": [{"type": "text", "text": {"content": "🎯 今日商機分析"}}]}},
    ]
    blocks.extend(text_to_notion_blocks(opp))
    
    # === 2. 個人筆記（私密）===
    blocks.append({"object": "block", "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "📓 個人版策略筆記（私密）"}}]}})
    blocks.append({"object": "block", "type": "callout",
        "callout": {"rich_text": [{"type": "text",
            "text": {"content": "只給 Maggie 看｜不要公開分享｜可能涉及內部視角"}}],
                    "icon": {"type": "emoji", "emoji": "🔒"}}})
    blocks.extend(text_to_notion_blocks(personal))
    
    # === 3. Threads 文案（code block 方便複製）===
    blocks.append({"object": "block", "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "📱 Threads 文案（500 字元內）"}}]}})
    blocks.append({"object": "block", "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text",
            "text": {"content": f"字元數：{len(threads)}｜上限：500"}}]}})
    blocks.append(code_block(threads, "plain text"))
    
    # === 4. Substack 文案 ===
    blocks.append({"object": "block", "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "📝 Substack 文案（繁中 800-1500 字）"}}]}})
    blocks.append({"object": "block", "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text",
            "text": {"content": f"字數：{len(substack)}"}}]}})
    blocks.append(code_block(substack, "markdown"))
    
    # === 5. Medium 文案 ===
    blocks.append({"object": "block", "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "📰 Medium 文案（English 800-1500 words）"}}]}})
    blocks.append({"object": "block", "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text",
            "text": {"content": f"Words: {len(medium.split())}"}}]}})
    blocks.append(code_block(medium, "markdown"))
    
    # === 6. 原始資料 ===
    blocks.append({"object": "block", "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "📋 完整爬取清單"}}]}})
    blocks.append({"object": "block", "type": "heading_3",
        "heading_3": {"rich_text": [{"type": "text", "text": {"content": "GitHub Trending"}}]}})
    for r in repos:
        blocks.append({"object": "block", "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": [
                {"type": "text", "text": {"content": f"{r['name']} ({r['stars']}★) ", "link": {"url": r["url"]}}},
                {"type": "text", "text": {"content": f"— {r['desc']}"}}]}})
    if skills:
        blocks.append({"object": "block", "type": "heading_3",
            "heading_3": {"rich_text": [{"type": "text", "text": {"content": "Claude Skills"}}]}})
        for s in skills:
            blocks.append({"object": "block", "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [
                    {"type": "text", "text": {"content": f"{s['name']} ({s['stars']}★) ", "link": {"url": s["url"]}}},
                    {"type": "text", "text": {"content": f"— {s['desc']}"}}]}})
    if cases:
        blocks.append({"object": "block", "type": "heading_3",
            "heading_3": {"rich_text": [{"type": "text", "text": {"content": "AI 自動化案例"}}]}})
        for c in cases:
            blocks.append({"object": "block", "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [
                    {"type": "text", "text": {"content": f"{c['name']} ({c['stars']}★) ", "link": {"url": c["url"]}}},
                    {"type": "text", "text": {"content": f"— {c['desc']}"}}]}})
    blocks.append({"object": "block", "type": "divider", "divider": {}})
    
    for i in range(0, len(blocks), 100):
        chunk = blocks[i:i+100]
        result = http_request(
            f"https://api.notion.com/v1/blocks/{NOTION_PAGE_ID}/children",
            headers={"Authorization": f"Bearer {NOTION_TOKEN}",
                     "Content-Type": "application/json", "Notion-Version": "2022-06-28"},
            data={"children": chunk}, method="PATCH",
        )
        if not result:
            print(f"❌ 第 {i//100 + 1} 批失敗")
            return False
    print(f"✅ 寫入完成，共 {len(blocks)} 個 blocks")
    return True


def main():
    print(f"🚀 Chris v3 — {TODAY} 週{WEEKDAY_TW}")
    repos = fetch_github_trending()
    skills = fetch_anthropic_skills()
    cases = fetch_automation_cases()
    
    if not repos and not skills and not cases:
        print("⚠️  今天沒爬到東西"); return
    
    opp = analyze_opportunities(repos, skills, cases)
    personal = generate_personal_notes(repos, cases, opp)
    threads = generate_threads_post(opp)
    substack = generate_substack_post(opp, personal)
    medium = generate_medium_post(opp, personal)
    
    print(f"\n📱 Threads ({len(threads)} 字元)")
    print(f"📝 Substack ({len(substack)} 字)")
    print(f"📰 Medium ({len(medium.split())} words)\n")
    
    write_to_notion(opp, personal, threads, substack, medium, repos, skills, cases)
    print("🎉 完成")


if __name__ == "__main__":
    main()
