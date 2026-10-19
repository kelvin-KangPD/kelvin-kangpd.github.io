#!/usr/bin/env python3
"""강PD 로그 — 정적 블로그 빌더.

content/posts/*.md 를 읽어서 저장소 루트에 HTML을 만든다.
글 파일 맨 위 머리말 형식:

---
title: 글 제목
date: 2026-10-19
category: 작업기록   # 작업기록 / 생각 / 일상 / 숏츠
tags: [프리미어, 자막]
summary: 목록에 보일 한 줄 요약 (생략하면 본문 앞부분 사용)
youtube: 영상ID 또는 유튜브 주소 (숏츠 글이면 넣기)
---

본문 안 아무 곳에나 {{shorts: 영상ID 또는 주소}} / {{youtube: 영상ID 또는 주소}} 로 영상 삽입 가능.
"""
import html
import json
import re
import shutil
from datetime import date, datetime
from pathlib import Path

import markdown
import yaml

ROOT = Path(__file__).parent
POSTS_DIR = ROOT / "content" / "posts"
LAYOUT = (ROOT / "_layout" / "base.html").read_text(encoding="utf-8")

SITE = {
    "title": "강PD 로그",
    "desc": "작업과정과 생각, 일상을 쌓아두는 곳",
    "url": "https://kelvin-kangpd.github.io",
    "author": "강준구",
    "cusdis_app_id": "",  # cusdis.com 대시보드의 App ID. 비어 있으면 댓글창을 안 붙임
}
CUSDIS_LOCALE = {"powered_by": "Cusdis 제공", "post_comment": "등록", "loading": "불러오는 중...", "email": "이메일 (선택)", "nickname": "닉네임", "reply_placeholder": "댓글...", "reply_btn": "답글", "sending": "보내는 중...", "mod_badge": "운영자", "content_is_required": "내용을 입력해 주세요", "nickname_is_required": "닉네임을 입력해 주세요", "comment_has_been_sent": "댓글이 등록됐어요. 확인 후 보여요."}


def comments(p):
    if not SITE["cusdis_app_id"]:
        return ""
    return (f'<section class="comments"><h2>댓글</h2>'
            f'<script>window.CUSDIS_LOCALE={json.dumps(CUSDIS_LOCALE, ensure_ascii=False)}</script>'
            f'<div id="cusdis_thread" data-host="https://cusdis.com" data-app-id="{SITE["cusdis_app_id"]}" '
            f'data-page-id="ko:{p["slug"]}" data-page-url="{SITE["url"]}{p["url"]}" data-page-title="{html.escape(p["title"])}" data-theme="auto"></div>'
            '<script async defer src="https://cusdis.com/js/cusdis.es.js"></script></section>')
CATEGORIES = [
    ("작업기록", "work"),
    ("생각", "thoughts"),
    ("일상", "daily"),
    ("숏츠", "shorts"),
]
CAT_SLUG = dict(CATEGORIES)
GENERATED = ["posts", "category", "tag", "series", "index.html", "feed.xml", "404.html", "sitemap.xml", "robots.txt"]


def yt_id(v):
    v = str(v).strip()
    m = re.search(r"(?:shorts/|youtu\.be/|v=|embed/)([\w-]{11})", v)
    return m.group(1) if m else v


def embed(vid, vertical):
    cls = "video vertical" if vertical else "video"
    return (f'<div class="{cls}"><iframe src="https://www.youtube.com/embed/{yt_id(vid)}" '
            'title="YouTube" loading="lazy" allowfullscreen '
            'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"></iframe></div>')


def render_body(text):
    def repl(m):
        return "\n\n" + embed(m.group(2), m.group(1) == "shorts") + "\n\n"
    text = re.sub(r"\{\{\s*(shorts|youtube)\s*:\s*([^}]+?)\s*\}\}", repl, text)
    return markdown.markdown(text, extensions=["extra", "sane_lists", "toc"])


def load_posts():
    posts = []
    for f in sorted(POSTS_DIR.glob("*.md")):
        raw = f.read_text(encoding="utf-8")
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, re.S)
        meta, body = (yaml.safe_load(m.group(1)) or {}, m.group(2)) if m else ({}, raw)
        if meta.get("draft"):
            continue
        d = meta.get("date") or date.today()
        if isinstance(d, str):
            d = datetime.strptime(d[:10], "%Y-%m-%d").date()
        elif isinstance(d, datetime):
            d = d.date()
        slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", f.stem)
        cat = meta.get("category", "생각")
        plain = re.sub(r"<[^>]+>|\{\{.*?\}\}|[#*>`\[\]!]", "", body)
        plain = re.sub(r"\(http[^)]*\)", "", plain)
        summary = meta.get("summary") or " ".join(plain.split())[:110]
        posts.append({
            "title": meta.get("title", slug),
            "date": d,
            "category": cat,
            "tags": meta.get("tags") or [],
            "summary": summary,
            "youtube": meta.get("youtube"),
            "cover": meta.get("cover"),
            "series": meta.get("series"),
            "part": meta.get("part"),
            "slug": slug,
            "url": f"/posts/{slug}/",
            "html": render_body(body),
        })
    posts.sort(key=lambda p: (p["date"], p["slug"]), reverse=True)
    return posts


