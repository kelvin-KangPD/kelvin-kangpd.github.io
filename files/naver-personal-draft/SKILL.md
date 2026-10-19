---
name: naver-personal-draft
description: 개인 네이버 블로그 글을 사진 폴더와 대략적인 메모만 받아 내 이전 글 말투로 써서, 브라우저(웨일/크롬) 네이버 글쓰기에 사진·캡션·제목까지 넣고 임시저장하는 스킬. "블로그 글 써줘", "이 사진으로 글 만들어줘", "임시저장해줘", 사진 폴더 경로와 메모를 같이 주면 반드시 이 스킬을 쓴다. 발행은 절대 하지 않는다.
---

# 개인 네이버 블로그 임시저장

사진 + 대략적인 메모 → 내 말투로 쓴 글 → 네이버 글쓰기에 넣고 **임시저장**까지. 발행 버튼은 어떤 경우에도 누르지 않는다.

## 0. 원칙

| 원칙 | 내용 |
|---|---|
| 발행 금지 | 「저장」(임시저장)만 누른다. 「발행」「예약 발행」은 건드리지 않는다 |
| 지어내지 않기 | 메모·사진에 없는 가게 이름, 가격, 날짜, 메뉴명은 쓰지 않는다. 꼭 필요하면 본문에 `[확인 필요: ○○]`로 남기고 보고 때 알려 준다 |
| 말투는 내 글에서 | 문체는 `my-blog.md`의 문체 프로필을 따른다. 프로필이 없으면 1장부터 만든다 |
| 묻는 건 최소로 | 블로그 아이디, 「작성 중인 글이 있습니다」 팝업 처리처럼 되돌리기 어려운 것만 묻고, 나머지는 알아서 정한 뒤 보고한다 |

## 1. 처음 한 번: 설정과 문체 프로필

이 스킬 폴더의 `my-blog.md`를 먼저 읽는다. 없으면 만든다.

