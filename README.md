# KCSC Standard MCP

건설 구조계산서 검토를 위한 Claude용 MCP 서버입니다.

이 서버로 할 수 있는 일:

- 엑셀 / PDF 구조계산서 읽기
- 적용 KDS / KCS / KCSC 기준 찾기
- 시트별 검토 포인트 정리
- 구조계산서 검토 보고서 초안 작성 보조

## Claude에서 사용하는 방법

Claude의 커스텀 커넥터에 아래처럼 추가합니다.

- 이름: `kdh-standard-mcp`
- URL: `https://kdh-standard-mcp.onrender.com/mcp?oc=YOUR_KCSC_API_KEY`

예시:

```text
https://kdh-standard-mcp.onrender.com/mcp?oc=honggildong
```

`YOUR_KCSC_API_KEY` 부분에는 본인이 발급받은 KCSC API 키를 넣으면 됩니다.

## 연결 후 이렇게 쓰면 됩니다

예시 질문:

- "이 PDF 구조계산서 검토해줘"
- "적용 기준부터 정리해줘"
- "오류 가능성 있는 부분 먼저 찾아줘"
- "보고서 형식으로 정리해줘"
- "풍하중 기준 적용이 맞는지 봐줘"
- "누락된 계산 결과가 있는지 찾아줘"

## 이 서버가 Claude에 주는 기능

- 계산서 텍스트 추출
- 시트별 검토 패키지 생성
- KDS / KCS 기준 조회
- 상세 보고서용 프롬프트 제공

즉, Claude가 계산서 내용을 읽고 기준을 대조해서 더 구조적으로 답변할 수 있게 도와줍니다.

## 추천 사용 흐름

1. 계산서 파일을 Claude에 올립니다.
2. "적용 기준부터 정리해줘"처럼 먼저 전체 구조를 보게 합니다.
3. 그다음 "검토 보고서 형식으로 써줘"라고 요청합니다.
4. 필요하면 특정 항목만 다시 확인합니다.

예:

- "활하중 적용값이 맞는지 다시 봐줘"
- "앵커볼트 규격 불일치가 있는지 확인해줘"
- "수정·보완 필요 사항만 표로 정리해줘"

## 자주 쓰는 요청 예시

- "계산서 전체를 기준 검토 관점으로 요약해줘"
- "적합 / 검토필요 / 부적합으로 나눠줘"
- "페이지 근거를 붙여서 써줘"
- "최종 검토의견만 따로 정리해줘"
- "보고서 형식 표로 만들어줘"

## 필요한 것

- Claude
- KCSC API 키
- 커넥터 URL

## 예시 설정 파일

[claude_desktop_config.example.json](/c:/Users/user/PycharmProjects/kdh-standard-mcp/claude_desktop_config.example.json:1)
