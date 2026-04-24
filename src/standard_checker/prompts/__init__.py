SYSTEM_PROMPT_EXTRACTOR = """당신은 건설 구조 계산서를 분석하여 데이터를 정형화하는 전문 데이터 엔지니어입니다.
문맥을 추론하거나 계산이 맞는지 판단하지 마세요. 문서에 명시된 텍스트와 수식을 그대로 구조화하는 것만이 당신의 역할입니다.
단, 시트 간 연결 추론에 필요한 부재명·위치·하중케이스·검토단계 같은 문맥 라벨은 원문 표현을 근거로 최대한 분리해 기록하세요.
반드시 JSON만 반환하고, 설명 문장이나 ```코드 블록```은 사용하지 마세요."""

SYSTEM_PROMPT_AUDITOR = """당신은 구조 계산서 내부의 논리적 모순을 찾아내는 QA 엔지니어입니다.
추출된 데이터 내에서 '동일한 변수의 값이 다르게 적용되었는지', '입력값과 수식의 관계가 이상한지'만 검토합니다. 외부 기준(KDS/KCS)은 신경 쓰지 마세요.
반드시 JSON만 반환하고, 설명 문장이나 ```코드 블록```은 사용하지 마세요."""

SYSTEM_PROMPT_CROSS_AUDITOR = """당신은 여러 시트로 구성된 구조 계산서 묶음을 가로질러 정합성을 검증하는 QA 엔지니어입니다.
서로 다른 시트가 동일한 변수·기준 코드·부재명을 다르게 기입했는지, 인용 기준이 시트마다 충돌하는지를 찾아냅니다.
또한 충돌이 아니더라도 같은 부재/변수/계산 흐름으로 이어지는 시트 간 연결 관계를 찾아야 합니다.
외부 KDS/KCS 적합성은 신경 쓰지 말고 시트 간 일관성만 점검하세요.
반드시 JSON만 반환하고, 설명 문장이나 ```코드 블록```은 사용하지 마세요."""

SYSTEM_PROMPT_DEEP_REVIEWER = """당신은 한국건설기준(KDS/KCS) 전문 검토 엔지니어입니다.
주어진 계산서 데이터와 실제 기준 조항을 정밀 대조합니다. 수치 근거를 명확히 제시하고 논리적 단계를 거쳐 판정하세요.
반드시 JSON만 반환하고, 설명 문장이나 ```코드 블록```은 사용하지 마세요."""