1. 블로그 아이디(blog.naver.com/**아이디**)를 사용자에게 묻는다.
2. 최근 글 목록을 가져온다 (파워쉘):
   ```powershell
   $id='블로그아이디'; (Invoke-WebRequest -UseBasicParsing "https://blog.naver.com/PostTitleListAsync.naver?blogId=$id&viewdate=&currentPage=1&categoryNo=0&parentCategoryNo=0&countPerPage=30").Content
   ```
   `"logNo":"숫자"`, `"title":"..."`(URL 인코딩, `+`는 공백)을 뽑는다.
3. 최근 글 5편을 브라우저에서 `https://blog.naver.com/PostView.naver?blogId=아이디&logNo=번호`로 열고, 아래 코드로 구조를 읽는다:
   ```js
   () => { const m=document.querySelector('.se-main-container'); const out=[]; m.querySelectorAll('.se-component').forEach(c=>{ const k=(c.className.match(/se-(text|image|imageGroup|quotation|horizontalLine|sticker|oglink|table)\b/)||['?'])[0]; if(k==='se-text'){ c.querySelectorAll('.se-text-paragraph').forEach(p=>out.push('T['+p.className.replace(/se-text-paragraph\s*/,'')+'|'+((p.querySelector('span')||{}).className||'')+'] '+p.textContent)); } else out.push('['+k+'] '+((c.querySelector('.se-caption')||{}).textContent||'').trim()); }); return out.join('\n'); }
   ```
4. 다 읽은 뒤 `my-blog.md`에 아래 표를 채워 저장한다. 글을 10편 정도 더 쓰거나 사용자가 "말투 다시 봐줘"라고 하면 다시 만든다.

| 항목 | 기록할 것 |
|---|---|
| 블로그 아이디 | |
| 어미 | 반말/존댓말, 자주 쓰는 끝맺음(~했어요, ~했다, ~했음 등)과 비율 |
| 시작·끝 | 첫 문장 패턴, 마무리 인사 패턴 |
| 이모지·감탄 | 자주 쓰는 이모지·ㅎㅎ·ㅠㅠ 등과 대략 빈도 |
| 문단 | 한 문단 줄 수, 빈 줄 넣는 습관, 줄바꿈 위치 |
| 정렬·글꼴 | 문단 정렬(가운데/왼쪽, `se-text-paragraph-align-*`), 글꼴·크기(`se-ff-*`, `se-fs*`) |
| 사진 배치 | 사진 1장당 글 몇 줄, 사진 연속 배치 여부, 캡션 사용 여부 |
| 소제목 | 인용구·굵은 글씨·구분선 사용 여부와 모양 |
| 제목 | 길이, 괄호·이모지·장소명 넣는 습관 |
| 예시 문장 | 말투가 잘 드러나는 문장 5개 (그대로 베껴 쓰지 말고 참고만) |

## 2. 입력 받기

사용자가 주는 것: **사진 폴더 경로** + **메모**(대략적인 내용, 순서, 하고 싶은 말).

1. 폴더의 사진을 Read로 직접 본다. 순서는 메모 > 파일명 > 촬영 시각(EXIF) 순으로 정한다.
2. HEIC는 JPG로 바꾼다(`pip install pillow-heif` 후 PIL로 변환). 너무 크면(긴 변 4000px 초과) 긴 변 2560px로 줄인다.
3. 사용자가 위치 노출을 원하지 않으면 EXIF를 지운 사본을 쓴다(`Image.open(p).save(q, exif=b'')`).
4. **업로드용 사본은 반드시 현재 작업 폴더(Claude 세션 폴더) 안에** 만든다. Playwright 업로드는 작업 폴더 밖 파일을 거부한다. 파일명은 `01-키워드.jpg`처럼 순번을 붙인다.

## 3. 글 쓰기

1. 제목 후보 3개를 만들고 하나를 고른다(문체 프로필의 제목 습관 따름).
2. 본문을 HTML 조각으로 쓴다.
   - 문단: `<p>...</p>`, 문단 안 줄바꿈 `<br>`, 빈 줄은 `<p>&nbsp;</p>`(네이버는 문단 여백을 무시한다).
   - 정렬·크기는 프로필대로 `<p style="text-align:center"><span style="font-size:16px">` 식으로 적는다.
   - 사진 자리는 단독 문단으로 `<p>[📸 사진 01 | 캡션: ...]</p>`. 캡션을 안 쓰는 블로그면 `캡션:` 뒤를 비운다.
   - 굵게는 `<b>`, 소제목을 인용구로 쓰는 블로그면 `<blockquote>`, 구분선은 `<hr>`.
   - 링크는 URL만 단독 문단으로(나중에 링크 카드로 바꾼다).
3. 쓴 HTML은 작업 폴더에 `draft.html`로 저장해 둔다(나중에 다시 붙여넣을 수 있게).

## 4. 네이버 글쓰기에 넣기 (Playwright MCP)

브라우저는 CDP(예: `localhost:9222`)로 연결된 웨일/크롬. 시작 전에 `browser_tabs`(list)로 연결부터 확인한다.

### 4-1. 글쓰기 열기
- `browser_tabs`(new)로 `https://blog.naver.com/아이디/postwrite`를 연다.
- 「작성 중인 글이 있습니다」 팝업이 뜨면 **멈추고 사용자에게 묻는다**(확인=이어쓰기, 취소=새 글).
- 화면이 응답 없거나 스크린샷이 시간초과면 탭이 숨겨진 상태다(`document.visibilityState==='hidden'`). `browser_tabs`(select)로 앞으로 가져온다.
- 에디터 문서: `const fr = page.frame({ name: 'mainFrame' }) || page.mainFrame();`

