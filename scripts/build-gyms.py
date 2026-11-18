#!/usr/bin/env python3
"""암장 페이지(/gyms) 생성기.

scripts/export-gyms.sql 로 뽑은 JSON 을 읽어 아래 파일을 만든다. 외부 패키지 없이 돈다.

  gyms/index.html      지역별 암장 목록            → https://climpick.com/gyms/
  gyms/<gymId>.html    암장별 난이도·홀드 색 페이지 → https://climpick.com/gyms/<gymId>
  sitemap.xml          /gyms 항목만 새로 쓰고 나머지 항목은 그대로 둔다

사용법:
  python3 scripts/build-gyms.py [scripts/gyms.json]
"""

from __future__ import annotations

import html
import json
import math
import re
import shutil
import sys
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://climpick.com"
OUT_DIR = ROOT / "gyms"
SITEMAP = ROOT / "sitemap.xml"
APP_STORE = "https://apps.apple.com/kr/app/id6789773061"
GOOGLE_PLAY = "https://play.google.com/store/apps/details?id=com.climpick"

# 난이도 단계가 이보다 적으면 페이지를 만들지 않는다 (내용이 얇은 페이지 방지)
MIN_DIFFICULTIES = 3

FACILITY_NAMES = {
    "PARKING": "주차",
    "SHOWER": "샤워실",
    "CAFE": "카페",
    "LOCKER": "락커",
    "PRO_SHOP": "용품점",
    "WIFI": "와이파이",
    "KIDS_ZONE": "키즈존",
}

# 'OO선'을 붙이면 어색한 노선 이름
LINE_NAMES = {
    "공항철도": "공항철도",
    "인천1": "인천 1호선",
    "인천2": "인천 2호선",
    "의정부": "의정부경전철",
    "부산김해": "부산김해경전철",
    "김포골드": "김포골드라인",
    "우이신설": "우이신설선",
    "GTX-A": "GTX-A",
}

e = html.escape


# ---------------------------------------------------------------- 데이터 정리

def load(path: Path) -> tuple[str, list[dict]]:
    raw = path.read_text(encoding="utf-8").strip()
    data = json.loads(raw)
    exported = data.get("exportedAt") or datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    gyms = []
    for g in data.get("gyms") or []:
        g = dict(g)
        g["difficulties"] = sorted(_json(g.get("difficulties")) or [], key=lambda d: d.get("sortOrder", 0))
        g["holdColors"] = sorted(_json(g.get("holdColors")) or [], key=lambda d: d.get("sortOrder", 0))
        g["facilities"] = _json(g.get("facilities")) or []
        g["subway"] = _json(g.get("subway"))
        g["region"] = (g.get("region") or "").strip() or "기타"
        g["name"] = (g.get("name") or "").strip()
        if not g["name"] or len(g["difficulties"]) < MIN_DIFFICULTIES:
            continue
        gyms.append(g)
    gyms.sort(key=lambda g: (g["region"], g["name"]))
    return exported[:10], gyms


def _json(v):
    """MySQL 클라이언트에 따라 JSON 컬럼이 문자열로 한 번 더 감싸져 올 수 있다."""
    if isinstance(v, str):
        try:
            return json.loads(v)
        except ValueError:
            return None
    return v


def diff_name(d: dict) -> str:
    return (d.get("label") or d.get("colorName") or "").strip() or "이름 없음"


