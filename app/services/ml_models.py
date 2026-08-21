import csv
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "trip_records.csv"


def load_training_rows() -> list[dict]:
    with open(DATA_PATH, newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


class CategoryFallbackModel:
    def __init__(self, rows: list[dict]):
        self.global_choice = Counter(row["preferred_category"] for row in rows).most_common(1)[0][0]
        self.by_exact_key = defaultdict(Counter)
        self.by_mood_budget = defaultdict(Counter)
        for row in rows:
            exact_key = (row["city"], row["num_days"], row["num_people"], row["mood_preference"], row["budget_level"])
            mood_key = (row["mood_preference"], row["budget_level"])
            self.by_exact_key[exact_key][row["preferred_category"]] += 1
            self.by_mood_budget[mood_key][row["preferred_category"]] += 1

    def predict(self, samples):
        predictions = []
        for sample in samples:
            exact_key = (
                sample["city"],
                str(sample["num_days"]),
                str(sample["num_people"]),
                sample["mood_preference"],
                sample["budget_level"],
            )
            mood_key = (sample["mood_preference"], sample["budget_level"])
            if exact_key in self.by_exact_key:
                predictions.append(self.by_exact_key[exact_key].most_common(1)[0][0])
            elif mood_key in self.by_mood_budget:
                predictions.append(self.by_mood_budget[mood_key].most_common(1)[0][0])
            else:
                predictions.append(self.global_choice)
        return predictions


class CostFallbackModel:
    def __init__(self, rows: list[dict]):
        self.global_rate = self._rate(rows)
        self.by_mood_budget = defaultdict(list)
        for row in rows:
            key = (row["mood_preference"], row["budget_level"])
            self.by_mood_budget[key].append(row)
        self.group_rates = {key: self._rate(group) for key, group in self.by_mood_budget.items()}

    def _rate(self, rows: list[dict]) -> float:
        costs = [float(row["total_trip_cost"]) for row in rows]
        units = [max(1, int(row["num_days"]) * int(row["num_people"])) for row in rows]
        return sum(costs) / sum(units)

    def predict(self, samples):
        predictions = []
        for sample in samples:
            key = (sample["mood_preference"], sample["budget_level"])
            rate = self.group_rates.get(key, self.global_rate)
            predictions.append(rate * int(sample["num_days"]) * int(sample["num_people"]))
        return predictions


@lru_cache(maxsize=1)
def train_category_model():
    rows = load_training_rows()
    try:
        from sklearn.feature_extraction import DictVectorizer
        from sklearn.pipeline import Pipeline
        from sklearn.tree import DecisionTreeClassifier

        features = [
            {
                "city": row["city"],
                "num_days": int(row["num_days"]),
                "num_people": int(row["num_people"]),
                "mood_preference": row["mood_preference"],
                "budget_level": row["budget_level"],
            }
            for row in rows
        ]
        target = [row["preferred_category"] for row in rows]
        model = Pipeline(
            steps=[
                ("vectorize", DictVectorizer(sparse=False)),
                ("model", DecisionTreeClassifier(max_depth=6, random_state=42)),
            ]
        )
        return model.fit(features, target)
    except Exception:
        return CategoryFallbackModel(rows)


@lru_cache(maxsize=1)
def train_cost_model():
    rows = load_training_rows()
    try:
        from sklearn.feature_extraction import DictVectorizer
        from sklearn.linear_model import LinearRegression
        from sklearn.pipeline import Pipeline

        features = [
            {
                "num_days": int(row["num_days"]),
                "num_people": int(row["num_people"]),
                "mood_preference": row["mood_preference"],
                "budget_level": row["budget_level"],
            }
            for row in rows
        ]
        target = [float(row["total_trip_cost"]) for row in rows]
        model = Pipeline(
            steps=[
                ("vectorize", DictVectorizer(sparse=False)),
                ("model", LinearRegression()),
            ]
        )
        return model.fit(features, target)
    except Exception:
        return CostFallbackModel(rows)