### 4-2. 본문 붙여넣기 (가짜 붙여넣기 이벤트, 클립보드 불필요)
`browser_run_code_unsafe`로 실행. `HTML`에 draft.html의 본문을 넣는다.
```js
async (page) => {
  const HTML = `...draft 본문...`;
  const fr = page.frame({ name: 'mainFrame' }) || page.mainFrame();
  await fr.locator('.se-component.se-text .se-text-paragraph').first().click();
  await page.waitForTimeout(400);
  await fr.evaluate((h) => {
    const ib = [...document.querySelectorAll('iframe')].map(i => { try { return i.contentDocument } catch (e) { return null } }).find(x => x && x.body && x.body.isContentEditable);
    const W = ib.defaultView, dt = new W.DataTransfer();
    dt.setData('text/html', h); dt.setData('text/plain', h.replace(/<[^>]+>/g, ''));
    ib.body.dispatchEvent(new W.ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }));
  }, HTML);
  await page.waitForTimeout(4000);
  return fr.evaluate(() => [...document.querySelectorAll('.se-text-paragraph')].filter(p => p.textContent.includes('📸')).length);
}
```
붙여넣은 blockquote는 따옴표 인용구(인용구 1)로 들어온다. 다른 모양이 필요하면 인용구를 클릭해 뜨는 `button[data-name$="-layout"][data-value="quotation_line"]` 같은 버튼으로 바꾼다.

### 4-3. 사진 넣기 (사진마다 반복)
한 번 실행 = 「캡션이 빈 사진에 캡션 넣기」 + 「다음 📸 자리 지우고 사진 버튼 누르기」. 실행 후 파일 선택 상태가 되면 `browser_file_upload`로 그 순번 파일을 올리고, 다시 같은 코드를 실행한다. `next:"none"`이 나올 때까지.
```js
async (page) => {
  const CAPS = ['캡션1', '캡션2' /* 사진 순서대로, 캡션 안 쓰면 '' */];
  const fr = page.frame({ name: 'mainFrame' }) || page.mainFrame();
  const out = {};
  await page.waitForTimeout(4000); // 직전 업로드 대기 (img src가 svg 자리표시여도 정상)
  const imgs = fr.locator('.se-component.se-image');
  const n = await imgs.count(); out.imgs = n;
  for (let k = 0; k < n; k++) {
    const want = CAPS[k]; if (!want) continue;
    const cap = imgs.nth(k).locator('.se-caption .se-text-paragraph').first();
    const txt = (await cap.textContent()).replace(/[\s​]/g, '');
    if (txt !== '' && txt !== '사진설명을입력하세요.') continue;
    const im = imgs.nth(k).locator('img').first();
    await im.evaluate(e => e.scrollIntoView({ block: 'center' })); await page.waitForTimeout(400);
    const bb = await im.boundingBox();
    await page.mouse.click(bb.x + bb.width / 2, bb.y + bb.height / 2); await page.waitForTimeout(500); // 캡션 칸은 사진을 눌러야 보인다
    await cap.click({ timeout: 5000 }); await page.waitForTimeout(400);
    await page.keyboard.type(want); await page.waitForTimeout(500);
    out['cap' + (k + 1)] = (await cap.textContent()).trim();
  }
  const ph = fr.locator('.se-text-paragraph', { hasText: '[📸 사진 ' }).first();
  if (!(await ph.count())) { out.next = 'none'; return out; }
  out.next = (await ph.textContent()).slice(0, 12);
  const pid = await ph.getAttribute('id');
  await ph.evaluate(e => e.scrollIntoView({ block: 'center' })); await page.waitForTimeout(300);
  const box = await ph.locator('span').last().boundingBox();
  await page.mouse.click(box.x + box.width - 1, box.y + box.height / 2); await page.waitForTimeout(200);
  const left = () => fr.evaluate(id => { const p = document.getElementById(id); return p ? p.textContent.replace(/[\s​]/g, '').length : -1; }, pid);
  for (let i = 0; i < 150 && (await left()) > 0; i++) { await page.keyboard.press('Backspace'); await page.waitForTimeout(20); }
  out.remain = await left(); if (out.remain !== 0) return out;
  const pb = await fr.evaluate(() => { const all = [...document.querySelectorAll('button[data-name="image"]')].filter(x => x.offsetParent); const b = all.find(x => x.getAttribute('data-group') === 'documentToolbar') || all[0]; const r = b.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; });
  await page.mouse.click(pb[0], pb[1]); // 위쪽 툴바 「사진」
  return out;
}
```
- 사진 크기: 사진을 클릭한 뒤 `button[data-name="content-mode-without-pagefull"]` 중 「작게」/「문서 너비」, 또는 `button[data-name="image-resizing"]`(크기 입력, 「모든사진 적용」은 끈 채로)로 프로필에 맞춘다.
- 여러 장을 한 줄로 묶는 블로그(이미지 그룹)라면 해당 사진들을 한 번에 `browser_file_upload`에 넘기고 뜨는 배치 선택에서 고른다.

