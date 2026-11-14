# 어려운 자가 수정 시험 — 오류 100개 x 2 프로그램, AI 4종 (2026-11-11)

- 대상: FastAPI/LangGraph/selffix_demo/hard/<program>_<ai>.py (AI마다 같은 결함 사본, 원본은 *_original.py로 보존)
- 자동 적용: 채점 식을 전부 통과해야 적용되고, 하나라도 실패하면 원래 소스로 되돌린다.
- 오류는 분야 10종 x 10개로 고르게 심었다(분야별 표 참고).

## calc_engine (오류 100개, 채점 식 274개)

| AI | 상태 | 시간(초) | 검증 통과 | 수정안: 고친 오류 | 수정안: 통과 식 | 자동 적용 | 현재 파일: 남은 오류 |
|---|---|---|---|---|---|---|---|
| 원본(오류 100개) | - | - | - | 0/100 | 129/274 | - | 100 |
| Gemini | completed | 387.698 | True | 99/100 | 273/274 | 되돌림 | 1 |
| ChatGPT | completed | 244.549 | True | 100/100 | 274/274 | 적용 | 0 |
| Claude | completed | 1141.113 | True | 98/100 | 272/274 | 적용 | 0 |
| Ollama | timed_out | 3590.129 | False | -/100 | -/274 | 안 함(review not verified) | 100 |

### 분야별 고친 오류 수(수정안 기준, 분야당 10개)

| 분야 | Gemini | ChatGPT | Claude | Ollama |
|---|---|---|---|---|
| 경계값 | 10 | 10 | 10 | - |
| 부호·음수 | 9 | 10 | 9 | - |
| 부동소수·반올림 | 10 | 10 | 10 | - |
| 예외·검증 | 10 | 10 | 10 | - |
| 빈 입력·초기값 | 10 | 10 | 10 | - |
| 상태·부작용 | 10 | 10 | 10 | - |
| 연산 순서·우선순위 | 10 | 10 | 10 | - |
| 파싱·형 변환 | 10 | 10 | 9 | - |
| 조건 논리 | 10 | 10 | 10 | - |
| 공식·상수 | 10 | 10 | 10 | - |

### 오류별 결과(수정안 기준, O=고침 X=못 고침 -=수정안 없음, *=공유 채점 식)

