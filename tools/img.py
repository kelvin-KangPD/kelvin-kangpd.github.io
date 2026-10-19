#!/usr/bin/env python3
"""사진을 블로그용으로 변환한다.

사용: python3 tools/img.py <폴더이름> <원본1> <키워드1> [<원본2> <키워드2> ...]
예:   python3 tools/img.py 20261019-first-shorts a.jpg 촬영-세팅 b.png 편집-화면

결과: images/<폴더이름>/01-촬영-세팅.webp, 02-편집-화면.webp ...
가로 최대 1600px, WEBP, 위치정보(GPS) 등 메타데이터는 모두 지운다.
"""
import sys
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent


def main():
    if len(sys.argv) < 4 or len(sys.argv[2:]) % 2:
        print(__doc__)
        sys.exit(1)
    out_dir = ROOT / "images" / sys.argv[1]
    out_dir.mkdir(parents=True, exist_ok=True)
    pairs = list(zip(sys.argv[2::2], sys.argv[3::2]))
    for i, (src, kw) in enumerate(pairs, 1):
        im = ImageOps.exif_transpose(Image.open(src))
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGB")
        if im.width > 1600:
            im = im.resize((1600, round(im.height * 1600 / im.width)), Image.LANCZOS)
        out = out_dir / f"{i:02d}-{kw}.webp"
        im.save(out, "WEBP", quality=82, method=6)  # exif 미포함 저장
        print(f"/images/{sys.argv[1]}/{out.name}  ({im.width}x{im.height})")


if __name__ == "__main__":
    main()
