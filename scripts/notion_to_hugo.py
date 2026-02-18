from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from notion_client import Client
from slugify import slugify


# ---- CONFIG ----
HUGO_CONTENT_DIR = Path("site/content/posts")
DEFAULT_LANGUAGE = "ko"
DEFAULT_AUTHOR = ""
DRY_RUN = False  # True로 바꾸면 파일 쓰기 없이 출력만


# ---- Notion property names (스샷 기준) ----
PROP_TITLE = "Title"
PROP_SLUG = "Slug"
PROP_STATUS = "Status"
PROP_CHANNELS = "Channels"
PROP_TAGS = "Tags"
PROP_TYPE = "Type"
PROP_DATE = "Date"


READY_STATUS = "ready"
CHANNEL_GH = "GH"


@dataclass
class Post:
    page_id: str
    title: str
    slug: str
    date: str  # YYYY-MM-DD
    tags: List[str]
    type_: Optional[str]
    md_body: str


def _now_yyyy_mm_dd() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _safe_slug(title: str) -> str:
    # 한글도 허용(allow_unicode=True)
    s = slugify(title, allow_unicode=True)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "untitled"


def _get_title(props: Dict[str, Any]) -> str:
    t = props.get(PROP_TITLE, {})
    if t.get("type") == "title":
        parts = t.get("title", [])
        return "".join(p.get("plain_text", "") for p in parts).strip()
    # fallback: "Name" 같은 기본 타이틀 속성일 수 있음
    for k, v in props.items():
        if v.get("type") == "title":
            return "".join(p.get("plain_text", "") for p in v.get("title", [])).strip()
    return ""


def _get_select(props: Dict[str, Any], key: str) -> Optional[str]:
    v = props.get(key)
    if not v:
        return None
    if v.get("type") == "select" and v.get("select"):
        return v["select"]["name"]
    return None


def _get_multiselect(props: Dict[str, Any], key: str) -> List[str]:
    v = props.get(key)
    if not v:
        return []
    if v.get("type") == "multi_select":
        return [x["name"] for x in v.get("multi_select", []) if x.get("name")]
    return []


def _get_date(props: Dict[str, Any], key: str) -> Optional[str]:
    v = props.get(key)
    if not v:
        return None
    if v.get("type") == "date" and v.get("date") and v["date"].get("start"):
        # start may be 'YYYY-MM-DD' or ISO datetime; take date part
        return v["date"]["start"][:10]
    return None


def _has_channel(props: Dict[str, Any], channel_name: str) -> bool:
    channels = _get_multiselect(props, PROP_CHANNELS)
    return channel_name in channels


def _get_slug(props: Dict[str, Any], title: str) -> str:
    v = props.get(PROP_SLUG)
    if v and v.get("type") == "rich_text":
        rt = v.get("rich_text", [])
        s = "".join(p.get("plain_text", "") for p in rt).strip()
        if s:
            return _safe_slug(s)
    return _safe_slug(title)


def _rt_to_md(rich_text: List[Dict[str, Any]]) -> str:
    # Notion rich_text를 아주 단순하게 Markdown으로 변환 (bold/italic/code/link)
    out = []
    for t in rich_text:
        text = t.get("plain_text", "")
        ann = t.get("annotations", {}) or {}
        href = t.get("href")

        if ann.get("code"):
            text = f"`{text}`"
        if ann.get("bold"):
            text = f"**{text}**"
        if ann.get("italic"):
            text = f"*{text}*"
        if ann.get("strikethrough"):
            text = f"~~{text}~~"
        if href:
            text = f"[{text}]({href})"

        out.append(text)
    return "".join(out)


def _block_to_md(block: Dict[str, Any], indent: int = 0) -> str:
    t = block.get("type")
    data = block.get(t, {}) if t else {}

    prefix = " " * indent

    if t == "paragraph":
        txt = _rt_to_md(data.get("rich_text", []))
        return f"{prefix}{txt}\n" if txt.strip() else "\n"

    if t == "heading_1":
        txt = _rt_to_md(data.get("rich_text", []))
        return f"# {txt}\n\n"

    if t == "heading_2":
        txt = _rt_to_md(data.get("rich_text", []))
        return f"## {txt}\n\n"

    if t == "heading_3":
        txt = _rt_to_md(data.get("rich_text", []))
        return f"### {txt}\n\n"

    if t == "bulleted_list_item":
        txt = _rt_to_md(data.get("rich_text", []))
        return f"{prefix}- {txt}\n"

    if t == "numbered_list_item":
        txt = _rt_to_md(data.get("rich_text", []))
        # 번호는 Notion 순서를 모르니 1. 로 통일
        return f"{prefix}1. {txt}\n"

    if t == "quote":
        txt = _rt_to_md(data.get("rich_text", []))
        return f"> {txt}\n\n"

    if t == "code":
        txt = "".join(x.get("plain_text", "") for x in data.get("rich_text", []))
        lang = data.get("language", "")
        return f"```{lang}\n{txt}\n```\n\n"

    if t == "divider":
        return "\n---\n\n"

    if t == "callout":
        txt = _rt_to_md(data.get("rich_text", []))
        return f"> {txt}\n\n"

    if t == "to_do":
        txt = _rt_to_md(data.get("rich_text", []))
        checked = data.get("checked", False)
        box = "x" if checked else " "
        return f"{prefix}- [{box}] {txt}\n"

    if t == "image":
        # 이미지 자동화는 일단 제외(원하면 나중에 다운받아 static에 저장 가능)
        cap = _rt_to_md(data.get("caption", []))
        return f"\n<!-- image omitted: {cap} -->\n\n"

    # 기타 블록은 보수적으로 무시(원하면 계속 확장 가능)
    return ""