| # | 분야 | 함수 | 심은 오류 | Gemini | ChatGPT | Claude | Ollama |
|---|---|---|---|---|---|---|---|
| 1 | 경계값 | `factorial` | range 끝 누락(n을 곱하지 않음) | O | O | O | - |
| 2* | 경계값 | `primes_up_to` | 체 반복이 sqrt(n)을 포함하지 않음 | O | O | O | - |
| 3 | 경계값 | `primes_up_to` | n 자신이 소수여도 빠짐 | O | O | O | - |
| 4 | 경계값 | `is_prime` | 제곱수(k*k == n)를 소수로 판정 | O | O | O | - |
| 5* | 경계값 | `moving_average` | 마지막 창 누락 | O | O | O | - |
| 6* | 경계값 | `moving_average` | window == len을 거부 | O | O | O | - |
| 7 | 경계값 | `clamp` | low == high를 거부 | O | O | O | - |
| 8 | 경계값 | `format_thousands` | 정확히 3자리일 때 앞에 쉼표 | O | O | O | - |
| 9 | 경계값 | `median` | 짝수 개 가운데 인덱스 밀림 | O | O | O | - |
| 10* | 경계값 | `fibonacci` | 반복 1회 부족 | O | O | O | - |
| 11 | 부호·음수 | `absolute` | 부호 비교 반전 | O | O | O | - |
| 12 | 부호·음수 | `gcd` | b의 절댓값을 안 씀(음수 결과) | O | O | O | - |
| 13 | 부호·음수 | `lcm` | 음수 곱의 절댓값 누락 | O | O | O | - |
| 14 | 부호·음수 | `percent_change` | 음수 기준값에서 부호 뒤집힘 | X | O | X | - |
| 15 | 부호·음수 | `digit_sum` | 음수면 합에 부호를 붙임 | O | O | O | - |
| 16 | 부호·음수 | `is_palindrome_number` | 음수 검사 누락(절댓값으로 판정) | O | O | O | - |
| 17 | 부호·음수 | `to_binary` | 음수 부호 누락 | O | O | O | - |
| 18* | 부호·음수 | `from_binary` | 부호를 결과에 안 곱함 | O | O | O | - |
| 19 | 부호·음수 | `floor_divide` | 음수에서 0 쪽 버림(내림 아님) | O | O | O | - |
| 20 | 부호·음수 | `modulo` | fmod 사용(부호가 a를 따름) | O | O | O | - |
| 21 | 부동소수·반올림 | `round_half_up` | float를 Decimal로 바로 변환(이진 오차) | O | O | O | - |
| 22 | 부동소수·반올림 | `round_half_up` | 은행가 반올림을 같은 이름으로 import | O | O | O | - |
| 23 | 부동소수·반올림 | `truncate` | 음수에서 내림(0 쪽 아님) | O | O | O | - |
| 24 | 부동소수·반올림 | `ceil_divide` | 나누어떨어져도 +1 | O | O | O | - |
| 25 | 부동소수·반올림 | `average_of_two` | 정수 나눗셈 | O | O | O | - |
| 26 | 부동소수·반올림 | `mean` | 정수 나눗셈 | O | O | O | - |
| 27 | 부동소수·반올림 | `km_to_miles` | 근사 상수 1.6 | O | O | O | - |
| 28* | 부동소수·반올림 | `stdev` | 결과를 소수 1자리로 반올림 | O | O | O | - |
| 29 | 부동소수·반올림 | `percent` | 정수 나눗셈 | O | O | O | - |
| 30 | 부동소수·반올림 | `fahrenheit_to_celsius` | 5 // 9 = 0 | O | O | O | - |
| 31 | 예외·검증 | `divide` | 0 검사 누락(ZeroDivisionError) | O | O | O | - |
| 32 | 예외·검증 | `modulo` | 예외 종류가 ZeroDivisionError | O | O | O | - |
| 33 | 예외·검증 | `power` | 정수 지수 검사 누락 | O | O | O | - |
| 34 | 예외·검증 | `power` | 0의 음수 거듭제곱 검사 누락 | O | O | O | - |
| 35 | 예외·검증 | `reciprocal` | 예외 종류가 ArithmeticError | O | O | O | - |
| 36 | 예외·검증 | `round_half_up` | digits 정수 검사 누락 | O | O | O | - |
| 37 | 예외·검증 | `factorial` | 정수 검사 누락(2.0이면 TypeError) | O | O | O | - |
| 38 | 예외·검증 | `weighted_mean` | 음수 가중치 검사 누락 | O | O | O | - |
| 39 | 예외·검증 | `parse_number` | 문자열 검사 누락(AttributeError) | O | O | O | - |
| 40 | 예외·검증 | `km_to_miles` | 음수 거리 검사 누락 | O | O | O | - |
| 41 | 빈 입력·초기값 | `mean` | 빈 목록 검사 누락(ZeroDivisionError) | O | O | O | - |
| 42 | 빈 입력·초기값 | `median` | 빈 목록에 0을 돌려줌 | O | O | O | - |
| 43 | 빈 입력·초기값 | `lcm` | 0 처리 누락(lcm(0,0)에서 0 나누기) | O | O | O | - |
| 44 | 빈 입력·초기값 | `cumulative_sum` | 누적 시작값이 첫 원소 | O | O | O | - |
| 45 | 빈 입력·초기값 | `to_binary` | 0이면 빈 문자열 | O | O | O | - |
| 46 | 빈 입력·초기값 | `from_binary` | 빈 문자열 검사 누락 | O | O | O | - |
| 47* | 빈 입력·초기값 | `fibonacci` | F0이 1로 시작 | O | O | O | - |
| 48 | 빈 입력·초기값 | `moving_average` | window 0 허용(0 나누기) | O | O | O | - |
| 49 | 빈 입력·초기값 | `percent` | whole 0 검사 누락 | O | O | O | - |
| 50 | 빈 입력·초기값 | `percent_change` | old 0 검사 누락 | O | O | O | - |
| 51 | 상태·부작용 | `median` | 입력 목록을 제자리 정렬 | O | O | O | - |
| 52 | 상태·부작용 | `Calculator.__init__` | 넘겨받은 history를 복사하지 않음 | O | O | O | - |
| 53* | 상태·부작용 | `Calculator.undo` | pop 대신 마지막 값만 읽음 | O | O | O | - |
| 54* | 상태·부작용 | `Calculator.memory_recall` | 기록에 이전 값을 안 쌓음 | O | O | O | - |
| 55 | 상태·부작용 | `Calculator.memory_add` | 더하지 않고 덮어씀 | O | O | O | - |
| 56 | 상태·부작용 | `Calculator.memory_clear` | 메모리 대신 현재 값을 지움 | O | O | O | - |
| 57 | 상태·부작용 | `Calculator.apply` | 모르는 연산자를 조용히 무시하고 기록 | O | O | O | - |
| 58* | 상태·부작용 | `mode` | 호출 사이에 집계가 누적(모듈 전역) | O | O | O | - |
| 59 | 상태·부작용 | `Calculator.apply` | 이전 값 대신 새 값을 기록 | O | O | O | - |
| 60* | 상태·부작용 | `evaluate` | 연산자 스택이 모듈 전역(오류 뒤 찌꺼기 남음) | O | O | O | - |
| 61* | 연산 순서·우선순위 | `evaluate` | 같은 순위를 오른쪽부터 계산 | O | O | O | - |
| 62 | 연산 순서·우선순위 | `evaluate` | 피연산자 꺼내는 순서 뒤바뀜 | O | O | O | - |
| 63* | 연산 순서·우선순위 | `_PRECEDENCE` | 나눗셈 순위가 덧셈과 같음 | O | O | O | - |
| 64 | 연산 순서·우선순위 | `celsius_to_fahrenheit` | 괄호 위치 오류 | O | O | O | - |
| 65 | 연산 순서·우선순위 | `variance` | 제곱이 center에만 적용 | O | O | O | - |
| 66 | 연산 순서·우선순위 | `mode` | 동률에서 가장 큰 값을 고름 | O | O | O | - |
| 67 | 연산 순서·우선순위 | `format_thousands` | 그룹을 뒤에 붙여 순서 뒤집힘 | O | O | O | - |
| 68 | 연산 순서·우선순위 | `to_binary` | 비트를 뒤에 붙여 순서 뒤집힘 | O | O | O | - |
| 69 | 연산 순서·우선순위 | `from_binary` | 자리값 계산 순서 오류 | O | O | O | - |
| 70 | 연산 순서·우선순위 | `Calculator.apply` | 뺄셈 피연산자 순서 뒤바뀜 | O | O | O | - |
| 71* | 파싱·형 변환 | `tokenize` | '(' 뒤 '-'를 음수 부호로 안 봄 | O | O | O | - |
| 72 | 파싱·형 변환 | `tokenize` | 소수점 이후 숫자를 이어 읽지 않음 | O | O | O | - |
| 73 | 파싱·형 변환 | `tokenize` | 탭 등 공백 문자를 공백으로 안 봄 | O | O | X | - |
| 74 | 파싱·형 변환 | `parse_number` | 앞뒤 공백 미제거(정수가 float로) | O | O | O | - |
| 75 | 파싱·형 변환 | `parse_number` | 부호 있는 정수를 float로 | O | O | O | - |
| 76 | 파싱·형 변환 | `parse_number` | inf 허용 | O | O | O | - |
| 77 | 파싱·형 변환 | `parse_number` | 내부 공백을 지워 '1 2'를 12로 | O | O | O | - |
| 78 | 파싱·형 변환 | `from_binary` | '2'를 허용 | O | O | O | - |
| 79 | 파싱·형 변환 | `tokenize` | '$'를 연산자로 받아들임 | O | O | O | - |
| 80* | 파싱·형 변환 | `format_thousands` | 부호를 숫자에 섞어 그룹 계산 | O | O | O | - |
| 81 | 조건 논리 | `is_prime` | 짝수면 2도 False | O | O | O | - |
| 82* | 조건 논리 | `is_prime` | 1을 소수로 판정 | O | O | O | - |
| 83 | 조건 논리 | `clamp` | min/max 뒤바뀜 | O | O | O | - |
| 84 | 조건 논리 | `weighted_mean` | or 대신 and(길이 불일치 통과) | O | O | O | - |
| 85* | 조건 논리 | `primes_up_to` | 체 조건 반전 | O | O | O | - |
| 86 | 조건 논리 | `evaluate` | 숫자 연속('1 2') 검사 누락 | O | O | O | - |
| 87* | 조건 논리 | `evaluate` | 닫는 괄호 짝 검사 누락 | O | O | O | - |
| 88 | 조건 논리 | `is_palindrome_number` | 첫·끝 자리만 비교 | O | O | O | - |
| 89 | 조건 논리 | `Calculator.undo` | 빈 기록 검사가 None 비교(IndexError) | O | O | O | - |
| 90 | 조건 논리 | `tokenize` | 음수 부호 판정에 and 대신 or | O | O | O | - |
| 91* | 공식·상수 | `variance` | 표본분산(n-1)으로 나눔 | O | O | O | - |
| 92 | 공식·상수 | `value_range` | 최솟값 대신 첫 원소 | O | O | O | - |
| 93 | 공식·상수 | `weighted_mean` | 가중치 합 대신 개수로 나눔 | O | O | O | - |
| 94 | 공식·상수 | `mode` | 가장 적게 나온 값을 고름 | O | O | O | - |
| 95 | 공식·상수 | `power` | 밑의 절댓값을 거듭제곱 | O | O | O | - |
| 96* | 공식·상수 | `moving_average` | 창 크기 대신 전체 길이로 나눔 | O | O | O | - |
| 97* | 공식·상수 | `fibonacci` | 점화식 오류(b + b) | O | O | O | - |
| 98* | 공식·상수 | `Calculator.apply` | 나눗셈이 정수 나눗셈 | O | O | O | - |
| 99* | 공식·상수 | `is_prime` | 홀수 약수를 4씩 건너뜀 | O | O | O | - |
| 100* | 공식·상수 | `primes_up_to` | 배수 지우기가 n을 빼먹음 | O | O | O | - |