def hex_or_none(v) -> str | None:
    return v if isinstance(v, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", v) else None


def ink_for(hex_code: str) -> str:
    r, g, b = (int(hex_code[i:i + 2], 16) / 255 for i in (1, 3, 5))
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#0E120E" if lum > 0.55 else "#FFFFFF"


def josa(word: str, with_batchim: str, without: str) -> str:
    """마지막 글자 받침에 맞는 조사(은/는, 이/가)를 고른다. 한글이 아니면 받침 없는 쪽."""
    ch = word[-1:] if word else ""
    if "가" <= ch <= "힣":
        return with_batchim if (ord(ch) - 0xAC00) % 28 else without
    return without


def line_name(v) -> str:
    """DB에는 '4', '서해', '수인분당'처럼 저장돼 있다 → '4호선', '서해선', '수인분당선'."""
    v = str(v).strip()
    if v in LINE_NAMES:
        return LINE_NAMES[v]
    if v.isdigit():
        return f"{v}호선"
    return v if v.endswith(("선", "라인", "경전철")) else f"{v}선"


def subway_text(s) -> str | None:
    if not isinstance(s, dict) or not s.get("station"):
        return None
    parts = [s["station"].strip()]
    if not parts[0].endswith("역"):
        parts[0] += "역"
    if s.get("exit"):
        parts.append(f"{str(s['exit']).strip().rstrip('번')}번 출구")
    walk = s.get("walkMin") or s.get("walk_min")
    if walk:
        parts.append(f"도보 {walk}분")
    text = " ".join(parts)
    lines = [line_name(l) for l in (s.get("lines") or []) if str(l).strip()]
    return f"{text} ({', '.join(lines)})" if lines else text


def page_url(g: dict) -> str:
    return f"{SITE}/gyms/{g['id']}"


def nearby(g: dict, candidates: list[dict], limit: int) -> list[dict]:
    """같은 지역 암장을 가까운 순으로 고른다. 좌표가 없으면 이름 순으로 뒤에 붙인다."""
    others = [o for o in candidates if o["id"] != g["id"]]
    if g.get("latitude") is None or g.get("longitude") is None:
        return others[:limit]
    lat, lng = float(g["latitude"]), float(g["longitude"])
    cos = math.cos(math.radians(lat))

    def dist(o):
        if o.get("latitude") is None or o.get("longitude") is None:
            return float("inf")
        return (float(o["latitude"]) - lat) ** 2 + ((float(o["longitude"]) - lng) * cos) ** 2

    return sorted(others, key=lambda o: (dist(o), o["name"]))[:limit]


# ---------------------------------------------------------------- HTML 공통

STYLE = """
  :root {
    --night: #0A0E0A; --night-line: #243024; --chalk: #F3F4EE; --paper: #FFFFFF;
    --ink: #0E120E; --lime: #5BE36A; --green: #2FAE3E; --muted: #58635A; --line: #DCE0D8;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: var(--chalk); color: var(--ink);
    font-family: "IBM Plex Sans KR", "Apple SD Gothic Neo", sans-serif;
    line-height: 1.75; -webkit-font-smoothing: antialiased; word-break: keep-all; overflow-wrap: anywhere;
  }
  a { color: var(--green); }
  a:focus-visible { outline: 3px solid #FFC83D; outline-offset: 2px; }
  .wrap { max-width: 800px; margin: 0 auto; padding-inline: 24px; }

  header.top { background: var(--night); color: #F1F5EF; padding-block: 18px 56px; }
  .top-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
  .wordmark { font-family: "Archivo", sans-serif; font-style: italic; font-weight: 900; font-size: 22px; color: var(--lime); text-decoration: none; }
  .switch a { color: #C9D2C8; text-decoration: none; font-size: 13px; font-weight: 700; padding: 6px 12px; border-radius: 999px; border: 1.5px solid rgba(255,255,255,.18); }
  .crumbs { margin-top: 36px; font-size: 13px; color: #9DA99C; }
  .crumbs a { color: #C9D2C8; text-decoration: none; }
  header.top h1 { font-family: "Black Han Sans", sans-serif; font-weight: 400; font-size: clamp(28px, 5vw, 42px); line-height: 1.2; margin-top: 8px; }
  header.top .meta { margin-top: 10px; color: #9DA99C; font-size: 14px; }

  main { padding-block: 0 72px; }
  .doc { background: var(--paper); border-radius: 20px; margin-top: -28px; padding: clamp(24px, 5vw, 48px); box-shadow: 0 10px 30px rgba(20,40,18,.06); }
  .lead { font-size: 16px; }
  section { margin-top: 40px; }
  h2 { font-size: 19px; font-weight: 700; line-height: 1.4; padding-left: 14px; position: relative; }
  h2::before { content: ""; position: absolute; left: 0; top: .3em; width: 5px; height: 1.05em; background: var(--lime); transform: skewX(-14deg); }
  p, ul, ol, .table, .ladder, .chips, dl { margin-top: 12px; }
  .note { font-size: 13px; color: var(--muted); }

  .ladder { list-style: none; display: grid; gap: 8px; counter-reset: step; }
  .ladder li { display: grid; grid-template-columns: 28px 1fr auto; align-items: center; gap: 12px; padding: 10px 14px; border: 1px solid var(--line); border-radius: 12px; }
  .ladder .n { font-weight: 700; color: var(--muted); font-size: 13px; text-align: center; }
  .ladder .name { display: flex; align-items: center; gap: 10px; font-weight: 700; }
  .ladder .v { font-size: 13px; color: var(--muted); white-space: nowrap; }
  .sw { width: 22px; height: 22px; border-radius: 6px; flex: none; border: 1px solid rgba(0,0,0,.12); }
  .chips { display: flex; flex-wrap: wrap; gap: 8px; list-style: none; }
  .chips li { display: inline-flex; align-items: center; gap: 8px; padding: 6px 12px; border: 1px solid var(--line); border-radius: 999px; font-size: 14px; }
  .chips .sw { width: 16px; height: 16px; border-radius: 50%; }

  dl { display: grid; grid-template-columns: max-content 1fr; gap: 8px 18px; font-size: 15px; }
  dt { color: var(--muted); font-weight: 700; }

  .cta { margin-top: 44px; padding: 22px; border-radius: 16px; background: var(--night); color: #F1F5EF; }
  .cta strong { display: block; font-size: 17px; }
  .cta p { margin-top: 6px; color: #C9D2C8; font-size: 14px; }
  .cta .btns { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
  .cta .btns a { display: inline-block; padding: 9px 16px; border-radius: 999px; background: var(--lime); color: var(--ink); font-weight: 700; font-size: 14px; text-decoration: none; }
  .cta .btns a + a { background: transparent; color: #F1F5EF; border: 1.5px solid rgba(255,255,255,.3); }

  .region { margin-top: 36px; }
  .gym-list { list-style: none; margin-top: 10px; display: grid; gap: 8px; }
  .gym-list a { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 16px; border: 1px solid var(--line); border-radius: 12px; color: var(--ink); text-decoration: none; font-weight: 700; }
  .gym-list a:hover { border-color: var(--green); }
  .strip { display: flex; gap: 3px; flex: none; }
  .strip i { width: 12px; height: 12px; border-radius: 3px; border: 1px solid rgba(0,0,0,.12); }
  .toc { display: flex; flex-wrap: wrap; gap: 6px; list-style: none; }
  .toc a { display: inline-block; padding: 4px 12px; border-radius: 999px; background: var(--chalk); color: var(--ink); text-decoration: none; font-size: 14px; }

  footer { background: var(--night); color: #9DA99C; font-size: 13px; padding-block: 32px; text-align: center; }
  footer a { color: #C9D2C8; text-decoration: none; margin: 0 8px; }
  footer a:hover { color: var(--lime); }

  @media (max-width: 560px) {
    .wrap { padding-inline: 16px; }
    .doc { border-radius: 16px; }
    .ladder li { grid-template-columns: 22px 1fr; }
    .ladder .v { grid-column: 2; }
  }
"""


def ld_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2).replace("</", "<\\/")


