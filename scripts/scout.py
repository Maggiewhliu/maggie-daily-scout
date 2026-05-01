#!/usr/bin/env python3
"""Maggie Daily Scout — 每日 GitHub + Skills 自動爬取 + Claude 分析 + 寫進 Notion"""
import os, json, urllib.request, urllib.error, urllib.parse
from datetime import datetime, timezone, timedelta

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
NOTION_PAGE_ID = "34c7266f944c80b5aef2dca4cba2e6af"
TPE = timezone(timedelta(hours=8))
TODAY = datetime.now(TPE).strftime("%Y-%m-%d")


def http_request(url, headers=None, data=None, method="GET"):
    req = urllib.request.Request(url, headers=headers or {}, method=method)
    if data:
        req.data = json.dumps(data).encode("utf-8")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP {e.code}: {e.read().decode()[:300]}")
        return None
    except Exception as e:
        print(f"❌ {e}")
        return None


def fetch_github_trending():
    print("📊 爬 GitHub Trending...")
    week_ago = (datetime.now(TPE) - timedelta(days=7)).strftime("%Y-%m-%d")
    queries = [
        f"created:>{week_ago} topic:ai language:Python",
        f"created:>{week_ago} topic:llm",
        f"created:>{week_ago} topic:agent",
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


def analyze_with_claude(repos, skills):
    print("🧠 Claude 分析中...")
    items_text = "## GitHub Trending\n"
    for r in repos:
        items_text += f"- **{r['name']}** ({r['stars']}★, {r['lang']}): {r['desc']}\n"
    items_text += "\n## Claude Skills\n"
    for s in skills:
        items_text += f"- **{s['name']}** ({s['stars']}★): {s['desc']}\n"
    prompt = f"""你是 Maggie 的 AI 情報員 Chris。Maggie 的事業：
- Maggie Stock AI（美股分析訂閱服務，付費用戶 + MRR）
- Dentsu 廣告公司 senior director（產品開發）
- 個人品牌：IG/Threads/FB 美股 + 媽媽 + AI

今天爬到這些 repo：

{items_text}

請從中挑 5 個最有商機的，每個用這格式（繁中、簡短、直接）：
- **[名字]** ({{星數}}★) — 一句話說它是什麼
  - **對 Maggie**：一句話商機（直接點名是接 Stock AI / Dentsu / 個人品牌哪一塊）

只挑真的有商機的，沒有就不寫滿 5 個。別講廢話。"""
    result = http_request(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        data={"model": "claude-opus-4-5", "max_tokens": 2000, "messages": [{"role": "user", "content": prompt}]},
        method="POST",
    )
    if not result:
        return "（Claude API 失敗，今日略過分析）"
    return result["content"][0]["text"]


def text_to_notion_blocks(text):
    blocks = []
    for line in text.split("\n"):
        line = line.rstrip()
        if not line:
            continue
        if line.startswith("- "):
            blocks.append({"object": "block", "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": line[2:][:1900]}}]}})
        elif line.startswith("  - "):
            blocks.append({"object": "block", "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": "  " + line[4:][:1900]}}]}})
        else:
            blocks.append({"object": "block", "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": line[:1900]}}]}})
    return blocks


def write_to_notion(analysis, repos, skills):
    print("📤 寫進 Notion...")
    blocks = [
        {"object": "block", "type": "divider", "divider": {}},
        {"object": "block", "type": "heading_1",
         "heading_1": {"rich_text": [{"type": "text", "text": {"content": f"🌅 {TODAY} 每日情報（Chris 自動）"}}]}},
        {"object": "block", "type": "callout",
         "callout": {"rich_text": [{"type": "text", "text": {"content": f"GitHub Trending {len(repos)} 個｜Claude Skills {len(skills)} 個｜每日 09:00 自動更新"}}],
                     "icon": {"type": "emoji", "emoji": "🤖"}}},
        {"object": "block", "type": "heading_2",
         "heading_2": {"rich_text": [{"type": "text", "text": {"content": "🎯 Chris 的商機分析"}}]}},
    ]
    blocks.extend(text_to_notion_blocks(analysis))
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
    blocks.append({"object": "block", "type": "divider", "divider": {}})
    for i in range(0, len(blocks), 100):
        chunk = blocks[i:i+100]
        result = http_request(
            f"https://api.notion.com/v1/blocks/{NOTION_PAGE_ID}/children",
            headers={"Authorization": f"Bearer {NOTION_TOKEN}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"},
            data={"children": chunk}, method="PATCH",
        )
        if not result:
            print(f"❌ 第 {i//100 + 1} 批失敗")
            return False
    print(f"✅ 寫入完成，共 {len(blocks)} 個 blocks")
    return True


def main():
    print(f"🚀 Maggie Daily Scout — {TODAY}")
    repos = fetch_github_trending()
    skills = fetch_anthropic_skills()
    if not repos and not skills:
        print("⚠️  今天沒爬到東西"); return
    analysis = analyze_with_claude(repos, skills)
    print("\n--- Chris 分析 ---\n", analysis, "\n--- 結束 ---\n")
    write_to_notion(analysis, repos, skills)
    print("🎉 完成")


if __name__ == "__main__":
    main()
