from django.contrib import admin
from .models import Store, Product, Review, Order, OrderItem

"""
Admin site registrations for the shop app.
"""

admin.site.register(Store)
admin.site.register(Product)
admin.site.register(Review)
admin.site.register(Order)
admin.site.register(OrderItem)
