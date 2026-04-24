# KCSC Standard MCP

건설 구조계산서 검토용 원격 MCP 서버입니다.

이 서버로 할 수 있는 일:

- 엑셀 / PDF 구조계산서 파싱
- 시트별 검토 패키지 생성
- KCSC / KDS / KCS 기준 조회
- Claude가 바로 쓸 수 있는 보고서용 검토 컨텍스트 제공

## Claude에서 쓰는 방법

Claude.ai 커스텀 커넥터에 아래처럼 넣으면 됩니다.

- 이름: `kcsc-standard-mcp`
- URL: `https://your-service.onrender.com/mcp?oc=YOUR_KCSC_API_KEY`

즉, **자기 KCSC API 키를 URL의 `oc` 값으로 넣어서 연결**합니다.

예시:

```text
https://your-service.onrender.com/mcp?oc=honggildong
```

연결 후 Claude에서 바로 물어보면 됩니다.

- "이 PDF 구조계산서 검토해줘"
- "적용 기준부터 정리해줘"
- "보고서 형식으로 결과 써줘"

## 지원하는 API 키 방식

우선순위는 아래와 같습니다.

1. MCP URL 쿼리 `?oc=...`
2. tool 입력의 `api_key`
3. 요청 헤더 `X-KCSC-API-Key`
4. 세션 저장 `set_kcsc_api_key`
5. 서버 환경변수 `KCSC_API_KEY`

Claude.ai에서는 **`?oc=` 방식이 가장 간단**합니다.

## 주요 도구

- `parse_excel_sheets`
- `review_excel_by_sheet`
- `analyze_single_sheet`
- `kcsc_get_code_list`
- `kcsc_get_code_detail`
- `standardchecker_detailed_report` Prompt

## Render 무료 배포

### 1. GitHub에 push

이 저장소를 GitHub에 올립니다.

### 2. Render에서 Web Service 생성

`New +` → `Web Service`

### 3. 아래 값 입력

- Runtime: `Python 3`
- Branch: `main`
- Root Directory: 비움
- Build Command: `pip install .`
- Start Command: `kcsc-standard-mcp`
- Instance Type: `Free`

### 4. 환경변수 추가

- `MCP_SERVER_PATH` = `/mcp`

공용 키 서버로 운영할 때만 아래도 추가:

- `KCSC_API_KEY` = 운영자 키

### 5. 배포 후 확인

예를 들어 Render 주소가 아래라면:

```text
https://kdh-standard-mcp.onrender.com
```

확인 주소:

```text
https://kdh-standard-mcp.onrender.com/healthz
https://kdh-standard-mcp.onrender.com/mcp
```

Claude에는 `/mcp` 주소를 넣습니다.

사용자별 키 방식이면 최종 URL은 이런 형태입니다.

```text
https://kdh-standard-mcp.onrender.com/mcp?oc=YOUR_KCSC_API_KEY
```

## 로컬 실행

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
$env:MCP_SERVER_PATH="/mcp"
kcsc-standard-mcp
```

공용 키로 테스트할 때만:

```powershell
$env:KCSC_API_KEY="YOUR_KCSC_API_KEY"
```

## 예시 설정 파일

[claude_desktop_config.example.json](/c:/Users/user/PycharmProjects/kdh-standard-mcp/claude_desktop_config.example.json:1)

## 파일

- [pyproject.toml](/c:/Users/user/PycharmProjects/kdh-standard-mcp/pyproject.toml:1)
- [render.yaml](/c:/Users/user/PycharmProjects/kdh-standard-mcp/render.yaml:1)
- [src/standard_checker/mcp_server/mcp_server.py](/c:/Users/user/PycharmProjects/kdh-standard-mcp/src/standard_checker/mcp_server/mcp_server.py:1)
