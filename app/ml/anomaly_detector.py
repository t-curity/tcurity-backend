# app/ml/anomaly_detector.py

class DummyModel:
    def predict(self, features, attempts=0):
        # 첫 시도는 실패, 두 번째는 성공
        if attempts == 0:
            return 0.8   # 실패
        return 0.2       # 성공

model = DummyModel()
