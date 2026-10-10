import json

from agentfault.commerce import Product


def test_product_serializes_to_json() -> None:
    product = Product(
        id="sony_wh1000xm5",
        name="Sony WH-1000XM5",
        category="headphones",
    )

    result = product.model_dump_json()

    assert json.loads(result) == {
        "id": "sony_wh1000xm5",
        "name": "Sony WH-1000XM5",
        "category": "headphones",
    }


def test_product_list_can_be_serialized() -> None:
    products = [
        Product(
            id="sony_wh1000xm5",
            name="Sony WH-1000XM5",
            category="headphones",
        ),
        Product(
            id="airpods_max",
            name="AirPods Max",
            category="headphones",
        ),
    ]

    result = json.dumps([product.model_dump() for product in products])

    assert json.loads(result) == [
        {
            "id": "sony_wh1000xm5",
            "name": "Sony WH-1000XM5",
            "category": "headphones",
        },
        {
            "id": "airpods_max",
            "name": "AirPods Max",
            "category": "headphones",
        },
    ]
