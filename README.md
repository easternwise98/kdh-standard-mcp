# KCSC Standard MCP

국내 건설 계산서 검토를 위한 원격 MCP 서버입니다. 엑셀/PDF 계산서를 파싱하고, KCSC/KDS/KCS 기준 문구를 조회해 Claude 같은 AI가 검토 근거를 바로 사용할 수 있게 합니다.

이 저장소는 원격 MCP URL 방식만 지원합니다. 사용자는 로컬 `command`가 아니라 공개 URL로 연결합니다.

- `https://your-domain.example.com/mcp`
- Claude.ai 커스텀 커넥터
- Claude Desktop / Cursor / Windsurf 등의 `url` 기반 MCP 설정

## 무엇을 하는 서버인가

이 서버는 별도의 LLM 서버가 아닙니다. 아래 역할만 담당합니다.

- 엑셀 계산서 파싱
- PDF 계산서 파싱
- 시트별 검토 패키지 생성
- KCSC/KDS/KCS 코드 목록 조회
- KCSC/KDS/KCS 상세 기준 조회

최종 판단은 이 MCP 서버를 호출한 호스트 AI 모델이 수행합니다.

## 중요한 변경점

대시보드 기능은 제거했습니다. 대신 MCP 응답 자체에 검토 진행 상황이 잘 보이도록 아래 정보를 포함합니다.

- `progress_overview`
  - 파일 전체 기준 진행 요약
  - 우선 확인해야 할 시트 목록
  - 누락된 공식 결과 개수
  - 다음 단계 안내
- `review_inputs[].progress`
  - 시트별 상태
  - 추천 코드 개수
  - 기준 상세 포함 개수
  - 우선 검토 포인트

즉, 별도 UI 없이도 Claude가 응답 중간에 "어디부터 봐야 하는지" 자연스럽게 설명할 수 있게 설계했습니다.

## 제공 도구

### `parse_excel_sheets`

엑셀 또는 PDF를 파싱해 시트/페이지별 텍스트를 반환합니다.

추가로 아래 정보를 함께 반환합니다.

- `progress_overview`
- 시트별 미리보기
- 공식 셀 목록
- 결과가 비어 있는 공식 셀 목록

### `review_excel_by_sheet`

실제 검토용 패키지를 생성하는 핵심 도구입니다.

반환 정보:

- `claude_review_task`
- `progress_overview`
- `review_inputs`
- `review_inputs[].progress`
- `recommended_codes`
- `standard_details`
- `missing_formula_results`

### `analyze_single_sheet`

파일 없이 시트 텍스트만 직접 넣어 검토 패키지를 만듭니다.

### `kcsc_get_code_list`

KCSC/KDS/KCS 코드 목록을 조회합니다.

### `kcsc_get_code_detail`

특정 KDS/KCS 코드의 상세 기준 문구를 조회합니다.

## 결과 전용 프롬프트

상세 보고서 수준의 결과가 필요하면 MCP Prompt `standardchecker_detailed_report`를 사용하면 됩니다.

이 프롬프트는 아래 목적에 맞춰 작성되어 있습니다.

- 구조계산서 검토 보고서 형식 유지
- 적합 / 부적합 / 검토필요 구분
- 근거 표기 강화
- 수정·보완 필요 사항 표 형식 정리

또한 `review_excel_by_sheet` 응답에는 아래 필드가 함께 포함됩니다.

- `claude_report_task`
- `report_template_markdown`

즉, MCP 클라이언트가 Prompt를 직접 쓰지 않더라도 패키지 응답만으로 동일한 수준의 보고서 초안을 만들 수 있습니다.

## 원격 MCP 방식

이 프로젝트는 Streamable HTTP 기반 Remote MCP 서버로 동작합니다.

- 기본 MCP 엔드포인트: `/mcp`
- 상태 확인 엔드포인트: `/healthz`
- 서버 소개 엔드포인트: `/`

배포 후 사용자가 실제로 넣는 주소는 아래입니다.

```text
https://your-domain.example.com/mcp
```

## 요구 사항

- Python 3.11 이상
- 공개 배포 가능한 서버 환경
- HTTPS 제공 가능한 도메인 또는 호스팅 플랫폼
- `KCSC_API_KEY`

