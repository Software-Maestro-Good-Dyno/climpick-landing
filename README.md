# ClimPick Landing

클라이밍 기록 앱 **클라임픽(ClimPick)** 의 랜딩 페이지와 정책 문서입니다.

- 사이트: https://climpick.com
- App Store: https://apps.apple.com/kr/app/id6789773061
- Google Play: https://play.google.com/store/apps/details?id=com.climpick

## 파일

| 파일 | 주소 | 내용 |
| --- | --- | --- |
| `index.html` | `/` | 랜딩 페이지 |
| `privacy.html` | `/privacy` | 개인정보처리방침 |
| `terms.html` | `/terms` | 이용약관 |
| `delete-account.html` | `/delete-account` | 계정 삭제 안내. Google Play 데이터 보안 양식의 계정 삭제 링크로 쓰는 주소라 이름을 바꾸거나 지우지 말 것. 앱·개발자 이름은 Play 등록정보 그대로(개발자 "굿다이노") 둘 것 |
| `terms-20260911.html` | `/terms-20260911` | 이용약관 2026년 9월 11일판(이전 판, 검색 제외). 본문과 부칙이 링크하니 지우지 말 것 |
| `download.html` | `/download` | QR·공유용 링크. 기기에 맞는 스토어로 리디렉트 (Android → Google Play, iOS → App Store, 그 외 → 랜딩) |
| `gyms/` | `/gyms/`, `/gyms/<암장 ID>` | 암장별 난이도 색 순서 페이지. `scripts/build-gyms.py`가 만드는 파일이라 직접 고치지 말 것 |
| `scripts/` | - | 암장 페이지 생성 스크립트(`export-gyms.sql`, `build-gyms.py`). 아래 "암장 페이지를 다시 만들 때" 참고 |
| `_redirects` | - | Netlify 리디렉트 규칙. `climpick.netlify.app`으로 들어온 요청을 `climpick.com`의 같은 경로로 301 이동 |

빌드 과정이 없는 정적 HTML입니다. 브라우저로 파일을 바로 열어 확인할 수 있습니다. 스크린샷 이미지는 `img/`에 있습니다. `gyms/`만 스크립트로 미리 만들어 커밋해 둡니다(Netlify에서 빌드하지 않습니다).

## 배포

Netlify에 호스팅합니다(`gooddynolimbing@gmail.com` 계정 소유). GitHub `main` 브랜치와 연동돼 있어서 PR을 `main`에 머지하면 자동으로 배포됩니다. 수동 배포가 필요할 때만 아래 명령을 씁니다.

```bash
npx netlify-cli status   # gooddynolimbing 계정으로 로그인됐는지 확인
npx netlify-cli deploy --prod --dir . --site 3c687fe8-ab23-44b2-8d59-a758205b457f
```

## 암장 페이지를 다시 만들 때

`gyms/`는 운영 DB의 암장 데이터를 한 번 뽑아 만든 정적 페이지입니다. 암장 정보가 바뀌었을 때 다시 만듭니다.

1. `scripts/export-gyms.sql`을 운영 DB(`climbing_db`)에서 읽기 전용으로 실행해 결과를 `scripts/gyms.json`으로 저장합니다. 쿼리 맨 위 주석에 실행 명령과 담는 기준이 있습니다. 한글이 깨지지 않도록 `--default-character-set=utf8mb4`를 꼭 붙입니다.
2. `python3 scripts/build-gyms.py`를 실행합니다. `gyms/`를 통째로 새로 만들고 `sitemap.xml`의 `/gyms` 항목도 바꿉니다.
3. `gyms/`와 `sitemap.xml`을 커밋합니다. `scripts/gyms.json`은 커밋하지 않습니다(`.gitignore`).

- 난이도 체계를 관리자가 검수했고(`difficulty_scheme_admin_verified`) 난이도가 3단계 이상인 암장만 페이지를 만듭니다.
- 홀드 색은 홀드 체계도 검수된 암장(`hold_scheme_admin_verified`)만 보여 줍니다.
- 암장 이미지, 블로그 글, 가격, 운영 시간은 싣지 않습니다. 외부에서 수집한 콘텐츠이거나 금방 낡는 정보입니다.

## 정책 문서를 고칠 때

- 문서 안의 시행일과 공고일을 바꿉니다.
- 개인정보처리방침은 시행 7일 전까지, 이용자에게 불리한 약관 변경은 시행 30일 전까지 알려야 합니다.
- 운영자명은 "굿다이노팀"으로 통일합니다.

---

© 2026 Software Maestro Good Dyno