EXTRACT_CHECKPOINTS_PROMPT = """아래 건설 계산서에서 설계기준 검토에 필요한 항목들을 구조적으로 추출하세요.
입력에는 각 행마다 "[R<행번호>]" 접두사가 있으니, 각 항목이 등장하는 원본 행 번호를 반드시 source_row에 숫자로 기록하세요.
여러 행에 걸쳐 있으면 대표 행 번호 하나를 선택하세요.
계산이 맞는지 판단하지 말고, 문서에 명시된 입력값·수식·결과·인용 기준을 그대로 추출만 하세요.
입력 끝에 "[표 구조 해석 보조]" 블록이 있으면, 이는 헤더 행과 값 행이 분리된 표를 열 기준으로 재구성한 key=value 힌트입니다. 행 단위 텍스트보다 이 블록의 열 대응 관계를 우선 참고하세요.
예: `[R5~R6 표 해석] fck=27 MPa; fy=400 MPa`는 R5의 fck/fy 헤더와 R6의 값을 열 기준으로 대응시킨 것입니다.
`[R10~R20 표 구조]` 블록은 긴 표의 열 제목과 일부 행을 보존한 것입니다. PM 상관도, 핵심 파라미터, 부재력 검토처럼 열이 많은 표는 이 구조 블록에서 열 이름(C1, C2 또는 실제 헤더)과 값의 대응을 읽으세요.

[시트명]
{sheet_name}

[계산서 내용 (행번호 포함)]
{sheet_content}

추출 규칙:
1. design_inputs: 재료강도(fck·fy·Es 등), 하중, 단면 치수, 피복두께 등 설계 입력값
2. applied_formulas: 계산에 사용된 중요 수식 (예: Vc = 1/6 * sqrt(fck) * bw * d). target_variable은 수식의 결과 기호.
3. calculation_results: 응력·처짐·균열폭·단면력 등 계산 결과값. 허용값과의 비교가 있으면 함께 기록
4. referenced_standards: 계산서에 명시된 기준 코드(KDS/KCS) 번호와 조항
5. check_conditions: "이상·이하·이내" 등 기준과 비교가 필요한 허용 조건

연결성 메타데이터 규칙:
- 모든 항목에는 가능한 경우 element(부재/대상: 보, 슬래브, 벽체, 기초 등), member(부재명: B1, W1 등), location(층/위치), load_case(하중 조합/시공 단계), stage(입력/계산/검토/결과), unit(단위), normalized_value(숫자+단위를 정리한 값), source_row를 포함하세요.
- 원문에 없으면 빈 문자열 "" 또는 null을 쓰세요. 지어내지 마세요.
- symbol은 fck, fy, Vu, Vc처럼 비교 가능한 표준 표기로 최대한 통일하세요. 원문 표기는 value 또는 context에 보존하세요.
- 같은 시트 안에서 다른 항목이 이어질 때 depends_on에 관련 symbol 목록을 기록하세요.

JSON만 반환:
{{
  "design_inputs": [
    {{"name": "항목명", "symbol": "기호", "value": "값 및 단위", "normalized_value": "정규화 값", "unit": "단위", "context": "적용 부재/단계", "element": "부재/대상", "member": "부재명", "location": "층/위치", "load_case": "하중케이스", "stage": "입력", "depends_on": [], "source_row": 12}}
  ],
  "applied_formulas": [
    {{"target_variable": "결과 기호", "formula": "사용된 수식 텍스트", "context": "적용 맥락", "element": "부재/대상", "member": "부재명", "location": "층/위치", "load_case": "하중케이스", "stage": "계산", "depends_on": ["입력 symbol"], "source_row": 24}}
  ],
  "calculation_results": [
    {{"name": "결과명", "symbol": "기호", "value": "계산값 및 단위", "normalized_value": "정규화 값", "unit": "단위", "limit": "허용값(있으면)", "context": "검토 맥락", "element": "부재/대상", "member": "부재명", "location": "층/위치", "load_case": "하중케이스", "stage": "결과", "depends_on": ["입력/수식 symbol"], "source_row": 34}}
  ],
  "referenced_standards": [
    {{"code": "기준코드(예: KDS 24 14 21)", "clause": "조항번호", "context": "적용 맥락", "element": "부재/대상", "member": "부재명", "location": "층/위치", "load_case": "하중케이스", "stage": "기준인용", "source_row": 7}}
  ],
  "check_conditions": [
    {{"description": "조건 설명", "value": "적용값", "limit": "한계값(있으면)", "context": "검토 맥락", "element": "부재/대상", "member": "부재명", "location": "층/위치", "load_case": "하중케이스", "stage": "검토조건", "source_row": 41}}
  ]
}}"""

AUDIT_INTERNAL_PROMPT = """아래는 계산서에서 추출된 설계 입력값, 적용 수식, 결과값 데이터입니다.
외부 설계기준(KDS/KCS)은 무시하고, 문서 내부의 정합성만 점검하세요.

[시트명] {sheet_name}

[추출 데이터 JSON]
{extracted_json_data}

수행 작업:
1. Variable Collision (변수 충돌): 동일한 기호(symbol)를 가진 변수가 문서 내에서 서로 다른 값을 가지고 있는지 확인하세요.
   (예: 12행 fck=30, 45행 fck=27 → 충돌)
2. Logical Mismatch (논리적 오류): 단위가 명백히 호환되지 않거나, 같은 시트 안에서 입력값과 결과값이 논리적으로 모순되는지 확인하세요.
   - 단, applied_formulas의 수식에 등장하는 변수가 현재 시트의 design_inputs에 없다는 이유만으로 오류로 판단하지 마세요.
   - 구조 계산서는 별도 "변수", "입력값", "설계조건" 시트의 값을 계산 시트에서 참조하는 경우가 많습니다. 이런 경우는 시트 간 감사에서 연결성으로 판단할 대상입니다.
   - 현재 시트 안에 입력값이 직접 없으면 High 오류가 아니라, 필요한 경우 "External Reference Needed" 성격의 Medium 이슈로만 기록하세요.

판정 가이드:
- severity: "High" = 결과값이 명백히 달라질 충돌/오류, "Medium" = 표기·맥락 차이일 가능성도 있는 경우
- 문제가 전혀 없으면 internal_issues는 빈 배열로 두고 is_consistent를 true로 두세요.

JSON만 반환:
{{
  "internal_issues": [
    {{
      "issue_type": "Variable Collision 또는 Logical Mismatch",
      "severity": "High 또는 Medium",
      "description": "발견된 문제 상세 설명 (수치/기호 포함)",
      "related_symbols": ["fck"],
      "related_rows": [12, 45]
    }}
  ],
  "is_consistent": true
}}"""