## 환경 변수

필수:

- `KCSC_API_KEY`

원격 서버 실행용:

- `HOST`
- `PORT`
- `MCP_SERVER_PATH`

기본값:

- `HOST=0.0.0.0`
- `PORT=8000`
- `MCP_SERVER_PATH=/mcp`

예시 `.env`:

```env
KCSC_API_KEY=YOUR_KCSC_API_KEY
HOST=0.0.0.0
PORT=8000
MCP_SERVER_PATH=/mcp
```

## 로컬에서 실행해보기

### 1. 저장소 준비

```powershell
git clone <YOUR_REPO_URL>
cd kdh-standard-mcp
```

### 2. 가상환경 생성

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### 3. 패키지 설치

```powershell
pip install -e .
```

### 4. 환경 변수 설정

```powershell
$env:KCSC_API_KEY="YOUR_KCSC_API_KEY"
$env:HOST="0.0.0.0"
$env:PORT="8000"
$env:MCP_SERVER_PATH="/mcp"
```

### 5. 서버 실행

```powershell
kcsc-standard-mcp
```

실행 후 확인:

- `http://localhost:8000/`
- `http://localhost:8000/healthz`
- `http://localhost:8000/mcp`

주의:

- 로컬 주소는 Claude.ai 웹 커넥터에서 바로 쓸 수 없습니다.
- 공개 HTTPS 주소로 배포한 뒤 그 URL을 사용해야 합니다.

## 배포 방식

핵심은 하나입니다.

**공개 HTTPS URL에서 `/mcp` 엔드포인트가 열려 있어야 합니다.**

즉, 최종적으로 사용자에게 아래 주소를 주면 됩니다.

```text
https://your-domain.example.com/mcp
```

배포 절차:

1. 저장소를 서버 또는 호스팅 플랫폼에 올립니다.
2. `pip install -e .` 또는 wheel 설치를 수행합니다.
3. `KCSC_API_KEY`를 환경 변수로 등록합니다.
4. 시작 명령을 `kcsc-standard-mcp`로 지정합니다.
5. 외부 도메인을 연결합니다.
6. `/healthz`와 `/mcp`가 열리는지 확인합니다.

## 연결 방법

### Claude.ai 커스텀 커넥터

커스텀 커넥터 추가 화면에서 아래처럼 입력합니다.

- 이름: `kcsc-standard-mcp`
- 원격 MCP 서버 URL: `https://your-domain.example.com/mcp`

### URL 기반 MCP 설정

`url` 기반 설정을 지원하는 MCP 클라이언트에서는 아래처럼 등록합니다.

```json
{
  "mcpServers": {
    "kcsc-standard-mcp": {
      "url": "https://your-domain.example.com/mcp"
    }
  }
}
```

예시 파일은 [claude_desktop_config.example.json](/c:/Users/user/PycharmProjects/kdh-standard-mcp/claude_desktop_config.example.json:1)에 있습니다.

## 추천 사용 흐름

### 1. 파일 구조 먼저 파악

먼저 `parse_excel_sheets`를 호출합니다.

AI가 아래를 기준으로 응답하게 유도하면 좋습니다.

- 시트별 미리보기 요약
- 누락된 공식 결과가 있는 시트 우선 표시
- 다음에 검토할 시트 추천

예시 질문:

- "이 파일에서 먼저 봐야 할 시트를 우선순위로 정리해줘"
- "누락된 계산 결과가 있는 시트부터 보여줘"

### 2. 검토 패키지 생성

다음으로 `review_excel_by_sheet`를 호출합니다.

이때 AI는 `progress_overview`와 `review_inputs[].progress`를 이용해 아래처럼 응답할 수 있습니다.

- 현재 검토 준비 상태 요약
- 먼저 봐야 할 시트
- 기준 문구가 충분히 붙은 시트와 부족한 시트 구분
- 다음 단계 제안

예시 질문:

- "기초와 보 시트 기준으로 검토 패키지 만들고, 어디부터 보면 좋을지 먼저 설명해줘"
- "결과 누락이 있는 시트를 우선 검토해줘"

### 3. 기준 문구 추가 조회

