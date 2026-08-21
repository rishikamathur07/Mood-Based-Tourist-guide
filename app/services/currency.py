import os

INR_PER_USD = float(os.getenv("INR_PER_USD", "83.5"))
SUPPORTED_CURRENCIES = ("USD", "INR")


def normalize_currency(currency: str | None) -> str:
    value = (currency or "USD").strip().upper()
    return value if value in SUPPORTED_CURRENCIES else "USD"


def to_usd(amount: float, currency: str) -> float:
    currency = normalize_currency(currency)
    if currency == "INR":
        return float(amount) / INR_PER_USD
    return float(amount)


def from_usd(amount_usd: float, currency: str) -> float:
    currency = normalize_currency(currency)
    if currency == "INR":
        return float(amount_usd) * INR_PER_USD
    return float(amount_usd)


def currency_symbol(currency: str) -> str:
    return "₹" if normalize_currency(currency) == "INR" else "$"


def format_money(amount_usd: float, currency: str, decimals: int = 0) -> str:
    value = from_usd(amount_usd, currency)
    symbol = currency_symbol(currency)
    if decimals <= 0:
        return f"{symbol}{value:,.0f}"
    return f"{symbol}{value:,.{decimals}f}"


def budget_defaults_for(currency: str) -> dict[str, int]:
    currency = normalize_currency(currency)
    usd_defaults = {"Low": 500, "Medium": 1200, "High": 2500}
    if currency == "USD":
        return usd_defaults
    return {level: int(round(from_usd(amount, "INR"))) for level, amount in usd_defaults.items()}
