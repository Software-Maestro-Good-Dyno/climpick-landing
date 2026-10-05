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
- 개인정보처리방침은 시행 7일 전까지, 이용자에게 불리한 약관 변경은 시행 30일 전까지 알려야 합니다.
- 운영자명은 "굿다이노팀"으로 통일합니다.

---

© 2026 Software Maestro Good Dyno