## tetris_engine (오류 100개, 채점 식 188개)

| AI | 상태 | 시간(초) | 검증 통과 | 수정안: 고친 오류 | 수정안: 통과 식 | 자동 적용 | 현재 파일: 남은 오류 |
|---|---|---|---|---|---|---|---|
| 원본(오류 100개) | - | - | - | 0/100 | 41/188 | - | 100 |
| Gemini | failed | 9.443 | False | -/100 | -/188 | 안 함(review not verified) | 100 |
| ChatGPT | completed | 200.535 | True | 100/100 | 188/188 | 적용 | 0 |
| Claude | completed | 852.583 | True | 99/100 | 187/188 | 적용 | 0 |
| Ollama | completed | 3520.339 | True | 27/100 | 97/188 | 되돌림 | 100 |

### 분야별 고친 오류 수(수정안 기준, 분야당 10개)

| 분야 | Gemini | ChatGPT | Claude | Ollama |
|---|---|---|---|---|
| 경계값 | - | 10 | 10 | 2 |
| 부호·방향 | - | 10 | 10 | 8 |
| 회전·좌표 | - | 10 | 10 | 1 |
| 예외·검증 | - | 10 | 10 | 3 |
| 빈 입력·초기값 | - | 10 | 10 | 1 |
| 상태·부작용 | - | 10 | 10 | 3 |
| 순서·우선순위 | - | 10 | 10 | 2 |
| 파싱·변환 | - | 10 | 9 | 1 |
| 조건 논리 | - | 10 | 10 | 5 |
| 공식·상수 | - | 10 | 10 | 1 |