필요하면 `kcsc_get_code_list`, `kcsc_get_code_detail`을 추가로 사용합니다.

예시 질문:

- "철근콘크리트 관련 KDS 코드 찾아줘"
- "KDS 14 20 10 상세 기준 보여줘"

## 입력 예시

### `review_excel_by_sheet`

```json
{
  "file_path": "/data/sample.xlsx",
  "sheet_names": ["기초", "보", "슬래브"],
  "max_codes": 6,
  "include_standard_details": true,
  "per_code_chars": 1800
}
```

### `kcsc_get_code_detail`

```json
{
  "code_type": "KDS",
  "code_no": "142010"
}
```

## 응답에서 주로 보게 될 필드

### `parse_excel_sheets` 응답

- `progress_overview.status`
- `progress_overview.sheet_count`
- `progress_overview.total_formula_cells`
- `progress_overview.total_missing_formula_results`
- `progress_overview.next_actions`

### `review_excel_by_sheet` 응답

- `progress_overview.attention_sheets`
- `progress_overview.total_missing_formula_results`
- `progress_overview.next_prompt_hint`
- `review_inputs[].progress.status`
- `review_inputs[].progress.top_recommended_codes`
- `review_inputs[].progress.next_actions`

## 운영 체크리스트

- `https://your-domain.example.com/healthz` 가 `200 OK` 인가
- `https://your-domain.example.com/mcp` 경로가 열려 있는가
- `KCSC_API_KEY`가 배포 환경에 정확히 주입됐는가
- 파일 경로 처리 방식이 실제 운영 환경과 맞는가

## 자주 발생하는 문제

### 1. Claude.ai 커넥터에 URL을 넣었는데 연결이 안 됨

확인할 것:

- 공개 인터넷에서 접근 가능한 주소인지
- HTTPS인지
- `/mcp` 경로를 정확히 넣었는지
- 리버스 프록시가 POST, GET, DELETE를 막고 있지 않은지

### 2. KCSC 기준 조회가 실패함

원인:

- `KCSC_API_KEY` 미설정
- 키 값 오입력

### 3. 도구는 뜨는데 응답이 밋밋함

권장 질문 방식:

- "검토 패키지를 만든 뒤 우선순위와 위험 신호를 먼저 요약해줘"
- "시트별 진행 상태를 먼저 설명하고 그다음 본문 검토로 들어가줘"
- "누락 공식 결과가 있는 시트부터 검토해줘"

### 4. 클라이언트에서 도구가 보이지 않음

확인할 것:

- 커넥터 URL에 `/mcp`가 포함돼 있는지
- 서버가 실제로 살아 있는지
- 배포 직후 재기동이 필요한지

## 파일 구조

- [pyproject.toml](/c:/Users/user/PycharmProjects/kdh-standard-mcp/pyproject.toml:1)
- [src/standard_checker/mcp_server/mcp_server.py](/c:/Users/user/PycharmProjects/kdh-standard-mcp/src/standard_checker/mcp_server/mcp_server.py:1)
- [src/standard_checker/clients/kcsc/kcsc.py](/c:/Users/user/PycharmProjects/kdh-standard-mcp/src/standard_checker/clients/kcsc/kcsc.py:1)
- [src/standard_checker/parsers/excel_parser.py](/c:/Users/user/PycharmProjects/kdh-standard-mcp/src/standard_checker/parsers/excel_parser.py:1)
- [src/standard_checker/parsers/pdf_parser.py](/c:/Users/user/PycharmProjects/kdh-standard-mcp/src/standard_checker/parsers/pdf_parser.py:1)
- [claude_desktop_config.example.json](/c:/Users/user/PycharmProjects/kdh-standard-mcp/claude_desktop_config.example.json:1)

## 빠른 시작 요약

1. `pip install -e .`
2. `KCSC_API_KEY` 설정
3. `kcsc-standard-mcp` 실행
4. 공개 HTTPS 도메인에 배포
5. 최종 URL `https://your-domain.example.com/mcp` 생성
6. Claude.ai 커스텀 커넥터 또는 MCP 클라이언트에 해당 URL 등록

## 라이선스

필요 시 라이선스 정보를 추가하세요.
