import csv
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parents[3] / "database" / "data" / "trip_records.csv"


def load_training_rows() -> list[dict]:
    with open(DATA_PATH, newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


class CategoryFallbackModel:
    """Safe pure-Python dataset-backed fallback when scikit-learn is unavailable."""

    def __init__(self, rows: list[dict]):
        self.global_choice = Counter(row["preferred_category"] for row in rows).most_common(1)[0][0]
        self.by_exact_key = defaultdict(Counter)
        self.by_mood_budget = defaultdict(Counter)
        for row in rows:
            exact_key = (
                row["city"].strip().lower(),
                str(row["num_days"]),
                str(row["num_people"]),
                row["mood_preference"].strip().lower(),
                row["budget_level"].strip().lower(),
            )
            mood_key = (row["mood_preference"].strip().lower(), row["budget_level"].strip().lower())
            self.by_exact_key[exact_key][row["preferred_category"]] += 1
            self.by_mood_budget[mood_key][row["preferred_category"]] += 1

    def predict(self, samples):
        predictions = []
        for sample in samples:
            exact_key = (
                str(sample.get("city", "")).strip().lower(),
                str(sample.get("num_days", 1)),
                str(sample.get("num_people", 1)),
                str(sample.get("mood_preference", "")).strip().lower(),
                str(sample.get("budget_level", "")).strip().lower(),
            )
            mood_key = (
                str(sample.get("mood_preference", "")).strip().lower(),
                str(sample.get("budget_level", "")).strip().lower(),
            )
            if exact_key in self.by_exact_key:
                predictions.append(self.by_exact_key[exact_key].most_common(1)[0][0])
            elif mood_key in self.by_mood_budget:
                predictions.append(self.by_mood_budget[mood_key].most_common(1)[0][0])
            else:
                predictions.append(self.global_choice)
        return predictions


class CostFallbackModel:
    """Safe pure-Python dataset-backed cost fallback when scikit-learn is unavailable."""

    def __init__(self, rows: list[dict]):
        self.global_rate = self._rate(rows)
        self.by_mood_budget = defaultdict(list)
        for row in rows:
            key = (row["mood_preference"].strip().lower(), row["budget_level"].strip().lower())
            self.by_mood_budget[key].append(row)
        self.group_rates = {key: self._rate(group) for key, group in self.by_mood_budget.items()}

    def _rate(self, rows: list[dict]) -> float:
        costs = [float(row["total_trip_cost"]) for row in rows]
        units = [max(1, int(row["num_days"]) * int(row["num_people"])) for row in rows]
        return sum(costs) / sum(units)

    def predict(self, samples):
        predictions = []
        for sample in samples:
            key = (
                str(sample.get("mood_preference", "")).strip().lower(),
                str(sample.get("budget_level", "")).strip().lower(),
            )
            rate = self.group_rates.get(key, self.global_rate)
            days = max(1, int(sample.get("num_days", 1)))
            people = max(1, int(sample.get("num_people", 1)))
            predictions.append(round(rate * days * people, 2))
        return predictions


@lru_cache(maxsize=1)
def train_category_model():
    """Train Decision Tree from trip records to predict preferred category."""
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
    """Train Linear Regression to estimate trip cost."""
    rows = load_training_rows()
    try:
        from sklearn.feature_extraction import DictVectorizer
        from sklearn.linear_model import LinearRegression
        from sklearn.pipeline import Pipeline

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


def _feature_rows(rows: list[dict], include_city: bool) -> list[dict]:
    features = []
    for row in rows:
        sample = {
            "num_days": int(row["num_days"]),
            "num_people": int(row["num_people"]),
            "mood_preference": row["mood_preference"],
            "budget_level": row["budget_level"],
        }
        if include_city:
            sample["city"] = row["city"]
        features.append(sample)
    return features


@lru_cache(maxsize=1)
def model_report() -> dict:
    """Internal model validation report on held-out test split."""
    rows = load_training_rows()
    training_rows = [row for index, row in enumerate(rows) if index % 5]
    validation_rows = [row for index, row in enumerate(rows) if not index % 5]
    category_expected = [row["preferred_category"] for row in validation_rows]
    cost_expected = [float(row["total_trip_cost"]) for row in validation_rows]

    backend = "Dataset fallback"
    try:
        from sklearn.feature_extraction import DictVectorizer
        from sklearn.linear_model import LinearRegression
        from sklearn.pipeline import Pipeline
        from sklearn.tree import DecisionTreeClassifier

        category_model = Pipeline(
            [("vectorize", DictVectorizer(sparse=False)), ("model", DecisionTreeClassifier(max_depth=6, random_state=42))]
        ).fit(_feature_rows(training_rows, include_city=True), [row["preferred_category"] for row in training_rows])
        cost_model = Pipeline(
            [("vectorize", DictVectorizer(sparse=False)), ("model", LinearRegression())]
        ).fit(_feature_rows(training_rows, include_city=True), [float(row["total_trip_cost"]) for row in training_rows])
        category_predictions = category_model.predict(_feature_rows(validation_rows, include_city=True))
        cost_predictions = cost_model.predict(_feature_rows(validation_rows, include_city=True))
        backend = "scikit-learn"
    except Exception:
        category_predictions = CategoryFallbackModel(training_rows).predict(_feature_rows(validation_rows, include_city=True))
        cost_predictions = CostFallbackModel(training_rows).predict(_feature_rows(validation_rows, include_city=True))

    accuracy = sum(predicted == expected for predicted, expected in zip(category_predictions, category_expected)) / len(category_expected)
    mae = sum(abs(float(predicted) - expected) for predicted, expected in zip(cost_predictions, cost_expected)) / len(cost_expected)
    average_cost = sum(cost_expected) / len(cost_expected)
    total_variance = sum((value - average_cost) ** 2 for value in cost_expected)
    residual_variance = sum((float(predicted) - expected) ** 2 for predicted, expected in zip(cost_predictions, cost_expected))
    r_squared = 1 - residual_variance / total_variance if total_variance else 0
    return {
        "backend": backend,
        "training_rows": len(training_rows),
        "validation_rows": len(validation_rows),
        "category_accuracy_percent": round(accuracy * 100, 1),
        "cost_mae": round(mae, 2),
        "cost_r_squared": round(r_squared, 3),
    }
