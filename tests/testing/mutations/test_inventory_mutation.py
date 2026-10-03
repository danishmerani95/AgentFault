from cartspec.testing.perturbations import ChangeInventory
from examples.basic_world import create_basic_world


def test_quantity_is_changing() -> None:
    world = create_basic_world()
    test_offer_id = "offer_sony_1"

    inventory_perturbation = ChangeInventory(offer_id=test_offer_id, new_quantity=0)
    inventory_perturbation.apply(world)

    assert world.inventories[test_offer_id].quantity == 0
