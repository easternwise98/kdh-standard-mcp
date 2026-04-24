# KCSC Standard MCP

국내 건설 계산서 검토를 위한 MCP 서버입니다.  
엑셀/ PDF 계산서를 파싱하고, KCSC/KDS/KCS 기준 문구를 조회해 AI 클라이언트가 검토에 필요한 근거를 바로 사용할 수 있게 해줍니다.

이 저장소는 `Claude Desktop`, `Cursor`, `Windsurf` 같은 MCP 클라이언트에서 바로 연결할 수 있는 **Python 기반 stdio MCP 서버** 패키지입니다.

## 무엇을 해주는가

이 서버는 직접 법률/기준 검토 결론을 생성하는 LLM 서버가 아닙니다. 역할은 아래에 집중됩니다.

- 엑셀 계산서 파싱
- PDF 계산서 파싱
- 시트별 검토용 입력 패키지 생성
- KCSC/KDS/KCS 코드 목록 조회
- KCSC/KDS/KCS 상세 기준 문구 조회

즉, **이 MCP 서버는 자료를 정리하고 근거를 수집**합니다.  
최종 판단과 설명은 Claude 같은 **호스트 AI 모델이 현재 대화 안에서 수행**합니다.

## 이런 경우에 적합합니다

- 구조/건축 계산서를 AI로 1차 검토하고 싶은 경우
- 엑셀 시트별 계산 근거와 기준 문구를 함께 보고 싶은 경우
- KCSC/KDS/KCS 기준 조회를 AI 도구로 연결하고 싶은 경우
- 사내 검토 보조용 MCP 서버를 배포하고 싶은 경우

## 포함된 기능

현재 패키지에는 아래 기능이 포함되어 있습니다.

- `parse_excel_sheets`
  - 엑셀 또는 PDF를 파싱해서 시트/페이지별 텍스트를 반환
- `review_excel_by_sheet`
  - 검토용 패키지 생성
  - 추천 기준 코드와 기준 상세 텍스트를 함께 포함 가능
- `analyze_single_sheet`
  - 파일 없이 시트 텍스트만 직접 넣어 검토 패키지 생성
- `kcsc_get_code_list`
  - KCSC/KDS/KCS 코드 목록 조회
- `kcsc_get_code_detail`
  - 특정 KDS/KCS 코드 상세 기준 조회
- `open_dashboard`
  - 대시보드 URL 반환
- `close_dashboard`
  - MCP 서버가 띄운 대시보드 종료
- `analyze_and_push`
  - 대시보드와 함께 검토 패키지 생성

## 먼저 알아둘 점

- 이 서버는 `stdio` 방식 MCP 서버입니다.
- 별도 웹서버 배포가 기본이 아니라, **클라이언트가 로컬 프로세스로 실행**하는 형태입니다.
- KCSC 기준 조회에는 `KCSC_API_KEY`가 필요합니다.
- 대시보드 관련 기능은 루트의 `app.py`를 전제로 합니다.
  - 현재 이 저장소에는 `app.py`가 포함되어 있지 않다면 `open_dashboard`, `analyze_and_push`는 바로 동작하지 않을 수 있습니다.
  - 따라서 일반 사용자는 우선 `parse_excel_sheets`, `review_excel_by_sheet`, `kcsc_get_code_list`, `kcsc_get_code_detail` 중심으로 사용하는 것이 안전합니다.

## 요구 사항

- Python `3.11` 이상
- Windows / macOS / Linux
- KCSC Open API 접근 키

## 설치 방법

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

macOS/Linux라면:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### 3. 패키지 설치

가장 권장하는 방식은 editable 설치입니다.

```powershell
pip install -e .
```

또는 requirements만 설치할 수도 있습니다.

```powershell
pip install -r requirements-mcp.txt
```

다만 MCP 클라이언트에서 실행 명령을 간단히 쓰려면 `pip install -e .` 방식이 더 낫습니다.

## 환경 변수 설정

필수 환경 변수:

- `KCSC_API_KEY`

선택 환경 변수:

- `MCP_DASH_HOST`
- `MCP_DASH_PORT`

PowerShell 예시:

```powershell
$env:KCSC_API_KEY="YOUR_KCSC_API_KEY"
```

프로젝트 루트에 `.env` 파일을 두는 방식도 가능합니다.

```env
KCSC_API_KEY=YOUR_KCSC_API_KEY
MCP_DASH_HOST=127.0.0.1
MCP_DASH_PORT=8060
```

## 로컬 실행 확인

설치가 끝나면 먼저 콘솔에서 서버가 뜨는지 확인합니다.

```powershell
.venv\Scripts\Activate.ps1
kcsc-standard-mcp
```

이 서버는 MCP stdio 서버이므로 일반 프로그램처럼 친절한 콘솔 UI가 뜨지 않아도 이상이 아닙니다.  
실제 사용은 Claude Desktop 같은 MCP 클라이언트가 이 프로세스를 실행하면서 이루어집니다.