CROSS_SHEET_AUDIT_PROMPT = """아래는 동일한 계산서 파일에 포함된 여러 시트의 추출 데이터입니다.
각 시트는 독립적으로 추출되었으나, 같은 프로젝트의 일부이므로 변수·기준·부재 정보는 일관되어야 합니다.

[시트별 추출 데이터 JSON]
{multi_sheet_data}

[Python 결정적 사전 검사 결과 (참고)]
{deterministic_findings}

수행 작업:
1. Cross Sheet Link Discovery: 같은 부재/위치/하중케이스/변수/계산 흐름으로 이어지는 항목들을 cross_sheet_links에 기록하세요. 충돌이 없어도 중요한 연결이면 기록하세요.
   - 특히 "변수", "입력값", "설계조건" 성격의 시트에 정의된 값이 다른 계산/검토 시트에서 사용되는 구조는 정상적인 input_to_result 연결일 수 있습니다.
   - 계산 시트에 값이 직접 반복 기재되지 않고 변수 시트 값을 참조하는 형태라면, 이를 곧바로 "입력값 누락" 또는 오류로 판단하지 마세요.
2. Variable Conflict Across Sheets: 동일한 기호(symbol)가 시트마다 다른 값을 가지는지 확인하세요.
   - 단, element/member/location/load_case가 명백히 다르면 충돌이 아닐 수 있으므로 cross_sheet_links에는 연결로 남기고 issue를 "none" 또는 "context_diff"로 두세요.
3. Standard Code Conflict: 같은 종류의 검토(예: 전단)에 대해 시트마다 다른 KDS/KCS 코드를 인용하는지 확인하세요.
4. Naming Inconsistency: 동일 부재나 변수에 대해 시트별로 다른 표기(예: fck vs f_ck, B1 vs Beam-1)를 사용하는지 확인하세요.
5. Result Discrepancy: 한 시트의 입력값이 다른 시트의 결과로 이어지는 흐름에서 값이 끊기거나 변형되었는지 확인하세요.

오류로 보지 말아야 하는 경우:
- 변수/입력 시트에 b, d, h, fck, fy, As, Mu 같은 값이 있고 계산 시트가 그 값을 참조해 계산하는 경우는 정상적인 input_to_result 연결입니다.
- 계산 시트에 값이 비어 있거나 직접 표시되지 않아도, linked_items 안에 참조 원천 시트의 값이 있으면 "누락" 이슈로 만들지 말고 cross_sheet_links로만 기록하세요.
- 실제 이슈는 같은 대상의 원천값과 사용값이 서로 다르거나, 참조해야 할 원천값이 어디에도 없을 때만 만드세요.

판정 가이드:
- severity: "High" = 결과·판정에 영향이 명확한 충돌, "Medium" = 표기·맥락 차이 가능성
- 실제 문제가 없으면 cross_sheet_issues는 빈 배열로 두고 is_consistent를 true로 두세요.

JSON만 반환:
{{
  "cross_sheet_links": [
    {{
      "subject": "연결 대상 (예: 벽체 fck, B1 전단검토)",
      "relationship": "same_element_same_variable 또는 input_to_result 또는 source_to_calculation 또는 same_standard_family 또는 context_diff",
      "confidence": "High 또는 Medium 또는 Low",
      "issue": "none 또는 value_conflict 또는 missing_reference 또는 naming_inconsistency 또는 context_diff",
      "reason": "왜 연결된다고 판단했는지, 충돌이면 왜 문제인지",
      "linked_items": [
        {{"sheet": "시트명1", "symbol": "fck", "value": "37 MPa", "element": "벽체", "member": "W1", "location": "B1F", "load_case": "", "source_row": 12}},
        {{"sheet": "시트명2", "symbol": "fck", "value": "40 MPa", "element": "벽체", "member": "W1", "location": "B1F", "load_case": "", "source_row": 45}}
      ]
    }}
  ],
  "cross_sheet_issues": [
    {{
      "issue_type": "Variable Conflict 또는 Standard Code Conflict 또는 Naming Inconsistency 또는 Result Discrepancy",
      "severity": "High 또는 Medium",
      "subject": "충돌 대상 (변수 기호 또는 코드 또는 부재명)",
      "description": "발견된 문제 상세 설명 (수치/기호 포함)",
      "occurrences": [
        {{"sheet": "시트명1", "value": "해당 시트에서의 값/표기", "element": "부재/대상", "member": "부재명", "location": "층/위치", "source_row": 12}},
        {{"sheet": "시트명2", "value": "해당 시트에서의 값/표기", "element": "부재/대상", "member": "부재명", "location": "층/위치", "source_row": 45}}
      ],
      "suggestion": "권고 조치"
    }}
  ],
  "is_consistent": true
}}"""

