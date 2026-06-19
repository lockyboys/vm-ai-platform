# core/anomaly_detector.py ★ 7.20.0
# 이상값 탐지 전용 모듈
# 초등학생 설명: 줄에서 너무 멀리 떨어진 숫자를 찾아요.


def detect_iqr(df):
    """IQR 방식으로 숫자 열의 이상값 개수를 세요."""
    result = {}
    for col in df.select_dtypes(include="number").columns:
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        mask = (df[col] < q1 - 1.5 * iqr) | (df[col] > q3 + 1.5 * iqr)
        result[col] = int(mask.sum())
    return result