## Claude Desktop 연결 방법

Windows 기준 설정 파일 경로:

```text
%APPDATA%\Claude\claude_desktop_config.json
```

설정 예시는 아래와 같습니다.

```json
{
  "mcpServers": {
    "kcsc-standard-mcp": {
      "command": "C:\\Users\\user\\PycharmProjects\\kdh-standard-mcp\\.venv\\Scripts\\kcsc-standard-mcp.exe",
      "env": {
        "KCSC_API_KEY": "YOUR_KCSC_API_KEY"
      }
    }
  }
}
```

핵심 포인트:

- `command`는 실제 설치된 실행 파일 경로를 넣습니다.
- `pip install -e .` 후 생성된 `kcsc-standard-mcp.exe` 경로를 쓰면 가장 명확합니다.
- 기존에 다른 MCP 서버가 있다면 `mcpServers` 안에 항목만 추가하면 됩니다.

설정 저장 후 Claude Desktop을 완전히 종료했다가 다시 실행하세요.

## Cursor / Windsurf 등에서 연결하는 방법

이 서버는 `stdio` 기반이므로, MCP 설정 파일에 같은 방식으로 등록하면 됩니다.

예시:

```json
{
  "mcpServers": {
    "kcsc-standard-mcp": {
      "command": "C:\\Users\\user\\PycharmProjects\\kdh-standard-mcp\\.venv\\Scripts\\kcsc-standard-mcp.exe",
      "env": {
        "KCSC_API_KEY": "YOUR_KCSC_API_KEY"
      }
    }
  }
}
```

클라이언트마다 설정 파일 위치와 필드명은 조금씩 다를 수 있지만, 핵심은 동일합니다.

- 서버 이름 등록
- 실행 명령 지정
- `KCSC_API_KEY` 전달

## 추천 사용 흐름

실사용은 보통 아래 순서로 진행하면 됩니다.

### 흐름 1. 파일 구조 먼저 확인

1. `parse_excel_sheets` 호출
2. 시트 이름과 텍스트 미리보기 확인
3. 검토할 시트 선택

예시 질문:

- "이 엑셀 파일 시트별 내용을 먼저 보여줘"
- "어떤 시트가 구조 계산 핵심인지 먼저 분류해줘"

### 흐름 2. 시트별 검토 패키지 생성

1. `review_excel_by_sheet` 호출
2. `review_inputs` 확인
3. AI가 `claude_review_task` 지시에 따라 직접 검토

예시 질문:

- "1층 보 시트만 검토해줘"
- "이 계산서에서 누락된 공식 결과가 있는지 같이 봐줘"
- "관련 KDS/KCS 기준까지 붙여서 검토해줘"

### 흐름 3. 기준 문구 개별 확인

1. `kcsc_get_code_list`로 코드 후보 탐색
2. `kcsc_get_code_detail`로 특정 기준 본문 확인

예시 질문:

- "철근 관련 KDS 코드 찾아줘"
- "KDS 14 20 10 상세 기준 보여줘"

## 도구별 설명

### `parse_excel_sheets`

엑셀 또는 PDF를 파싱해서 시트/페이지별 텍스트를 반환합니다.

입력:

```json
{
  "file_path": "C:\\path\\to\\file.xlsx"
}
```

이럴 때 사용:

- 어떤 시트를 검토해야 할지 먼저 보고 싶을 때
- PDF가 텍스트로 어느 정도 추출되는지 점검할 때
- 공식 셀, 누락된 결과 셀을 1차 확인할 때

### `review_excel_by_sheet`

실제 검토용 패키지를 생성하는 핵심 도구입니다.

입력 예시:

```json
{
  "file_path": "C:\\path\\to\\file.xlsx",
  "sheet_names": ["기초", "보", "슬래브"],
  "max_codes": 6,
  "include_standard_details": true,
  "per_code_chars": 1800
}
```

주요 반환 항목:

- `claude_review_task`
- `output_schema`
- `review_inputs`
- `recommended_codes`
- `standard_details`
- `missing_formula_results`

이 도구를 쓰면 AI가 검토에 필요한 데이터와 기준 문구를 한 번에 받아볼 수 있습니다.

### `analyze_single_sheet`

파일 없이 텍스트만으로 검토 패키지를 만들 때 사용합니다.

입력 예시:

```json
{
  "sheet_name": "지하층 기초",
  "sheet_text": "직접 붙여넣은 계산서 텍스트",
  "max_codes": 4,
  "include_standard_details": true
}
```

이럴 때 유용합니다.

- 외부 시스템에서 이미 추출한 텍스트를 재사용할 때
- 파일 업로드 없이 빠르게 검토 실험을 할 때

### `kcsc_get_code_list`

KCSC 코드 목록을 가져옵니다.

용도:

- 관련 KDS/KCS 코드 후보 탐색
- 특정 분야 기준 체계를 먼저 확인

