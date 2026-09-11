from dataclasses import dataclass
from uuid import uuid4


@dataclass
class Product:
    id: str
    name: str
    category: str


@dataclass
class Merchant:
    id: str
    name: str


@dataclass
class Offer:
    id: str
    product_id: str
    merchant_id: str
    price: float
    currency: str


@dataclass
class Inventory:
    offer_id: str
    quantity: int


@dataclass
class CartItem:
    offer_id: str
    quantity: int


@dataclass
class Cart:
    id: str
    items: list[CartItem]


@dataclass
class Order:
    id: str
    offer_id: str
    quantity: int
    unit_price: float
    currency: str
    total_price: float
    status: str


class CommerceEnvironment:
    def __init__(
        self,
        products: list[Product],
        merchants: list[Merchant],
        offers: list[Offer],
        inventories: list[Inventory],
    ) -> None:
        self.products = {product.id: product for product in products}
        self.merchants = {merchant.id: merchant for merchant in merchants}
        self.offers = {offer.id: offer for offer in offers}
        self.inventories = {inventory.offer_id: inventory for inventory in inventories}

        self.carts: dict[str, Cart] = {}
        self.orders: dict[str, Order] = {}

    def search_products(self, query: str) -> list[Product]:
        query = query.lower()

        return [
            product
            for product in self.products.values()
            if query in product.name.lower() or query in product.category.lower()
        ]

    def get_offer(self, offer_id: str) -> Offer:
        return self.offers[offer_id]

    def check_inventory(self, offer_id: str) -> Inventory:
        return self.inventories[offer_id]

    def create_cart(self) -> Cart:
        cart = Cart(
            id=f"cart_{uuid4().hex[:8]}",
            items=[],
        )

        self.carts[cart.id] = cart

        return cart

    def add_to_cart(
        self,
        cart_id: str,
        offer_id: str,
        quantity: int,
    ) -> Cart:
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        cart = self.carts[cart_id]

        if offer_id not in self.offers:
            raise ValueError(f"Unknown offer: {offer_id}")

        inventory = self.inventories[offer_id]

        if inventory.quantity < quantity:
            raise ValueError("Not enough inventory.")

        cart.items.append(
            CartItem(
                offer_id=offer_id,
                quantity=quantity,
            )
        )

        return cart

    def purchase(self, cart_id: str) -> list[Order]:
        cart = self.carts[cart_id]

        if not cart.items:
            raise ValueError("Cannot purchase an empty cart.")

        orders: list[Order] = []

        for item in cart.items:
            offer = self.offers[item.offer_id]
            inventory = self.inventories[item.offer_id]

            if inventory.quantity < item.quantity:
                raise ValueError(f"Not enough inventory for offer: {item.offer_id}")

            order = Order(
                id=f"order_{uuid4().hex[:8]}",
                offer_id=item.offer_id,
                quantity=item.quantity,
                unit_price=offer.price,
                currency=offer.currency,
                total_price=offer.price * item.quantity,
                status="completed",
            )

            inventory.quantity -= item.quantity
            self.orders[order.id] = order
            orders.append(order)

        cart.items.clear()

        return orders

    def get_offers_for_product(self, product_id: str) -> list[Offer]:
        return [
            offer for offer in self.offers.values() if offer.product_id == product_id
        ]
