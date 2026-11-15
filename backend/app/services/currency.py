import os


# USD remains the stored dataset currency. These planning conversion rates make
# destination estimates readable in local currency; they are not live FX quotes.
CURRENCY_INFO = {
    "USD": {"name": "US Dollar", "symbol": "$", "per_usd": 1.0},
    "INR": {"name": "Indian Rupee", "symbol": "₹", "per_usd": float(os.getenv("INR_PER_USD", "93.7"))},
    "ARS": {"name": "Argentine Peso", "symbol": "ARS ", "per_usd": 1500.0},
    "AUD": {"name": "Australian Dollar", "symbol": "A$", "per_usd": 1.47},
    "BRL": {"name": "Brazilian Real", "symbol": "R$", "per_usd": 5.56},
    "CAD": {"name": "Canadian Dollar", "symbol": "C$", "per_usd": 1.43},
    "CNY": {"name": "Chinese Yuan", "symbol": "CN¥", "per_usd": 6.67},
    "EGP": {"name": "Egyptian Pound", "symbol": "E£", "per_usd": 52.0},
    "EUR": {"name": "Euro", "symbol": "€", "per_usd": 0.905},
    "JPY": {"name": "Japanese Yen", "symbol": "¥", "per_usd": 160.0},
    "KES": {"name": "Kenyan Shilling", "symbol": "KSh ", "per_usd": 129.0},
    "MAD": {"name": "Moroccan Dirham", "symbol": "MAD ", "per_usd": 10.0},
    "MXN": {"name": "Mexican Peso", "symbol": "MX$", "per_usd": 18.7},
    "NZD": {"name": "New Zealand Dollar", "symbol": "NZ$", "per_usd": 1.71},
    "PEN": {"name": "Peruvian Sol", "symbol": "S/ ", "per_usd": 3.75},
    "THB": {"name": "Thai Baht", "symbol": "฿", "per_usd": 36.0},
    "VND": {"name": "Vietnamese Dong", "symbol": "₫", "per_usd": 26200.0},
    "ZAR": {"name": "South African Rand", "symbol": "R ", "per_usd": 16.6},
}

COUNTRY_CURRENCY = {
    "Argentina": "ARS", "Australia": "AUD", "Brazil": "BRL", "Canada": "CAD",
    "China": "CNY", "Egypt": "EGP", "France": "EUR", "Germany": "EUR",
    "Greece": "EUR", "India": "INR", "Italy": "EUR", "Japan": "JPY",
    "Kenya": "KES", "Mexico": "MXN", "Morocco": "MAD", "New Zealand": "NZD",
    "Peru": "PEN", "South Africa": "ZAR", "Spain": "EUR", "Thailand": "THB",
    "USA": "USD", "Vietnam": "VND",
}
SUPPORTED_CURRENCIES = tuple(CURRENCY_INFO)


def normalize_currency(currency: str | None) -> str:
    value = (currency or "USD").strip().upper()
    return value if value in CURRENCY_INFO else "USD"


def currency_for_country(country: str | None) -> str:
    return COUNTRY_CURRENCY.get((country or "").strip(), "USD")


def to_usd(amount: float, currency: str) -> float:
    return float(amount) / CURRENCY_INFO[normalize_currency(currency)]["per_usd"]


def from_usd(amount_usd: float, currency: str) -> float:
    return float(amount_usd) * CURRENCY_INFO[normalize_currency(currency)]["per_usd"]


def currency_symbol(currency: str) -> str:
    return CURRENCY_INFO[normalize_currency(currency)]["symbol"]


def currency_label(currency: str) -> str:
    code = normalize_currency(currency)
    return f"{CURRENCY_INFO[code]['name']} ({code})"


def format_money(amount_usd: float, currency: str, decimals: int = 0) -> str:
    value = from_usd(amount_usd, currency)
    symbol = currency_symbol(currency)
    if decimals <= 0:
        return f"{symbol}{value:,.0f}"
    return f"{symbol}{value:,.{decimals}f}"


def budget_defaults_for(currency: str) -> dict[str, int]:
    currency = normalize_currency(currency)
    usd_defaults = {"Low": 100, "Medium": 250, "High": 500}
    return {level: int(round(from_usd(amount, currency))) for level, amount in usd_defaults.items()}
