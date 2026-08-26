import requests

def fetch(url: str) -> dict:
    # Extract item ID from Home Depot URL
    import re
    match = re.search(r'/(\d{9})(?:\?|$)', url)
    if not match:
        return {"price": None, "name": None, "in_stock": None, "error": "Invalid URL"}
    
    item_id = match.group(1)
    
    params = {
        "engine": "home_depot_product",
        "product_id": item_id,
        "api_key": config.SERPAPI_KEY
    }
    
    response = requests.get("https://serpapi.com/search", params=params)
    data = response.json()
    
    product = data.get("product_results", {})
    return {
        "price": product.get("price"),
        "name": product.get("title"),
        "in_stock": product.get("in_stock", False),
        "error": None
    }
