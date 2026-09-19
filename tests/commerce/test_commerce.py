from examples.basic_world import create_basic_world


def test_discover_headphones() -> None:
    world = create_basic_world()

    products = world.search_products("headphones")

    assert len(products) == 1
    assert products[0].name == "Sony WH-1000XM5"

    offer = world.get_offer("offer_sony_1")

    assert offer.price == 139.0
    assert offer.currency == "EUR"

    inventory = world.check_inventory("offer_sony_1")

    assert inventory.quantity == 5


def test_create_cart_and_add_item() -> None:
    world = create_basic_world()

    cart = world.create_cart()

    assert cart.id in world.carts
    assert cart.items == []

    cart = world.add_to_cart(
        cart_id=cart.id,
        offer_id="offer_sony_1",
        quantity=1,
    )

    assert len(cart.items) == 1
    assert cart.items[0].offer_id == "offer_sony_1"
    assert cart.items[0].quantity == 1


def test_purchase() -> None:
    world = create_basic_world()
    cart = world.create_cart()
    world.add_to_cart(
        cart_id=cart.id,
        offer_id="offer_sony_1",
        quantity=1,
    )
    orders = world.purchase(cart.id)

    assert len(orders) == 1

    order = orders[0]
    assert order.offer_id == "offer_sony_1"
    assert order.quantity == 1
    assert order.unit_price == 139.0
    assert order.total_price == 139.0
    assert order.currency == "EUR"
    assert order.status == "completed"

    assert world.inventories["offer_sony_1"].quantity == 4
    assert world.carts[cart.id].items == []


def test_get_offers_for_product() -> None:
    world = create_basic_world()

    offers = world.get_offers_for_product("sony_wh1000xm5")

    assert len(offers) == 1
    assert offers[0].id == "offer_sony_1"
