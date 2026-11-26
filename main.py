import json
import math
import re
import time
from pathlib import Path

EPSILON = 1e-9
REPETITIONS = 10
SIZES = (3, 5, 13, 25)


def generate_pattern(size, shape):
    """홀수 N×N Cross/X 패턴을 생성한다."""
    if type(size) is not int or size < 1 or size % 2 == 0:
        raise ValueError("크기는 양의 홀수여야 합니다.")
    if shape not in ("Cross", "X"):
        raise ValueError("패턴은 Cross 또는 X여야 합니다.")
    middle = size // 2
    return [[int(r == middle or c == middle) if shape == "Cross"
             else int(r == c or r + c == size - 1)
             for c in range(size)] for r in range(size)]


# 생성 패턴은 3×3 성능 측정 및 보너스 메뉴에 재사용한다.
pattern = generate_pattern(3, "Cross")
x_pattern = generate_pattern(3, "X")
cross_filter = generate_pattern(3, "Cross")
x_filter = generate_pattern(3, "X")


# 패턴과 필터의 같은 위치를 곱하고 모두 더한다.
def mac_score(pattern, filter_matrix):
    total = 0

    for row in range(len(pattern)):
        for column in range(len(pattern[row])):
            total = total + pattern[row][column] * filter_matrix[row][column]

    return total


# 두 점수를 비교해 판정한다.
def decide_shape(cross_score, x_score):
    if abs(cross_score - x_score) < EPSILON:
        return "판정 불가"
    elif cross_score > x_score:
        return "Cross"
    else:
        return "X"

def decide_filter(score_a, score_b):
    if abs(score_a - score_b) < EPSILON:
        return "판정 불가"
    elif score_a > score_b:
        return "A"
    else:
        return "B"

def read_row(prompt):
    while True:
        text = input(prompt)
        parts = text.split()

        if len(parts) != 3:
            print("입력 오류: 숫자 3개를 공백으로 구분해 입력하세요.")
            continue

        row = []

        try:
            for part in parts:
                row.append(float(part))
        except ValueError:
            print("입력 오류: 숫자로 입력하세요.")
            continue

        if not all(math.isfinite(value) for value in row):
            print("입력 오류: NaN 및 무한대는 사용할 수 없습니다.")
            continue

        return row

def read_matrix(matrix_name):
    matrix = []

    for row_number in range(1, 4):
        prompt = f"{matrix_name} {row_number}행: "
        row = read_row(prompt)
        matrix.append(row)

    return matrix    

def run_manual_mode():
    print("Mini NPU 과제 시작")

    while True:
        filter_a = read_matrix("필터 A")
        filter_b = read_matrix("필터 B")

        print("입력된 필터 A:", filter_a)
        print("입력된 필터 B:", filter_b)

        while True:
            confirmation = input("필터 A와 B를 저장할까요? (y/n): ").strip().lower()
            if confirmation in ("y", "n"):
                break
            print("y 또는 n으로 입력하세요.")

        if confirmation == "y":
            print("필터 A와 B를 저장했습니다.")
            break

        print("필터 A와 B를 다시 입력합니다.")

    while True:
        user_pattern = read_matrix("판정 패턴")
        print("입력된 패턴:", user_pattern)
        score_a = mac_score(user_pattern, filter_a)
        score_b = mac_score(user_pattern, filter_b)
        if math.isfinite(score_a) and math.isfinite(score_b):
            break
        print("연산 오류: 점수가 유효 범위를 벗어났습니다. 패턴을 다시 입력하세요.")

    average_time_ms = measure_mac(mac_score, user_pattern, filter_a, filter_b)
    print("필터 A 점수:", score_a)
    print("필터 B 점수:", score_b)
    print("판정:", decide_filter(score_a, score_b))
    print(f"MAC 1회 평균 시간 (A·B 각 {REPETITIONS}회): {average_time_ms:.6f} ms")
    print("크기 | MAC 1회 평균(ms) | 위치 수(N²)")
    print(f"3×3 | {average_time_ms:.6f} | 9")