def fetch_page_markdown(notion: Client, page_id: str) -> str:
    md_lines: List[str] = []
    cursor = None
    while True:
        resp = notion.blocks.children.list(block_id=page_id, start_cursor=cursor) if cursor else notion.blocks.children.list(block_id=page_id)
        for b in resp.get("results", []):
            md_lines.append(_block_to_md(b))

            # children 처리 (리스트/토글 등)
            if b.get("has_children"):
                child_id = b["id"]
                child_cursor = None
                child_lines = []
                while True:
                    child_resp = notion.blocks.children.list(block_id=child_id, start_cursor=child_cursor) if child_cursor else notion.blocks.children.list(block_id=child_id)
                    for cb in child_resp.get("results", []):
                        child_lines.append(_block_to_md(cb, indent=2))
                    child_cursor = child_resp.get("next_cursor")
                    if not child_resp.get("has_more"):
                        break
                if child_lines:
                    # 바로 이어붙이기
                    md_lines.append("".join(child_lines) + "\n")

        cursor = resp.get("next_cursor")
        if not resp.get("has_more"):
            break

    # 정리: 연속 빈 줄 과다 제거
    md = "".join(md_lines)
    md = re.sub(r"\n{4,}", "\n\n\n", md)
    return md.strip() + "\n"


def make_frontmatter(p: Post) -> str:
    # YAML frontmatter (PaperMod/Hugo 표준)
    tags_yaml = "[" + ", ".join(f'"{t}"' for t in p.tags) + "]" if p.tags else "[]"
    # type_은 카테고리/태그로 쓰기 좋음. 여기선 tags에 섞지 않고 별도 param으로 둠.
    type_line = f'type: "{p.type_}"\n' if p.type_ else ""
    author_line = f'author: "{DEFAULT_AUTHOR}"\n' if DEFAULT_AUTHOR else ""

    fm = (
        "---\n"
        f'title: "{p.title}"\n'
        f"date: {p.date}\n"
        "draft: false\n"
        f"{author_line}"
        f"{type_line}"
        f"tags: {tags_yaml}\n"
        f'slug: "{p.slug}"\n'
        "---\n\n"
    )
    return fm


def get_first_data_source_id(notion, database_id: str) -> str:
    db = notion.databases.retrieve(database_id=database_id)
    data_sources = db.get("data_sources") or []
    if not data_sources:
        raise RuntimeError(
            "No data_sources found in this database. "
            "Check Notion-Version / integration permissions."
        )
    return data_sources[0]["id"]


def query_ready_gh_posts(notion: Client, db_id: str) -> List[Dict[str, Any]]:
    # Status == ready AND Channels contains GH
    # (Channels는 multi_select filter: contains)
    # Status는 select filter: equals
    data_source_id = get_first_data_source_id(notion, db_id)
    resp = notion.data_sources.query(
        data_source_id=data_source_id,
        filter={
            "and": [
                {"property": PROP_STATUS, "select": {"equals": READY_STATUS}},
                {"property": PROP_CHANNELS, "multi_select": {"contains": CHANNEL_GH}},
            ]
        },
        sorts=[{"property": PROP_DATE, "direction": "descending"}],
    )
    return resp.get("results", [])


def main() -> int:
    load_dotenv()
    token = os.getenv("NOTION_TOKEN")
    db_id = os.getenv("NOTION_DATABASE_ID")

    if not token or not db_id:
        print("ERROR: NOTION_TOKEN / NOTION_DATABASE_ID 가 .env에 필요합니다.", file=sys.stderr)
        return 1

    notion = Client(auth=token)

    HUGO_CONTENT_DIR.mkdir(parents=True, exist_ok=True)

    pages = query_ready_gh_posts(notion, db_id)
    print(f"Found {len(pages)} ready GH post(s).")

    for page in pages:
        page_id = page["id"]
        props = page.get("properties", {}) or {}

        title = _get_title(props)
        if not title:
            print(f"SKIP: no title (page_id={page_id})")
            continue

        slug = _get_slug(props, title)
        date = _get_date(props, PROP_DATE) or _now_yyyy_mm_dd()
        tags = _get_multiselect(props, PROP_TAGS)
        type_ = _get_select(props, PROP_TYPE)

        md_body = fetch_page_markdown(notion, page_id)

        post = Post(
            page_id=page_id,
            title=title,
            slug=slug,
            date=date,
            tags=tags,
            type_=type_,
            md_body=md_body,
        )

        out_path = HUGO_CONTENT_DIR / f"{post.slug}.md"
        content = make_frontmatter(post) + post.md_body

        if DRY_RUN:
            print(f"\n--- {out_path} ---\n{content[:800]}\n...")
            continue

        out_path.write_text(content, encoding="utf-8")
        print(f"Wrote: {out_path}")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY
