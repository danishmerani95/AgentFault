from cartspec.tool import Tool


def add_to_cart(
    cart_id: str,
    offer_id: str,
    quantity: int,
) -> None:
    pass


def test_tool_generates_openai_schema() -> None:
    tool = Tool(
        name="add_to_cart",
        description="Add an item to a cart.",
        function=add_to_cart,
    )

    schema = tool.to_openai_schema()

    assert schema == {
        "type": "function",
        "function": {
            "name": "add_to_cart",
            "description": "Add an item to a cart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cart_id": {"type": "string"},
                    "offer_id": {"type": "string"},
                    "quantity": {"type": "integer"},
                },
                "required": [
                    "cart_id",
                    "offer_id",
                    "quantity",
                ],
            },
        },
    }