def load_series():
    f = ROOT / "content" / "series.yml"
    return (yaml.safe_load(f.read_text(encoding="utf-8")) or {}) if f.exists() else {}


SERIES = load_series()


def series_parts(sid, posts):
    info = SERIES.get(sid, {})
    pub = {p["part"]: p for p in posts if p["series"] == sid}
    plan = info.get("parts", [])
    n = max([len(plan)] + list(pub.keys() or [0]))
    rows = []
    for i in range(1, n + 1):
        p = pub.get(i)
        rows.append((i, p["title"] if p else (plan[i - 1] if i <= len(plan) else ""), p))
    return info, rows


def series_box(p, posts):
    info, rows = series_parts(p["series"], posts)
    items = ""
    for i, title, q in rows:
        if q is p:
            items += f'<li class="now"><span>{i}부</span>{html.escape(title)}</li>'
        elif q:
            items += f'<li><span>{i}부</span><a href="{q["url"]}">{html.escape(title)}</a></li>'
        else:
            items += f'<li class="soon"><span>{i}부</span>{html.escape(title)} <em>준비 중</em></li>'
    return (f'<aside class="series-box"><a class="series-name" href="/series/{p["series"]}/">시리즈 · '
            f'{html.escape(info.get("title", p["series"]))}</a><ol>{items}</ol></aside>')


def nav(active=""):
    items = ['<a href="/"%s>전체</a>' % (' class="on"' if active == "all" else "")]
    for name, slug in CATEGORIES:
        on = ' class="on"' if active == name else ""
        items.append(f'<a href="/category/{slug}/"{on}>{name}</a>')
    if SERIES:
        on = ' class="on"' if active == "series" else ""
        items.append(f'<a href="/series/"{on}>시리즈</a>')
    return "".join(items)


def page(title, body, active="", desc=None, image=None):
    full = SITE["title"] if title == SITE["title"] else f"{title} · {SITE['title']}"
    return (LAYOUT.replace("{{TITLE}}", html.escape(full))
            .replace("{{DESC}}", html.escape(desc or SITE["desc"]))
            .replace("{{OGIMAGE}}", (f'<meta property="og:image" content="{image if image.startswith("http") else SITE["url"] + image}">' if image else ""))
            .replace("{{SITE}}", SITE["title"])
            .replace("{{NAV}}", nav(active))
            .replace("{{BODY}}", body)
            .replace("{{YEAR}}", str(date.today().year))
            .replace("{{AUTHOR}}", SITE["author"]))


def fmt(d):
    return f"{d.year}. {d.month}. {d.day}."


def card(p):
    cslug = CAT_SLUG.get(p["category"], "thoughts")
    thumb = ""
    if p["cover"]:
        thumb = f'<img class="thumb wide" loading="lazy" alt="" src="{p["cover"]}">'
    elif p["youtube"]:
        thumb = (f'<img class="thumb" loading="lazy" alt="" '
                 f'src="https://i.ytimg.com/vi/{yt_id(p["youtube"])}/hqdefault.jpg">')
    return (f'<article class="card{" has-thumb" if thumb else ""}">'
            f'<a href="{p["url"]}" class="card-link">'
            f'<div class="card-text"><div class="meta"><span class="cat c-{cslug}">{p["category"]}</span>'
            f'<time>{fmt(p["date"])}</time></div>'
            f'<h2>{html.escape(p["title"])}</h2><p>{html.escape(p["summary"])}</p></div>{thumb}</a></article>')


def listing(posts, heading=None, sub=None):
    head = ""
    if heading:
        head = f'<header class="list-head"><h1>{html.escape(heading)}</h1>'
        head += f'<p>{html.escape(sub)}</p>' if sub else ""
        head += "</header>"
    if not posts:
        return head + '<p class="empty">아직 글이 없어요.</p>'
    return head + '<div class="list">' + "".join(card(p) for p in posts) + "</div>"


def write(rel, content):
    out = ROOT / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")


