from agentfault.commerce import (
    CommerceEnvironment,
    Inventory,
    Merchant,
    Offer,
    Product,
)

def create_basic_world() -> CommerceEnvironment:
    headphones = Product(
        id="sony_wh1000xm5",
        name="Sony WH-1000XM5",
        category="headphones",
    )

    audio_world = Merchant(
        id="audio_world",
        name="AudioWorld",
    )

    headphones_offer = Offer(
        id="offer_sony_1",
        product_id=headphones.id,
        merchant_id=audio_world.id,
        price=139.0,
        currency="EUR",
    )

    headphones_inventory = Inventory(
        offer_id=headphones_offer.id,
        quantity=5,
    )

    return CommerceEnvironment(
        products=[headphones],
        merchants=[audio_world],
        offers=[headphones_offer],
        inventories=[headphones_inventory],
    )


if __name__ == "__main__":
    world = create_basic_world()

    print("Products:", world.products)
    print("Merchants:", world.merchants)
    print("Offers:", world.offers)
    print("Inventories:", world.inventories)