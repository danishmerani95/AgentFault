from cartspec.testing.mutations import PriceMutation
from examples.basic_world import create_basic_world


def test_price_is_mutating() -> None:
    world = create_basic_world()
    test_offer_id = "offer_sony_1"

    price_mutation = PriceMutation(offer_id=test_offer_id, new_price=179.0)
    price_mutation.apply(world)

    assert world.offers[test_offer_id].price == 179