### 오류별 결과(수정안 기준, O=고침 X=못 고침 -=수정안 없음, *=공유 채점 식)

| # | 분야 | 함수 | 심은 오류 | Gemini | ChatGPT | Claude | Ollama |
|---|---|---|---|---|---|---|---|
| 1 | 경계값 | `new_board` | cols 0 허용 | - | O | O | X |
| 2 | 경계값 | `can_place` | 아래 경계 y == rows 통과(IndexError) | - | O | O | O |
| 3* | 경계값 | `can_place` | 오른쪽 경계 x == cols 통과(IndexError) | - | O | O | X |
| 4* | 경계값 | `can_place` | y == -1 통과(마지막 행으로 감김) | - | O | O | O |
| 5* | 경계값 | `trim_piece` | 오른쪽 열 하나 잘림 | - | O | O | X |
| 6* | 경계값 | `trim_piece` | 아래 행 하나 잘림 | - | O | O | X |
| 7* | 경계값 | `lines_to_next_level` | 남은 줄 수가 1 작음 | - | O | O | X |
| 8* | 경계값 | `column_heights` | 높이가 1 작음 | - | O | O | X |
| 9* | 경계값 | `bumpiness` | 마지막 열 쌍 누락 | - | O | O | X |
| 10* | 경계값 | `score_for_lines` | 4줄(테트리스)을 거부 | - | O | O | X |
| 11* | 부호·방향 | `shift` | 이동 방향 반대로 돌려줌 | - | O | O | O |
| 12* | 부호·방향 | `wall_kick` | 행 이동 부호 반대로 돌려줌 | - | O | O | O |
| 13* | 부호·방향 | `wall_kick` | 열 이동을 반대로 시험 | - | O | O | O |
| 14* | 부호·방향 | `gravity_frames` | 레벨이 오를수록 느려짐 | - | O | O | O |
| 15* | 부호·방향 | `hard_drop` | 떨어진 칸 수 부호 반대 | - | O | O | X |
| 16* | 부호·방향 | `bumpiness` | 차이의 절댓값 누락 | - | O | O | X |
| 17 | 부호·방향 | `score_for_lines` | level -1 허용 | - | O | O | O |
| 18* | 부호·방향 | `level_for_lines` | 음수 줄 수 허용 | - | O | O | O |
| 19* | 부호·방향 | `bag_sequence` | count -1 허용 | - | O | O | O |
| 20* | 부호·방향 | `combo_bonus` | 음수 콤보에 음수 보너스 | - | O | O | O |
| 21 | 회전·좌표 | `rotate_cw` | 전치만 함 | - | O | O | X |
| 22 | 회전·좌표 | `rotate_ccw` | 행 대신 각 행을 뒤집음(시계 방향이 됨) | - | O | O | X |
| 23 | 회전·좌표 | `rotate_180` | 행 순서를 안 뒤집음(좌우 반전만) | - | O | O | X |
| 24 | 회전·좌표 | `piece_cells` | (열, 행)으로 뒤바뀜 | - | O | O | X |
| 25* | 회전·좌표 | `can_place` | 행·열 오프셋 뒤바뀜 | - | O | O | X |
| 26* | 회전·좌표 | `place` | 행·열 오프셋 뒤바뀜 | - | O | O | X |
| 27* | 회전·좌표 | `trim_piece` | 왼쪽 경계를 행 번호로 계산 | - | O | O | X |
| 28 | 회전·좌표 | `column_heights` | 보드를 [x][y]로 읽음 | - | O | O | O |
| 29 | 회전·좌표 | `piece_size` | (너비, 높이)로 뒤바뀜 | - | O | O | X |
| 30* | 회전·좌표 | `count_holes` | 열 수 대신 행 수만큼 검사 | - | O | O | X |
| 31 | 예외·검증 | `new_board` | 정수 검사 누락(TypeError) | - | O | O | X |
| 32 | 예외·검증 | `text_to_board` | 허용 문자 검사 누락 | - | O | O | X |
| 33 | 예외·검증 | `text_to_board` | 줄 길이 검사 누락 | - | O | O | X |
| 34 | 예외·검증 | `place` | 놓을 수 있는지 검사 누락 | - | O | O | X |
| 35* | 예외·검증 | `drop_row` | 시작 위치 막혀도 그대로 반환 | - | O | O | X |
| 36 | 예외·검증 | `trim_piece` | 빈 조각에 빈 목록 반환 | - | O | O | O |
| 37 | 예외·검증 | `score_for_lines` | 예외 종류가 IndexError | - | O | O | X |
| 38* | 예외·검증 | `level_for_lines` | 예외 종류가 RuntimeError | - | O | O | O |
| 39* | 예외·검증 | `GameState.hold` | 두 번 보관 검사 누락 | - | O | O | X |
| 40* | 예외·검증 | `bag_sequence` | 음수 count에 빈 목록 | - | O | O | O |
| 41* | 빈 입력·초기값 | `GameState.__init__` | 콤보 초기값 1 | - | O | O | X |
| 42* | 빈 입력·초기값 | `GameState.__init__` | 보관 초기값이 빈 문자열 | - | O | O | X |
| 43* | 빈 입력·초기값 | `GameState.__init__` | 처음부터 보관 불가 | - | O | O | X |
| 44* | 빈 입력·초기값 | `column_heights` | 빈 열 높이가 보드 높이 | - | O | O | X |
| 45* | 빈 입력·초기값 | `max_height` | 첫 열을 빼고 계산 | - | O | O | O |
| 46* | 빈 입력·초기값 | `count_holes` | 블록을 본 것으로 시작 | - | O | O | X |
| 47* | 빈 입력·초기값 | `hard_drop` | 기본 시작 행 1 | - | O | O | X |
| 48* | 빈 입력·초기값 | `drop_row` | 기본 시작 행 1 | - | O | O | X |
| 49* | 빈 입력·초기값 | `GameState.__init__` | 줄 수 초기값 1 | - | O | O | X |
| 50 | 빈 입력·초기값 | `GameState.__init__` | 시작 레벨 무시 | - | O | O | X |
| 51 | 상태·부작용 | `copy_board` | 얕은 복사(행 공유) | - | O | O | O |
| 52 | 상태·부작용 | `new_board` | 모든 행이 같은 리스트 | - | O | O | O |
| 53 | 상태·부작용 | `clear_lines` | 남긴 행을 복사하지 않음(입력과 공유) | - | O | O | X |
| 54 | 상태·부작용 | `clear_lines` | 채운 빈 행이 같은 리스트 | - | O | O | O |
| 55* | 상태·부작용 | `GameState.record_clear` | 놓은 뒤 보관 가능 상태로 안 돌림 | - | O | O | X |
| 56* | 상태·부작용 | `GameState.__init__` | log 기본값이 모든 인스턴스가 공유하는 리스트 | - | O | O | X |
| 57* | 상태·부작용 | `place` | 입력 보드를 직접 수정 | - | O | O | X |
| 58* | 상태·부작용 | `GameState.hold` | 보관 후 잠금 누락 | - | O | O | X |
| 59* | 상태·부작용 | `GameState.record_clear` | 줄 수를 누적하지 않고 덮어씀 | - | O | O | X |
| 60* | 상태·부작용 | `GameState.record_clear` | 점수를 누적하지 않고 덮어씀 | - | O | O | X |
| 61* | 순서·우선순위 | `GameState.record_clear` | 반영 후 레벨로 점수 계산 | - | O | O | X |
| 62* | 순서·우선순위 | `GameState.record_clear` | 콤보 증가 전에 보너스 계산 | - | O | O | X |
| 63* | 순서·우선순위 | `hard_drop` | 놓기 전에 줄 지움 | - | O | O | X |
| 64* | 순서·우선순위 | `wall_kick` | 기본 시도 순서에서 왼쪽을 먼저 | - | O | O | X |
| 65* | 순서·우선순위 | `full_rows` | 내림차순 | - | O | O | X |
| 66* | 순서·우선순위 | `board_to_text` | 행 순서 뒤집힘 | - | O | O | X |
| 67 | 순서·우선순위 | `score_for_lines` | 괄호 누락(level + 1) | - | O | O | O |
| 68* | 순서·우선순위 | `combo_bonus` | 괄호 누락(level + 1) | - | O | O | X |
| 69* | 순서·우선순위 | `shift` | dx를 행에 더함 | - | O | O | O |
| 70* | 순서·우선순위 | `text_to_board` | 행을 앞에 끼워 순서 뒤집힘 | - | O | O | X |
| 71 | 파싱·변환 | `bag_sequence` | 이름 대신 모양(리스트)을 섞음 | - | O | O | X |
| 72* | 파싱·변환 | `board_to_text` | 블록 문자 'x' | - | O | O | X |
| 73* | 파싱·변환 | `text_to_board` | splitlines 사용(끝 줄바꿈 무시) | - | O | X | X |
| 74* | 파싱·변환 | `board_to_text` | 줄 구분 \r\n | - | O | O | X |
| 75 | 파싱·변환 | `bag_sequence` | count로 자르지 않음 | - | O | O | X |
| 76 | 파싱·변환 | `text_to_board` | 칸이 int 대신 bool | - | O | O | X |
| 77* | 파싱·변환 | `level_for_lines` | 내림 대신 반올림 | - | O | O | X |
| 78 | 파싱·변환 | `board_to_text` | 빈칸 문자 공백 | - | O | O | X |
| 79 | 파싱·변환 | `bag_sequence` | seed 무시(매번 다른 순서) | - | O | O | O |
| 80* | 파싱·변환 | `hard_drop` | 튜플 대신 리스트 반환 | - | O | O | X |
| 81* | 조건 논리 | `full_rows` | all 대신 any | - | O | O | X |
| 82 | 조건 논리 | `clear_lines` | 가득 찬 행 대신 빈 행을 지움 | - | O | O | O |
| 83 | 조건 논리 | `can_place` | 충돌 조건 반전 | - | O | O | O |
| 84* | 조건 논리 | `count_holes` | 블록 위 빈칸을 셈 | - | O | O | X |
| 85 | 조건 논리 | `is_game_over` | 결과 반전 | - | O | O | O |
| 86* | 조건 논리 | `drop_row` | while 대신 if(한 칸만 내려감) | - | O | O | X |
| 87* | 조건 논리 | `GameState.record_clear` | 1줄 지움을 콤보로 안 셈 | - | O | O | X |
| 88* | 조건 논리 | `is_game_over` | 맨 위 대신 둘째 행 검사 | - | O | O | O |
| 89 | 조건 논리 | `wall_kick` | 모두 막혀도 원래 위치 반환 | - | O | O | O |
| 90* | 조건 논리 | `GameState.level` | 합 대신 큰 값 | - | O | O | X |
| 91 | 공식·상수 | `LINE_SCORES` | 테트리스 점수 1000 | - | O | O | X |
| 92 | 공식·상수 | `LINES_PER_LEVEL` | 레벨당 8줄 | - | O | O | X |
| 93* | 공식·상수 | `gravity_frames` | 최솟값 0 | - | O | O | O |
| 94* | 공식·상수 | `aggregate_height` | 합 대신 최고 높이 x 열 수 | - | O | O | X |
| 95 | 공식·상수 | `PIECES` | T 모양 오류 | - | O | O | X |
| 96* | 공식·상수 | `PIECES` | S가 Z 모양 | - | O | O | X |
| 97* | 공식·상수 | `count_holes` | 구멍 하나를 2로 셈 | - | O | O | X |
| 98* | 공식·상수 | `combo_bonus` | 보너스 단위 100 | - | O | O | X |
| 99* | 공식·상수 | `GameState.record_clear` | 줄 점수를 시작 레벨로 계산 | - | O | O | X |
| 100 | 공식·상수 | `PIECES` | L이 J 모양 | - | O | O | X |

