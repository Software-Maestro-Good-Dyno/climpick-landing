# ClimPick Landing

클라이밍 기록 앱 **클라임픽(ClimPick)** 의 랜딩 페이지와 정책 문서입니다.

- 사이트: https://climpick.netlify.app
- App Store: https://apps.apple.com/kr/app/id6789773061
- Google Play: https://play.google.com/store/apps/details?id=com.climpick

## 파일

| 파일 | 주소 | 내용 |
| --- | --- | --- |
| `index.html` | `/` | 랜딩 페이지 |
| `privacy.html` | `/privacy` | 개인정보처리방침 |
| `terms.html` | `/terms` | 이용약관 |
| `terms-20260911.html` | `/terms-20260911` | 이용약관 2026년 9월 11일판(이전 판, 검색 제외). 본문과 부칙이 링크하니 지우지 말 것 |
| `privacy-20260911.html` | `/privacy-20260911` | 개인정보처리방침 2026년 9월 11일판(이전 판, 검색 제외). 새 판과 옛 약관이 링크하니 지우지 말 것 |
| `download.html` | `/download` | QR·공유용 링크. 기기에 맞는 스토어로 리디렉트 (Android → Google Play, iOS → App Store, 그 외 → 랜딩) |

빌드 과정이 없는 정적 HTML입니다. 스크린샷 이미지는 `index.html` 안에 base64로 들어 있어서 파일 하나로 동작합니다. 브라우저로 파일을 바로 열어 확인할 수 있습니다.

## 배포

Netlify에 호스팅합니다(`gooddynolimbing@gmail.com` 계정 소유). GitHub `main` 브랜치와 연동돼 있어서 PR을 `main`에 머지하면 자동으로 배포됩니다. 수동 배포가 필요할 때만 아래 명령을 씁니다.

```bash
npx netlify-cli status   # gooddynolimbing 계정으로 로그인됐는지 확인
npx netlify-cli deploy --prod --dir . --site 3c687fe8-ab23-44b2-8d59-a758205b457f
```

## 정책 문서를 고칠 때

- 문서 안의 시행일과 공고일을 바꿉니다.
- 개인정보처리방침은 법정 사전 공지 기간이 없어 바로 시행할 수 있습니다. 바로 시행하는 대신 고치기 전 판을 `privacy-YYYYMMDD.html`로 남겨 적용 기간을 적고, 새 판 "방침의 변경" 절에 바뀐 점 대조표와 이전 판 링크를 둡니다. 다만 이미 받은 정보를 새 목적에 쓰거나 제3자에게 새로 제공하는 일은 공지만으로는 근거가 되지 않아, 따로 동의를 받거나 다른 근거(이용자가 요청한 서비스 제공 등)를 밝혀야 합니다.
- 이용약관은 시행 7일 전까지, 이용자에게 불리한 변경은 시행 30일 전까지 알립니다(약관 제3조).
- 고치기 전 판은 `privacy-YYYYMMDD.html`, `terms-YYYYMMDD.html`로 남깁니다. 이전 판 페이지는 검색 제외(`noindex`)로 두고, `canonical`·`og:url`은 자기 주소를 가리키게 합니다.
- 운영자명은 "굿다이노팀"으로 통일합니다. 사업자 상호 "클라임픽"으로 바꾸는 일은 이용약관 2차 개정(30일 예고와 앱 안내 화면)과 함께 합니다.

---

© 2026 Software Maestro Good Dyno
