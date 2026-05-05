from statistics import mean


def analyze_properties(properties: list[dict]) -> dict:
    prices = [int(item["price"]) for item in properties if item.get("price") is not None]
    if not prices:
        return {
            "total_results": 0,
            "average_price": None,
            "min_price": None,
            "max_price": None,
            "below_average_count": 0,
            "opportunities": [],
        }

    avg_price = mean(prices)
    opportunity_threshold = avg_price * 0.85
    opportunities = [item for item in properties if item.get("price") and item["price"] <= opportunity_threshold]

    return {
        "total_results": len(properties),
        "average_price": round(avg_price, 2),
        "min_price": min(prices),
        "max_price": max(prices),
        "below_average_count": sum(1 for price in prices if price < avg_price),
        "opportunities": opportunities,
    }
