"""블로그 글(content/posts/*.md)을 cutroom-notes의 5개 언어로 번역해 content/<언어>/<슬러그>.md 로 쓴다.

GitHub Actions(.github/workflows/translate-cutroom.yml)에서 돌린다. 번역 호출은 Gemini API.

  python tools/translate_cutroom.py --out cutroom --files content/posts/2026-10-19-hello.md
  python tools/translate_cutroom.py --out cutroom --missing        # 아직 번역 안 된 글 전부
  python tools/translate_cutroom.py --out cutroom --slug hello --force

환경 변수: GEMINI_API_KEY (필수), GEMINI_MODEL (기본 gemini-3.8-flash)
번역본에는 title·date·summary·series·part·cover·youtube 만 남긴다(category·tags는 다국어 사이트가 쓰지 않는다).
글에 쓰인 이미지는 같은 경로로 cutroom-notes의 images/ 에 복사한다.
"""
import argparse
import concurrent.futures as cf
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

LANG_NAMES = {
    "en": "English",
    "id": "Indonesian (Bahasa Indonesia)",
    "hi": "Hindi",
    "ar": "Arabic (Modern Standard Arabic)",
    "th": "Thai",
}
KEEP_KEYS = ["title", "date", "series", "part", "cover", "youtube", "summary"]
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

PROMPT = """You are translating a personal blog post by Kelvin, a Korean content creator, from Korean into {lang}.

Rules:
- Translate faithfully and naturally, keeping the first-person voice and the plain, unpretentious tone. Do not add, remove, embellish or explain anything.
- Keep the Markdown structure exactly: headings, tables (same rows and columns), bold, lists, blockquotes, code blocks, blank lines.
- Do NOT translate or change: URLs, link targets, image paths, code, command lines, file names, product names, numbers, units, and the blog name "강PD 로그".
- Translate image alt text and link text.
- Inside code blocks, keep code as it is; translate only natural-language comments if there are any.
- "summary" is a one-sentence description of the post for search results; translate it as one sentence.
- Output a JSON object with exactly three string fields: "title", "summary", "body". "body" is the translated Markdown without front matter.

Title: {title}
Summary: {summary}

Body:
{body}
"""


def split_front(text):
    m = re.match(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", text, re.S)
    if not m:
        raise ValueError("머리말(---)이 없다")
    return yaml.safe_load(m.group(1)) or {}, m.group(2).lstrip("\n")


def slug_of(path):
    return re.sub(r"^\d{4}-\d{2}-\d{2}-", "", Path(path).stem)


def gemini(prompt, key):
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 65536,
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {k: {"type": "STRING"} for k in ("title", "summary", "body")},
                "required": ["title", "summary", "body"],
            },
        },
    }).encode()
    req = urllib.request.Request(API.format(model=MODEL), data=body, headers={
        "Content-Type": "application/json", "x-goog-api-key": key})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.load(r)
    cand = data["candidates"][0]
    if cand.get("finishReason") not in (None, "STOP"):
        raise RuntimeError(f"finishReason={cand.get('finishReason')}")
    return json.loads("".join(p.get("text", "") for p in cand["content"]["parts"]))


def structure(md):
    """번역이 잘렸거나 구조가 깨졌는지 보려고 센다."""
    return (len(re.findall(r"^#{1,6} ", md, re.M)),
            len(re.findall(r"^\|.*\|\s*$", md, re.M)),
            len(re.findall(r"!\[", md)),
            md.count("```"))


def translate(meta, body, lang, key):
    prompt = PROMPT.format(lang=LANG_NAMES[lang], title=meta["title"],
                           summary=meta.get("summary", ""), body=body)
    last = None
    for attempt in range(6):
        try:
            out = gemini(prompt, key)
            if structure(out["body"]) != structure(body):
                raise ValueError(f"구조 불일치 {structure(body)} → {structure(out['body'])}")
            if not out["title"].strip():
                raise ValueError("제목 비어 있음")
            return out
        except (OSError, RuntimeError, ValueError, KeyError, json.JSONDecodeError) as e:  # OSError: 연결 끊김·타임아웃·URLError
            last = e
            if isinstance(e, urllib.error.HTTPError) and e.code not in (429, 500, 502, 503, 504):
                raise
            time.sleep(10 * 2 ** attempt)
    raise RuntimeError(f"{lang}: 재시도 소진: {last}")


