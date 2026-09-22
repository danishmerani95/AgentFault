from cartspec.testing.mutations.price_mutation import PriceMutation
from cartspec.testing.triggers.tool import ToolTrigger


def test_tool_trigger_has_correct_definition() -> None:
    mutation = PriceMutation(offer_id="test_id", new_price=100)
    trigger = ToolTrigger(tool_name="get_offers_for_product", mutation=mutation)

    assert trigger.tool_name == "get_offers_for_product"
    assert trigger.mutation is mutation