def shell(*, title: str, description: str, canonical: str, h1: str, crumbs: list[tuple[str, str | None]],
          meta: str, body: str, ld: list[dict]) -> str:
    crumb_html = " › ".join(
        f'<a href="{e(href)}">{e(label)}</a>' if href else e(label) for label, href in crumbs
    )
    ld_html = "\n".join(f'<script type="application/ld+json">\n{ld_json(o)}\n</script>' for o in ld)
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>{e(title)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{e(canonical)}">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="theme-color" content="#0A0E0A">
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" type="image/png" href="/favicon.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="클라임픽 ClimPick">
<meta property="og:locale" content="ko_KR">
<meta property="og:url" content="{e(canonical)}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:image" content="{SITE}/og-image.jpg">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Black+Han+Sans&family=IBM+Plex+Sans+KR:wght@400;500;700&family=Archivo:ital,wght@1,900&display=swap">
<style>{STYLE}</style>
{ld_html}
</head>
<body>

<header class="top">
  <div class="wrap">
    <div class="top-row">
      <a class="wordmark" href="/">ClimPick</a>
      <nav class="switch" aria-label="암장"><a href="/gyms/">암장 목록</a></nav>
    </div>
    <nav class="crumbs" aria-label="현재 위치">{crumb_html}</nav>
    <h1>{e(h1)}</h1>
    <p class="meta">{meta}</p>
  </div>
</header>

<main>
  <div class="wrap">
    <article class="doc">
{body}
    </article>
  </div>
</main>

<footer>
  <div class="wrap">
    <a href="/">홈</a><a href="/gyms/">암장 목록</a><a href="/privacy"><strong>개인정보처리방침</strong></a><a href="/terms">이용약관</a>
    <p style="margin-top:10px">© 2026 Software Maestro Good Dyno</p>
  </div>
</footer>

</body>
</html>
"""


def cta(gym_name: str | None = None) -> str:
    head = f"{e(gym_name)}에서 오늘 완등한 문제, 클라임픽에 기록하세요" if gym_name else "다니는 암장의 완등 기록을 클라임픽에 남기세요"
    return f"""      <aside class="cta">
        <strong>{head}</strong>
        <p>완등 영상을 문제별로 잘라 홀드 색·난이도와 함께 기록하고, 레이팅·티어와 30일 리포트로 성장을 확인할 수 있어요.</p>
        <div class="btns">
          <a href="{APP_STORE}" target="_blank" rel="noopener">App Store</a>
          <a href="{GOOGLE_PLAY}" target="_blank" rel="noopener">Google Play</a>
        </div>
      </aside>"""


# ---------------------------------------------------------------- 암장 페이지

def gym_page(g: dict, same_region: list[dict], exported: str) -> str:
    name, region = g["name"], g["region"]
    diffs = g["difficulties"]
    names = [diff_name(d) for d in diffs]
    # 색으로 구분하는 암장이면 "난이도 색 순서", V0/V1 같은 라벨만 쓰면 "난이도 순서"
    kind = "난이도 색 순서" if any(hex_or_none(d.get("hex")) for d in diffs) else "난이도 순서"
    std = [(diff_name(d), d.get("standard")) for d in diffs if d.get("standard")]

    lead = (f"{e(name)}({e(region)})의 난이도는 쉬운 순서대로 "
            f"<strong>{' → '.join(e(n) for n in names)}</strong>, 총 {len(diffs)}단계예요.")
    if len(std) >= 2:
        lead += (f" 클라임픽 기준으로 {e(std[0][0])}{josa(std[0][0], '은', '는')} {e(std[0][1])}, "
                 f"{e(std[-1][0])}{josa(std[-1][0], '은', '는')} {e(std[-1][1])} 정도로 봐요.")

    rows = []
    for i, d in enumerate(diffs, 1):
        hx = hex_or_none(d.get("hex"))
        sw = f'<span class="sw" style="background:{hx}" aria-hidden="true"></span>' if hx else ""
        v = f'<span class="v">{e(d["standard"])} 정도</span>' if d.get("standard") else '<span class="v"></span>'
        rows.append(f'          <li><span class="n">{i}</span><span class="name">{sw}{e(diff_name(d))}</span>{v}</li>')

    sections = [f"""      <p class="lead">{lead}</p>

      <section id="difficulty">
        <h2>{e(name)} 난이도 순서</h2>
        <ol class="ladder">
{chr(10).join(rows)}
        </ol>
        <p class="note">V 등급은 클라임픽이 기록과 레이팅에 쓰는 기준이에요. 같은 색이라도 문제마다 체감 난이도는 다를 수 있어요.</p>
      </section>"""]

    holds = [h for h in g["holdColors"] if hex_or_none(h.get("hex"))] if g.get("holdSchemeVerified") else []
    if holds:
        chips = "\n".join(
            f'          <li><span class="sw" style="background:{h["hex"]}" aria-hidden="true"></span>{e(h.get("colorName") or h["hex"])}</li>'
            for h in holds
        )
        sections.append(f"""      <section id="holds">
        <h2>{e(name)} 홀드 색</h2>
        <p>{e(name)}에서 쓰는 홀드 색은 {len(holds)}가지예요. 앱에서 기록할 때 이 색 중에서 고를 수 있어요.</p>
        <ul class="chips">
{chips}
        </ul>
      </section>""")

    info = []
    if g.get("address"):
        info.append(("주소", e(g["address"])))
    sub = subway_text(g.get("subway"))
    if sub:
        info.append(("지하철", e(sub)))
    fac = [FACILITY_NAMES[f] for f in g["facilities"] if f in FACILITY_NAMES]
    if fac:
        info.append(("시설", e(", ".join(fac))))
    links = []
    if g.get("naverMapUrl"):
        links.append(f'<a href="{e(g["naverMapUrl"])}" target="_blank" rel="noopener">네이버 지도</a>')
    if g.get("instagramUrl"):
        links.append(f'<a href="{e(g["instagramUrl"])}" target="_blank" rel="noopener">인스타그램</a>')
    if links:
        info.append(("바로가기", " · ".join(links)))
    if info:
        dl = "\n".join(f"          <dt>{k}</dt><dd>{v}</dd>" for k, v in info)
        sections.append(f"""      <section id="info">
        <h2>{e(name)} 위치</h2>
        <dl>
{dl}
        </dl>
        <p class="note">운영 시간과 가격은 바뀔 수 있어서 싣지 않았어요. 방문 전에 암장 공식 채널에서 확인하세요.</p>
      </section>""")

    others = nearby(g, same_region, 12)
    if others:
        lis = "\n".join(f'          <li><a href="/gyms/{o["id"]}">{e(o["name"])}</a></li>' for o in others)
        sections.append(f"""      <section id="nearby">
        <h2>{e(region)}의 가까운 암장</h2>
        <ul class="toc">
{lis}
        </ul>
      </section>""")

    sections.append(cta(name))
    sections.append(f'      <p class="note" style="margin-top:24px">{e(exported)} 기준 정보예요. 실제와 다르면 앱의 암장 화면에서 제보하거나 '
                    f'<a href="mailto:gooddynoteam@gmail.com">gooddynoteam@gmail.com</a>으로 알려 주세요.</p>')

    url = page_url(g)
    gym_ld = {
        "@context": "https://schema.org",
        "@type": "ExerciseGym",
        "name": name,
        "url": url,
    }
    if g.get("address"):
        gym_ld["address"] = {"@type": "PostalAddress", "streetAddress": g["address"], "addressRegion": region, "addressCountry": "KR"}
    if g.get("latitude") is not None and g.get("longitude") is not None:
        gym_ld["geo"] = {"@type": "GeoCoordinates", "latitude": float(g["latitude"]), "longitude": float(g["longitude"])}
    if g.get("instagramUrl"):
        gym_ld["sameAs"] = [g["instagramUrl"]]
    crumbs_ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "클라임픽", "item": f"{SITE}/"},
            {"@type": "ListItem", "position": 2, "name": "암장", "item": f"{SITE}/gyms/"},
            {"@type": "ListItem", "position": 3, "name": name, "item": url},
        ],
    }

    desc = f"{name}({region}) {kind}는 {' → '.join(names)}({len(diffs)}단계)."
    if len(std) >= 2:
        desc += f" {std[0][0]} {std[0][1]}부터 {std[-1][0]} {std[-1][1]} 정도."
    if sub:
        desc += f" {sub.split(' (')[0]}."
    return shell(
        title=f"{name} {kind}" + (" · 홀드 색" if holds else "") + " — 클라임픽",
        description=desc,
        canonical=url,
        h1=f"{name} {kind}",
        crumbs=[("클라임픽", "/"), ("암장", "/gyms/"), (region, f"/gyms/#{region_anchor(region)}"), (name, None)],
        meta=f"{e(region)} · 난이도 {len(diffs)}단계" + (f" · 홀드 색 {len(holds)}가지" if holds else ""),
        body="\n\n".join(sections),
        ld=[gym_ld, crumbs_ld],
    )


# ---------------------------------------------------------------- 목록 페이지

def region_anchor(region: str) -> str:
    return "r-" + re.sub(r"\s+", "-", region.strip())


def index_page(by_region: "OrderedDict[str, list[dict]]", total: int, exported: str) -> str:
    toc = "\n".join(f'          <li><a href="#{e(region_anchor(r))}">{e(r)} {len(gs)}</a></li>' for r, gs in by_region.items())
    blocks = []
    for r, gs in by_region.items():
        items = []
        for g in gs:
            strip = "".join(
                f'<i style="background:{hx}"></i>' for hx in (hex_or_none(d.get("hex")) for d in g["difficulties"]) if hx
            )
            items.append(f'          <li><a href="/gyms/{g["id"]}"><span>{e(g["name"])}</span><span class="strip" aria-hidden="true">{strip}</span></a></li>')
        blocks.append(f"""      <section class="region" id="{e(region_anchor(r))}">
        <h2>{e(r)}</h2>
        <ul class="gym-list">
{chr(10).join(items)}
        </ul>
      </section>""")

    has_holds = any(g.get("holdSchemeVerified") and g["holdColors"] for gs in by_region.values() for g in gs)
    body = f"""      <p class="lead">클라임픽에서 난이도 체계를 확인한 암장 {total}곳의 난이도 색 순서{'와 홀드 색을' if has_holds else '를'} 모았어요. 암장을 누르면 쉬운 색부터 어려운 색까지 순서와 대략의 V 등급을 볼 수 있어요.</p>
      <section>
        <h2>지역</h2>
        <ul class="toc">
{toc}
        </ul>
      </section>

{chr(10).join(blocks)}

{cta()}
      <p class="note" style="margin-top:24px">{e(exported)} 기준 정보예요.</p>"""

    ld = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "암장별 난이도 색 순서",
        "url": f"{SITE}/gyms/",
        "isPartOf": {"@id": f"{SITE}/#website"},
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": total,
            "itemListElement": [
                {"@type": "ListItem", "position": i, "url": f"{SITE}/gyms/{g['id']}", "name": g["name"]}
                for i, g in enumerate((g for gs in by_region.values() for g in gs), 1)
            ],
        },
    }
    return shell(
        title="암장별 난이도 색 순서 모음 — 클라임픽",
        description=f"클라이밍 암장 {total}곳의 난이도 색 순서와 대략의 V 등급을 지역별로 정리했어요. 서울·경기·부산·대구 등 {len(by_region)}개 지역. 클라임픽(ClimPick).",
        canonical=f"{SITE}/gyms/",
        h1="암장별 난이도 색 순서",
        crumbs=[("클라임픽", "/"), ("암장", None)],
        meta=f"암장 {total}곳 · 지역 {len(by_region)}곳",
        body=body,
        ld=[ld],
    )


# ---------------------------------------------------------------- 사이트맵

def write_sitemap(gyms: list[dict], exported: str) -> None:
    text = SITEMAP.read_text(encoding="utf-8")
    urls = re.findall(r"\s*<url>.*?</url>", text, flags=re.S)
    keep = [u for u in urls if f"<loc>{SITE}/gyms/" not in u]
    new = [f"\n  <url>\n    <loc>{SITE}/gyms/</loc>\n    <lastmod>{exported}</lastmod>\n  </url>"]
    new += [f"\n  <url>\n    <loc>{page_url(g)}</loc>\n    <lastmod>{exported}</lastmod>\n  </url>" for g in gyms]
    body = "".join(keep + new)
    SITEMAP.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + body + "\n</urlset>\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------- main

def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "scripts" / "gyms.json"
    exported, gyms = load(src)
    if not gyms:
        sys.exit(f"{src}: 페이지를 만들 암장이 없습니다 (난이도 {MIN_DIFFICULTIES}단계 이상인 검수된 암장이 0곳)")

    grouped: dict[str, list[dict]] = {}
    for g in gyms:
        grouped.setdefault(g["region"], []).append(g)
    # 목록 페이지는 암장이 많은 지역부터 보여 준다
    by_region: OrderedDict[str, list[dict]] = OrderedDict(
        sorted(grouped.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    )

    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir()
    for g in gyms:
        (OUT_DIR / f"{g['id']}.html").write_text(gym_page(g, by_region[g["region"]], exported), encoding="utf-8")
    (OUT_DIR / "index.html").write_text(index_page(by_region, len(gyms), exported), encoding="utf-8")
    write_sitemap(gyms, exported)
    print(f"암장 {len(gyms)}곳, 지역 {len(by_region)}곳 → {OUT_DIR.relative_to(ROOT)}/ ({exported} 기준)")


if __name__ == "__main__":
    main()