def render(meta, out):
    fm = {k: meta[k] for k in KEEP_KEYS if k in meta and k not in ("title", "summary")}
    fm["title"], fm["summary"] = out["title"].strip(), out["summary"].strip()
    order = [k for k in KEEP_KEYS if k in fm]
    head = "".join(
        f"{k}: {json.dumps(fm[k], ensure_ascii=False)}\n" if k in ("title", "summary")
        else yaml.safe_dump({k: fm[k]}, allow_unicode=True, default_flow_style=False)
        for k in order)
    return f"---\n{head}---\n\n{out['body'].strip()}\n"


def copy_images(meta, body, src_root, out_root):
    refs = set(re.findall(r"\]\((/images/[^)\s]+)\)", body))
    if isinstance(meta.get("cover"), str) and meta["cover"].startswith("/images/"):
        refs.add(meta["cover"])
    for ref in refs:
        s, d = src_root / ref.lstrip("/"), out_root / ref.lstrip("/")
        if s.exists() and not d.exists():
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, d)
        elif not s.exists():
            print(f"  경고: 이미지 없음 {ref}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="cutroom-notes 체크아웃 경로")
    ap.add_argument("--files", nargs="*", default=[], help="번역할 원문 경로")
    ap.add_argument("--slug", help="이 슬러그의 글만")
    ap.add_argument("--missing", action="store_true", help="번역본이 없는 글 전부")
    ap.add_argument("--force", action="store_true", help="이미 있어도 다시 번역")
    ap.add_argument("--langs", default=",".join(LANG_NAMES))
    a = ap.parse_args()

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY 없음")
    root, out_root = Path.cwd(), Path(a.out)
    langs = [l for l in a.langs.split(",") if l]
    posts = sorted((root / "content" / "posts").glob("*.md"))

    if a.files:
        want = {Path(f).resolve() for f in a.files}
        posts = [p for p in posts if p.resolve() in want]
    elif a.slug:
        posts = [p for p in posts if slug_of(p) == a.slug]
    elif not a.missing:
        sys.exit("--files, --slug, --missing 중 하나가 필요하다")

    jobs, failed = [], []
    for p in posts:
        meta, body = split_front(p.read_text(encoding="utf-8"))
        if meta.get("draft"):
            print(f"건너뜀(draft): {p.name}")
            continue
        slug = slug_of(p)
        for lang in langs:
            dest = out_root / "content" / lang / f"{slug}.md"
            if a.force or a.files or a.slug or not dest.exists():
                jobs.append((p, meta, body, slug, lang, dest))
    print(f"번역 {len(jobs)}건, 모델 {MODEL}")

    def run(job):
        p, meta, body, slug, lang, dest = job
        res = translate(meta, body, lang, key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(render(meta, res), encoding="utf-8")
        print(f"  완료 {lang}/{slug}")

    with cf.ThreadPoolExecutor(max_workers=2) as ex:
        futs = {ex.submit(run, j): j for j in jobs}
        for f in cf.as_completed(futs):
            try:
                f.result()
            except Exception as e:  # noqa: BLE001
                j = futs[f]
                failed.append(f"{j[4]}/{j[3]}: {e}")
                print(f"  실패 {j[4]}/{j[3]}: {e}", file=sys.stderr)

    for p in {j[0] for j in jobs}:
        meta, body = split_front(p.read_text(encoding="utf-8"))
        copy_images(meta, body, root, out_root)

    if failed:
        print("\n실패 목록:\n" + "\n".join(failed), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