def normalize_label(label):
    labels = {"+": "Cross", "cross": "Cross", "x": "X"}
    if not isinstance(label, str) or label.strip().lower() not in labels:
        raise ValueError(f"알 수 없는 라벨: {label!r}")
    return labels[label.strip().lower()]


def check_matrix(matrix, size, name):
    if not isinstance(matrix, list) or len(matrix) != size:
        raise ValueError(f"{name}의 행이 {size}개여야 합니다.")

    for row_number, row in enumerate(matrix, start=1):
        if not isinstance(row, list) or len(row) != size:
            raise ValueError(f"{name} {row_number}행의 값이 {size}개여야 합니다.")
        for value in row:
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError(f"{name} {row_number}행에 유효하지 않은 숫자가 있습니다.")


def flatten_matrix(matrix):
    """2차원 배열을 행 우선 순서의 1차원 배열로 변환한다."""
    return [value for row in matrix for value in row]


def mac_flat(pattern, filter_values):
    """1차원 배열의 MAC. 원래 위치 순서를 유지한다."""
    if len(pattern) != len(filter_values):
        raise ValueError("1차원 배열의 길이가 일치해야 합니다.")
    total = 0
    for value, weight in zip(pattern, filter_values):
        total += value * weight
    return total


def measure_mac(function, sample, first, second):
    """필터별 10회, 총 20회 호출의 1회 평균(ms). I/O 제외."""
    function(sample, first)  # 워밍업 (측정 제외)
    function(sample, second)
    start = time.perf_counter()
    for _ in range(REPETITIONS):
        function(sample, first)
        function(sample, second)
    return (time.perf_counter() - start) * 1000 / (2 * REPETITIONS)


def print_json_timing(samples):
    print("\n[성능 분석] 필터별 10회 반복, MAC 1회 평균")
    print("크기 | MAC 1회 평균(ms) | 위치 수(N²)")
    for size in SIZES:
        if size not in samples:
            print(f"{size}×{size} | 측정할 배열 없음 | {size * size}")
            continue
        sample, cross, x = samples[size]
        average_ms = measure_mac(mac_score, sample, cross, x)
        print(f"{size}×{size} | {average_ms:.6f} | {size * size}")

    print("\n[보너스] 동일 입력의 2D/1D 연산 비교 (변환 시간 별도)")
    print("크기 | 2D 평균(ms) | 1D 평균(ms) | 변환 1회(ms) | 점수 일치")
    for size in SIZES:
        if size not in samples:
            continue
        sample, cross, x = samples[size]
        start = time.perf_counter()
        flat_sample, flat_cross, flat_x = map(flatten_matrix, (sample, cross, x))
        conversion_ms = (time.perf_counter() - start) * 1000
        a = measure_mac(mac_score, sample, cross, x)
        b = measure_mac(mac_flat, flat_sample, flat_cross, flat_x)
        same = (mac_score(sample, cross) == mac_flat(flat_sample, flat_cross)
                and mac_score(sample, x) == mac_flat(flat_sample, flat_x))
        print(f"{size}×{size} | {a:.6f} | {b:.6f} | {conversion_ms:.6f} | {'일치' if same else '불일치'}")
    print("※ 변환 시간은 세 배열의 1회 변환 비용이며 MAC 평균에 포함하지 않습니다.")
    print("※ 두 방식 모두 필터 1개당 N² 위치를 연산하므로 O(N²)입니다.")