### 4-4. 제목
```js
async (page) => { const fr = page.frame({ name: 'mainFrame' }) || page.mainFrame();
  const t = fr.locator('.se-documentTitle .se-text-paragraph').first(); const b = await t.boundingBox();
  await page.mouse.click(b.x + 20, b.y + b.height / 2); await page.waitForTimeout(400);
  await page.keyboard.type('제목'); return (await t.textContent()).trim(); }
```

### 4-5. 링크 카드 (URL이 있을 때만)
URL 문단을 4-3과 같은 방식(끝 클릭 → Backspace 반복)으로 비운 뒤, 4-2의 붙여넣기 코드로 `text/plain`과 `<a href>` 형태의 URL만 붙여넣으면 카드가 생긴다. 카드 위에 URL 글자 줄이 하나 더 남으므로 그 문단도 비우고 Backspace를 한 번 더 눌러 빈 줄을 없앤다. 썸네일을 끄려면 카드 썸네일에 마우스를 올린 뒤 `button.se-oglink-thumbnail-delete`를 누른다.

### 4-6. 임시저장
```js
async (page) => { const fr = page.frame({ name: 'mainFrame' }) || page.mainFrame();
  const btn = fr.locator('button[class*="save_btn"]').first(); const label = (await btn.textContent()).trim();
  if (!/저장/.test(label) || /발행/.test(label)) return { error: label };
  const cnt = () => fr.evaluate(() => document.querySelector('[class*="save_btn"]').parentElement.textContent);
  const before = await cnt(); const b = await btn.boundingBox();
  await page.mouse.click(b.x + b.width / 2, b.y + b.height / 2); await page.waitForTimeout(2500);
  return { before, after: await cnt() }; }
```
저장 옆 숫자가 1 늘었으면 성공.

### 자주 막히는 곳

| 증상 | 해결 |
|---|---|
| Shift+Home으로 줄 선택이 안 됨 | 네이버 에디터가 키를 가로챈다. 줄 끝 클릭 + Backspace 반복으로 지운다 |
| locator.click이 계속 대기 | 툴바가 「라이브러리」 같은 사이드 패널에 가려졌거나 애니메이션 중. 패널 X를 누르고, 버튼은 `getBoundingClientRect` 좌표로 `page.mouse.click` |
| 업로드한 사진의 img src가 svg | 정상. 업로드 완료 판단은 몇 초 대기 + 라이브러리/화면 확인으로 |
| 캡션 칸이 안 보임 | 사진을 먼저 클릭해야 나타난다 |
| `browser_file_upload`가 경로 거부 | 사진 사본을 작업 폴더 안에 두고 그 경로를 쓴다 |
| 창 크기가 바뀌어 좌표가 어긋남 | 좌표는 매번 `boundingBox`로 다시 구한다 |

## 5. 마지막 점검과 보고

- 점검: 📸 자리 남은 것 없음, 사진 수 = 계획 수, 캡션 확인, 제목 확인, URL 글자 줄 남은 것 없음, 저장 숫자 +1.
- 보고(짧게): 저장한 제목, 사진 몇 장, `[확인 필요]`로 남긴 부분, 추천 태그 5~10개(태그는 발행 화면에서 넣는 것이라 직접 넣으시라고 안내).
- 발행은 사용자가 직접 한다.
