from django.db import models
from django.conf import settings
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator


# Create your models here.
class Store(models.Model):
    name = models.CharField(max_length=100)
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="stores",
    )

    def __str__(self):
        return self.name


class Product(models.Model):
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="products",
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        )
    stock = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name


class Review(models.Model):
    # ownership check:
    # author=request.user
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews_product",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews_author",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=100)
    body = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class Order(models.Model):
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total(self):
        return sum(item.line_total for item in self.items.all())

    def __str__(self):
        return f"Order #{self.pk} | {self.buyer} | R{self.total}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )

    @property
    def line_total(self):
        return self.quantity * self.price_at_purchase

    def __str__(self):
        return (
            f"{self.product} | Qty: {self.quantity} | "
            f"@ R{self.price_at_purchase} each | R{self.line_total}"
        )