def run_generator_mode():
    """생성된 패턴을 판정 및 성능 측정에 재활용한다."""
    while True:
        try:
            size = int(input("홀수 크기 N (1~99): "))
            if not 1 <= size <= 99:
                raise ValueError("크기는 1~99여야 합니다.")
            cross = generate_pattern(size, "Cross")
            x = generate_pattern(size, "X")
            break
        except ValueError as error:
            print(f"입력 오류: {error}")
    for name, sample in (("Cross", cross), ("X", x)):
        print(f"\n{name} 패턴")
        for row in sample:
            print(" ".join(map(str, row)))
        a, b = mac_score(sample, cross), mac_score(sample, x)
        result = decide_shape(a, b)
        print(f"Cross: {a} | X: {b} | 판정: {result}")
        print(f"MAC 1회 평균: {measure_mac(mac_score, sample, cross, x):.6f} ms | 위치 수: {size * size}")



def run_json_mode():
    data_path = Path(__file__).with_name("data.json")

    try:
        with data_path.open(encoding="utf-8-sig") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            raise ValueError("JSON 최상위에 객체가 필요합니다.")
        filter_groups = data.get("filters")
        cases = data.get("patterns")
        if not isinstance(filter_groups, dict) or not isinstance(cases, dict):
            raise ValueError("filters와 patterns는 JSON 객체여야 합니다.")
    except (OSError, ValueError) as error:
        print(f"data.json을 읽을 수 없습니다: {error}")
        return

    print("\n[JSON 로드] filters 및 patterns 확인 완료")
    print("[패턴 분석] 키 추출 → 크기 검증 → 라벨 정규화 → MAC")
    failures = []
    samples = {3: (pattern, cross_filter, x_filter)}

    for case_name, case in cases.items():
        try:
            match = re.fullmatch(r"size_([1-9][0-9]*)_[0-9]+", case_name)
            if match is None or not isinstance(case, dict):
                raise ValueError("케이스 이름 또는 형식이 잘못되었습니다.")

            size = int(match.group(1))
            expected = normalize_label(case.get("expected"))
            input_matrix = case.get("input")
            check_matrix(input_matrix, size, "입력 배열")

            group = filter_groups.get(f"size_{size}")
            if not isinstance(group, dict):
                raise ValueError(f"size_{size} 필터 묶음이 없습니다.")

            filters = {}
            for label, matrix in group.items():
                standard_label = normalize_label(label)
                if standard_label in filters:
                    raise ValueError(f"{standard_label} 필터가 중복되었습니다.")
                filters[standard_label] = matrix

            cross = filters.get("Cross")
            x = filters.get("X")
            check_matrix(cross, size, "Cross 필터")
            check_matrix(x, size, "X 필터")

            cross_score = mac_score(input_matrix, cross)
            x_score = mac_score(input_matrix, x)
            if not math.isfinite(cross_score) or not math.isfinite(x_score):
                raise ValueError("MAC 점수가 유효한 범위를 벗어났습니다.")
        except (ValueError, OverflowError) as error:
            failures.append((case_name, str(error)))
            print(f"{case_name} | FAIL | {error}")
            continue

        samples.setdefault(size, (input_matrix, cross, x))
        result = decide_shape(cross_score, x_score)
        if result == "판정 불가":
            result = "UNDECIDED"

        status = "PASS" if result == expected else "FAIL"
        print(
            f"{case_name} | Cross: {cross_score} | X: {x_score} | "
            f"판정: {result} | 기대값: {expected} | {status}"
        )
        if status == "FAIL":
            reason = "허용 오차 안에서 동점" if result == "UNDECIDED" else "기대값 불일치"
            failures.append((case_name, reason))

    print_json_timing(samples)
    print(f"\n전체 {len(cases)}건 | PASS {len(cases) - len(failures)}건 | FAIL {len(failures)}건")
    for case_name, reason in failures:
        print(f"- {case_name}: {reason}")


def main():
    while True:
        print("1. 사용자 입력 (3×3)")
        print("2. data.json 분석")
        print("3. 패턴 자동 생성 (보너스)")
        choice = input("선택: ").strip()

        if choice == "1":
            run_manual_mode()
            return
        if choice == "2":
            run_json_mode()
            return
        if choice == "3":
            run_generator_mode()
            return
        print("1, 2 또는 3을 입력하세요.")


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\n입력이 종료되었습니다.")