### `kcsc_get_code_detail`

특정 코드의 상세 기준 텍스트를 조회합니다.

입력 예시:

```json
{
  "code_type": "KDS",
  "code_no": "142010"
}
```

또는 번호 형식이 공백 포함인 경우에도 클라이언트에서 적절히 다루면 사용할 수 있습니다.

## 실제 질문 예시

아래처럼 자연어로 요청하면 MCP 클라이언트가 적절한 도구를 호출하게 만들 수 있습니다.

- "이 엑셀 파일 시트별로 어떤 내용인지 먼저 정리해줘"
- "구조 계산 관련 시트만 골라서 검토 패키지 만들어줘"
- "누락된 공식 결과 셀이 있으면 표시해줘"
- "철근콘크리트 관련 KDS/KCS 기준도 같이 붙여줘"
- "이 PDF 계산서에서 기준 검토에 필요한 핵심 수치만 뽑아줘"
- "기초 시트만 별도로 검토해줘"

## 배포 방법

이 프로젝트는 보통 아래 두 방식 중 하나로 배포합니다.

### 방법 1. 소스 저장소 배포

가장 간단합니다.

1. Git 저장소에 업로드
2. 사용자가 저장소를 clone
3. `pip install -e .`
4. MCP 클라이언트 설정에 실행 경로 등록

사내 배포나 팀 내부 공유에 가장 적합합니다.

### 방법 2. wheel 패키지 배포

패키지 형태로 배포하려면 빌드 후 배포할 수 있습니다.

```powershell
pip install build
python -m build
```

그러면 `dist/` 아래에 wheel과 sdist가 생성됩니다.  
사용자는 아래처럼 설치할 수 있습니다.

```powershell
pip install kcsc_standard_mcp-0.1.0-py3-none-any.whl
```

이후 MCP 클라이언트 설정에서 설치된 실행 파일을 `command`에 넣으면 됩니다.

## 추천 배포 체크리스트

배포 전 아래 항목을 확인하세요.

- `KCSC_API_KEY` 없이 어떤 기능이 제한되는지 README에 명시했는가
- Python 버전 요구사항이 분명한가
- MCP 클라이언트 설정 예시가 실제 경로 기준으로 검증되었는가
- 인코딩 깨진 문자열이 없는가
- 예제 파일 경로가 실제 운영 환경에 맞는가
- `app.py` 없이도 README가 오해를 주지 않는가

## 자주 발생하는 문제

### 1. `mcp package is required: pip install mcp`

원인:

- 의존성이 설치되지 않음

해결:

```powershell
pip install -e .
```

또는

```powershell
pip install -r requirements-mcp.txt
```

### 2. `KCSC API Key` 관련 오류

원인:

- `KCSC_API_KEY`가 설정되지 않음

해결:

- 환경 변수 설정
- `.env` 파일 작성
- MCP 클라이언트 설정의 `env`에 키 전달

### 3. Claude Desktop에서 서버가 안 뜸

확인할 것:

- `command` 경로가 정확한지
- 가상환경 실행 파일 경로가 맞는지
- 설정 JSON 문법이 맞는지
- 앱을 완전히 재시작했는지

### 4. 대시보드 기능이 동작하지 않음

원인:

- 현재 저장소 루트에 `app.py`가 없을 수 있음

해결:

- 대시보드 앱을 함께 포함해 배포
- 또는 README/운영에서 대시보드 기능을 제외하고 사용

## 프로젝트 구조

주요 파일:

- [pyproject.toml](/c:/Users/user/PycharmProjects/kdh-standard-mcp/pyproject.toml:1)
- [claude_desktop_config.example.json](/c:/Users/user/PycharmProjects/kdh-standard-mcp/claude_desktop_config.example.json:1)
- [src/standard_checker/mcp_server/mcp_server.py](/c:/Users/user/PycharmProjects/kdh-standard-mcp/src/standard_checker/mcp_server/mcp_server.py:1)
- [src/standard_checker/clients/kcsc/kcsc.py](/c:/Users/user/PycharmProjects/kdh-standard-mcp/src/standard_checker/clients/kcsc/kcsc.py:1)
- [src/standard_checker/parsers/excel_parser.py](/c:/Users/user/PycharmProjects/kdh-standard-mcp/src/standard_checker/parsers/excel_parser.py:1)
- [src/standard_checker/parsers/pdf_parser.py](/c:/Users/user/PycharmProjects/kdh-standard-mcp/src/standard_checker/parsers/pdf_parser.py:1)

## 빠른 시작 요약

가장 빠른 연결 순서는 아래입니다.

1. Python 3.11 가상환경 생성
2. `pip install -e .`
3. `KCSC_API_KEY` 준비
4. Claude Desktop 설정에 `kcsc-standard-mcp.exe` 등록
5. 앱 재시작
6. 엑셀/PDF 검토 요청

## 라이선스

필요 시 여기에 라이선스 정보를 추가하세요.