def post_page(p, prev, nxt, posts=()):
    cslug = CAT_SLUG.get(p["category"], "thoughts")
    tags = "".join(f'<a class="tag" href="/tag/{t}/">#{html.escape(str(t))}</a>' for t in p["tags"])
    video = embed(p["youtube"], p["category"] == "숏츠") if p["youtube"] and "{{" not in p["html"] and "youtube.com/embed" not in p["html"] else ""
    pager = '<nav class="pager">'
    pager += f'<a href="{nxt["url"]}"><span>다음 글</span>{html.escape(nxt["title"])}</a>' if nxt else "<span></span>"
    pager += f'<a href="{prev["url"]}" class="r"><span>이전 글</span>{html.escape(prev["title"])}</a>' if prev else "<span></span>"
    pager += "</nav>"
    body = (f'<article class="post"><header><a class="cat c-{cslug}" href="/category/{cslug}/">{p["category"]}</a>'
            f'<h1>{html.escape(p["title"])}</h1><time>{fmt(p["date"])}</time></header>'
            f'{series_box(p, posts) if p["series"] else ""}'
            f'{video}<div class="prose">{p["html"]}</div>'
            f'{series_box(p, posts) if p["series"] else ""}'
            f'<footer>{tags}</footer></article>{comments(p)}{pager}')
    og = p["cover"] or (f"https://i.ytimg.com/vi/{yt_id(p['youtube'])}/hqdefault.jpg" if p["youtube"] else None)
    return page(p["title"], body, p["category"], p["summary"], og)


def feed(posts):
    items = "".join(
        f"<item><title>{html.escape(p['title'])}</title><link>{SITE['url']}{p['url']}</link>"
        f"<guid>{SITE['url']}{p['url']}</guid><pubDate>{p['date'].strftime('%a, %d %b %Y 00:00:00 +0900')}</pubDate>"
        f"<description>{html.escape(p['summary'])}</description></item>" for p in posts[:30])
    return (f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
            f"<title>{SITE['title']}</title><link>{SITE['url']}</link><description>{SITE['desc']}</description>"
            f"<language>ko</language>{items}</channel></rss>")


def main():
    for g in GENERATED:
        t = ROOT / g
        if t.is_dir():
            shutil.rmtree(t)
        elif t.exists():
            t.unlink()
    posts = load_posts()
    write("index.html", page(SITE["title"], listing(posts), "all"))
    for i, p in enumerate(posts):
        prev = posts[i + 1] if i + 1 < len(posts) else None
        nxt = posts[i - 1] if i > 0 else None
        write(f"posts/{p['slug']}/index.html", post_page(p, prev, nxt, posts))
    sitems = ""
    for sid, info in SERIES.items():
        _, rows = series_parts(sid, posts)
        body = f'<header class="list-head"><h1>{html.escape(info.get("title", sid))}</h1><p>{html.escape(info.get("desc", ""))}</p></header><ol class="series-list">'
        for i, title, q in rows:
            if q:
                body += f'<li><a href="{q["url"]}"><span>{i}부</span>{html.escape(title)}<time>{fmt(q["date"])}</time></a></li>'
            else:
                body += f'<li class="soon"><span>{i}부</span>{html.escape(title)} <em>준비 중</em></li>'
        body += "</ol>"
        write(f"series/{sid}/index.html", page(info.get("title", sid), body, "series", info.get("desc")))
        done = sum(1 for r in rows if r[2])
        sitems += (f'<article class="card"><a href="/series/{sid}/" class="card-link"><div class="card-text">'
                   f'<div class="meta"><span>{done} / {len(rows)}부</span></div><h2>{html.escape(info.get("title", sid))}</h2>'
                   f'<p>{html.escape(info.get("desc", ""))}</p></div></a></article>')
    if SERIES:
        write("series/index.html", page("시리즈", '<header class="list-head"><h1>시리즈</h1><p>여러 편에 걸쳐 이어지는 글</p></header><div class="list">' + sitems + "</div>", "series"))
    subs = {"작업기록": "만들면서 배운 것들", "생각": "머릿속을 꺼내 정리해둔 것", "일상": "평범한 날의 기록", "숏츠": "짧게 찍고 짧게 남긴 영상"}
    for name, slug in CATEGORIES:
        sel = [p for p in posts if p["category"] == name]
        write(f"category/{slug}/index.html", page(name, listing(sel, name, subs.get(name)), name))
    tags = sorted({str(t) for p in posts for t in p["tags"]})
    for t in tags:
        sel = [p for p in posts if t in map(str, p["tags"])]
        write(f"tag/{t}/index.html", page(f"#{t}", listing(sel, f"#{t}")))
    write("feed.xml", feed(posts))
    urls = ["/"] + [f"/category/{s}/" for _, s in CATEGORIES] + [f"/series/{k}/" for k in SERIES] + [p["url"] for p in posts]
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
          + "".join(f"<url><loc>{SITE['url']}{u}</loc></url>" for u in urls) + "</urlset>")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE['url']}/sitemap.xml\n")
    write("404.html", page("페이지를 찾을 수 없어요",
                           '<div class="empty"><h1>404</h1><p>페이지를 찾을 수 없어요.</p><p><a href="/">처음으로</a></p></div>'))
    print(f"글 {len(posts)}개, 태그 {len(tags)}개 생성 완료")


if __name__ == "__main__":
    main()