DEEP_COMPARE_PROMPT = """아래는 내부 정합성 검증을 마친 계산서 데이터와 적용 설계기준의 실제 조항 내용입니다.
각 검토 항목(checkpoint)의 source_row 값은 원본 엑셀 시트의 행번호이므로, 대응 review에 반드시 동일한 source_row를 포함하세요.
source_row를 특정하기 어려우면 해당 항목의 source_row를 그대로 사용하거나 null을 쓰세요.

[시트명] {sheet_name}

[계산서 검토 항목 (행번호 포함)]
{checkpoints_section}

[내부 정합성 감사 결과]
{audit_section}

[적용 설계기준 실제 조항 내용]
{standards_content}

수행 작업:
1. 각 검토 항목마다 대응하는 기준 조항을 찾아 수치를 직접 비교하고 적합성을 판단하세요.
2. 각 review마다 reasoning_steps에 사고 과정(단계별 수치 비교)을 한국어로 간결히 명시하세요.
3. 기준 조항 중 계산서에서 누락된 중요 검토 항목을 unchecked_clauses에 기록하세요.
4. 내부 감사에서 High severity 충돌이 있는 변수와 관련된 검토는 judgment를 "검토필요"로 두고 reason에 충돌 사실을 명시하세요.
5. 보고서에 그대로 넣을 수 있도록 reason은 최소 2문장 이상으로 작성하고, suggestion은 실무자가 다음 조치를 알 수 있게 구체적으로 작성하세요.
6. report_comment에는 보고서용 검토 의견을 2~4문장으로 작성하세요. 단순 반복이 아니라 적용 기준, 계산서 위치, 판단 근거, 후속 확인 필요 여부를 포함하세요.

판정 기준:
- "적합": 계산서 값이 기준을 명확히 충족 (수치 근거 제시)
- "부적합": 계산서 값이 기준 위반 (수치 근거 제시)
- "검토필요": 계산서 정보만으로 판단 불가하거나 내부 충돌이 있는 경우

[중요] 구조 공학의 실무적 허용 오차(Tolerance):
- 한계값과 계산값의 차이가 3% 이내이면 "적합"으로 판정하세요.
- error_margin_percent에는 (|계산값-한계값| / 한계값 * 100)을 소수점 둘째자리까지 기록하고, 계산이 불가능하면 null을 쓰세요.

JSON만 반환:
{{
  "reviews": [
    {{
      "checkpoint": "검토 항목명 및 값 (예: 콘크리트 강도 fck = 30 MPa)",
      "sheet_name": "{sheet_name}",
      "source_row": 34,
      "standard_code": "기준코드 (예: KDS 14 20 10)",
      "standard_clause": "조항번호 (예: 4.2.1)",
      "standard_requirement": "기준 요건 (수치 포함, 예: fck ≥ 24 MPa)",
      "calculated_value": "계산서 적용값 (예: fck = 30 MPa)",
      "reasoning_steps": [
        "1. 계산서 적용값 fck = 30 MPa (행 34)",
        "2. KDS 조항 요구조건: fck ≥ 24 MPa",
        "3. 30 ≥ 24 이므로 조건 만족 (오차율 25.00%)"
      ],
      "judgment": "적합 또는 부적합 또는 검토필요",
      "error_margin_percent": 25.00,
      "reason": "판정 근거 (수치 비교 포함)",
      "suggestion": "개선 제안 또는 null",
      "report_comment": "보고서용 상세 검토 의견"
    }}
  ],
  "unchecked_clauses": [
    {{
      "standard_code": "기준코드",
      "clause": "조항번호",
      "title": "조항 제목",
      "reason": "계산서에서 확인 불가한 이유",
      "suggestion": "추가 검토 권고 내용"
    }}
  ],
  "summary": "전체 검토 요약 (예: 총 5개 항목 - 적합 3건, 검토필요 2건)"
}}"""
