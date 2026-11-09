from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import ProtectedError
from .models import Store, Product, Order, OrderItem, Review
from django.core.mail import EmailMessage
from django.conf import settings
from .functions.reddit import RedditFetchError, get_reddit_posts

"""
Views for stores, products, the cart, checkout and reviews.
"""


def home(request):
    """
    Show the home page: a product grid with search.
    """

    search_query = request.GET.get("q", "").strip()
    products = Product.objects.select_related("store").all()

    if search_query:
        products = products.filter(name__icontains=search_query)

    return render(
        request,
        "shop/home.html",
        {
            "products": products,
            "search_query": search_query,
        },
    )


def reddit_feed(request):
    """
    Renders a template displaying recent posts from a specified subreddit.
    """

    posts = []
    error = None
    try:
        posts = get_reddit_posts(
            "python"
        )  # "python" is just the subreddit, use another if you want # noqa
    except RedditFetchError as exc:
        error = str(exc)

    return render(
        request,
        "shop/reddit_feed.html",
        {"posts": posts, "error": error, "subreddit": "python"},
    )


# ***** STORE VIEWS - START *****
@login_required
@permission_required("shop.add_store", raise_exception=True)
def my_stores(request):
    """
    List the logged-in vendor's stores.
    """

    stores = Store.objects.filter(vendor=request.user)
    return render(request, "shop/my_stores.html", {"stores": stores})


@login_required
@permission_required("shop.add_store", raise_exception=True)
def create_store(request):
    """
    Create a store owned by the logged-in vendor.
    """

    if request.method != "POST":
        return render(request, "shop/create_store.html")

    name = request.POST.get("name", "").strip()

    if not name:
        return render(
            request,
            "shop/create_store.html",
            {
                "errors": ["Please enter a name."],
                "form_data": {"name": name},
            },
        )

    Store.objects.create(name=name, vendor=request.user)
    return redirect("shop:my_stores")


@login_required
@permission_required("shop.change_store", raise_exception=True)
def edit_store(request, pk):
    """
    Rename one of the vendor's own stores.
    """

    store = get_object_or_404(Store, pk=pk, vendor=request.user)

    if request.method != "POST":
        return render(request, "shop/edit_store.html", {"store": store})

    name = request.POST.get("name", "").strip()

    if not name:
        return render(
            request,
            "shop/edit_store.html",
            {
                "store": store,
                "errors": ["Please enter a store name."],
            },
        )
    store.name = name
    store.save()
    return redirect("shop:my_stores")


@login_required
@permission_required("shop.delete_store", raise_exception=True)
@require_POST
def delete_store(request, pk):
    """
    Delete one of the vendor's own stores (POST only).
    A store with products that have been ordered cannot be deleted,
    and the vendor is told why.
    """

    store = get_object_or_404(Store, pk=pk, vendor=request.user)
    try:
        store.delete()
    except ProtectedError:
        messages.error(
            request,
            "this store has products that have been ordered, "
            "and therefore can not be deleted.",
        )
    return redirect("shop:my_stores")


# ***** STORE VIEWS - END *****


# ***** PRODUCT VIEWS - START *****
@login_required
@permission_required("shop.add_product", raise_exception=True)
def my_products(request):
    """
    List the logged-in vendor's products, grouped by store.
    """

    stores = Store.objects.filter(vendor=request.user)
    return render(request, "shop/my_products.html", {"stores": stores})


@login_required
@permission_required("shop.add_product", raise_exception=True)
def add_product(request):
    """
    Add a product to one of the vendor's own stores.
    """

    stores = Store.objects.filter(vendor=request.user)

    if request.method != "POST":
        return render(request, "shop/add_product.html", {"stores": stores})

    # Store: looked up inside the vendor's own stores, so ownership is built in
    store_id = request.POST.get("store", "")
    store = stores.filter(pk=store_id).first() if store_id.isdigit() else None

    product = Product(
        store=store,
        name=request.POST.get("name", "").strip(),
        description=request.POST.get("description", "").strip(),
        price=request.POST.get("price", "").strip(),
        stock=request.POST.get("stock", "").strip(),
    )

    errors = []
    if store is None:
        errors.append("Please choose a store")

    try:
        product.full_clean(exclude=["store"])
    except ValidationError as e:
        for field, messages_list in e.message_dict.items():
            for message in messages_list:
                errors.append(f"{field.capitalize()}: {message}")

    if errors:
        return render(
            request,
            "shop/add_product.html",
            {
                "stores": stores,
                "errors": errors,
                "form_data": request.POST,
            },
        )

    product.save()
    return redirect("shop:my_products")


@login_required
@permission_required("shop.change_product", raise_exception=True)
def edit_product(request, pk):
    """
    Edit one of the vendor's own products.
    """

    product = get_object_or_404(Product, pk=pk, store__vendor=request.user)

    if request.method != "POST":
        form_data = {
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "stock": product.stock,
        }
        return render(
            request,
            "shop/edit_product.html",
            {
                "product": product,
                "form_data": form_data,
            },
        )

    product.name = request.POST.get("name", "").strip()
    product.description = request.POST.get("description", "").strip()
    product.price = request.POST.get("price", "").strip()
    product.stock = request.POST.get("stock", "").strip()

    errors = []
    try:
        product.full_clean(exclude=["store"])
    except ValidationError as e:
        for field, messages_list in e.message_dict.items():
            for message in messages_list:
                errors.append(f"{field.capitalize()}: {message}")

    if errors:
        return render(
            request,
            "shop/edit_product.html",
            {
                "product": product,
                "errors": errors,
                "form_data": request.POST,
            },
        )

    product.save()
    return redirect("shop:my_products")


@login_required
@permission_required("shop.delete_product", raise_exception=True)
@require_POST
def delete_product(request, pk):
    """
    Delete one of the vendor's own products (POST only).
    A product that has been ordered cannot be deleted, and the vendor
    is told why.
    """

    product = get_object_or_404(Product, pk=pk, store__vendor=request.user)
    try:
        product.delete()
    except ProtectedError:
        messages.error(
            request, "This product has been ordered, so it can't be deleted."
        )
    return redirect("shop:my_products")


@login_required
@permission_required("shop.view_product", raise_exception=True)
def product_list(request):
    """
    List every product from every store for logged-in users.
    """

    products = Product.objects.select_related("store").all()
    return render(request, "shop/product_list.html", {"products": products})


@login_required
@permission_required("shop.view_product", raise_exception=True)
def product_detail(request, pk):
    """
    Show one product with its reviews and the add-to-cart form.
    """

    product = get_object_or_404(Product, pk=pk)
    return render(request, "shop/product_detail.html", {"product": product})


# ***** PRODUCT VIEWS - END *****


# ***** REVIEW VIEWS - START *****
@login_required
@permission_required("shop.add_review", raise_exception=True)
@require_POST
def add_review(request, pk):
    """
    Post a review of a product (POST only).
    The review is marked verified when the buyer has purchased the
    product. The server decides this, never the submitted form.
    """

    product = get_object_or_404(Product, pk=pk)

    review = Review(
        product=product,
        author=request.user,
        rating=request.POST.get("rating", "").strip(),
        title=request.POST.get("title", "").strip(),
        body=request.POST.get("body", "").strip(),
        is_verified=OrderItem.objects.filter(
            order__buyer=request.user, product=product
        ).exists(),
    )
    try:
        review.full_clean()
    except ValidationError as e:
        for field, msgs in e.message_dict.items():
            for msg in msgs:
                messages.error(request, f"{field.capitalize()}: {msg}")
        return redirect("shop:product_detail", pk=product.pk)

    review.save()
    messages.success(request, "Your review has been posted.")
    return redirect("shop:product_detail", pk=product.pk)
# ***** REVIEW VIEWS - END *****


# ***** CART VIEWS - START *****
@login_required
@permission_required("shop.view_product", raise_exception=True)
@require_POST
def add_item_to_cart(request, pk):
    """
    Add a product to the session cart (POST only).
    The quantity must be 1 to 10 and must not exceed the available stock.
    """

    product = get_object_or_404(Product, pk=pk)
    quantity = request.POST.get("quantity", "").strip()
    if not product or not quantity:
        return redirect("shop:cart_page")

    try:
        quantity = int(request.POST.get("quantity", ""))
    except ValueError:
        quantity = 0

    if not 1 <= quantity <= 10:
        messages.error(request, "Each product has a 10 unit buy-limit")
        return redirect("shop:product_detail", pk=product.pk)

    cart = request.session.get("cart", {})

    key = str(product.pk)
    new_total = cart.get(key, 0) + quantity

    if new_total > product.stock:
        messages.error(request, f"Only {product.stock} units available.")
        return redirect("shop:product_detail", pk=product.pk)

    cart[key] = new_total
    request.session["cart"] = cart
    return redirect("shop:cart_page")


@login_required
@permission_required("shop.view_product", raise_exception=True)
@require_POST
def remove_cart_item(request, pk):
    """
    Remove a product from the session cart (POST only).
    """

    cart = request.session.get("cart", {})
    cart.pop(str(pk), None)
    request.session["cart"] = cart
    return redirect("shop:cart_page")


@login_required
@permission_required("shop.view_product", raise_exception=True)
def cart_page(request):
    """
    Show the cart, rebuilt from the product ids kept in the session.
    """

    cart = request.session.get("cart", {})
    products = Product.objects.select_related("store").filter(
        pk__in=list(cart)
    )

    items = []
    total = 0
    for product in products:
        quantity = cart[str(product.pk)]
        line_total = product.price * quantity
        total += line_total
        items.append(
            {
                "product": product,
                "quantity": quantity,
                "line_total": line_total,
            }
        )

    return render(
        request,
        "shop/cart.html",
        {
            "items": items,
            "total": total,
        },
    )
# ***** CART VIEWS - END *****


# ***** EMAIL VIEWS - START *****
def build_invoice_email(order):
    """
    Build the invoice email for an order.
    """

    lines = []
    for item in order.items.all():
        lines.append(
            f"- {item.product.name} ({item.product.store.name}): "
            f"{item.quantity} x R{item.price_at_purchase} "
            f"= R{item.line_total}"
        )

    body = (
        f"Hello, {order.buyer.username}, \n\n"
        f"Thank you for your order!\nHere is your invoice: \n\n"
        f"Invoice #{order.pk}\n"
        + "\n".join(lines)
        + f"\n\nTotal: R{order.total}\n"
    )

    return EmailMessage(
        subject=f"__ISM invoice #{order.pk}",
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.buyer.email],
    )


# ***** EMAIL VIEWS - END *****


# CHECKOUT
@login_required
@require_POST
def checkout(request):
    """
    Turn the session cart into an order (POST only).
    Stock is checked, then the order, its items and the stock
    reduction are saved in one database transaction. Afterwards the
    cart is emptied and the invoice is emailed to the buyer.
    """

    cart = request.session.get("cart", {})

    if not cart:
        messages.error(request, "Your shopping cart is empty")
        return redirect("shop:cart_page")

    with transaction.atomic():
        products = Product.objects.filter(pk__in=list(cart))

        if not products:
            messages.error(request, "Some items are no longer available.")
            return redirect("shop:cart_page")

        for product in products:
            if cart[str(product.pk)] > product.stock:
                messages.error(request, f"Not enough stock of {product.name}.")
                return redirect("shop:cart_page")

        order = Order.objects.create(buyer=request.user)
        for product in products:
            quantity = cart[str(product.pk)]
            OrderItem.objects.create(
                order=order,
                product=product,
                price_at_purchase=product.price,
                quantity=quantity,
            )
            product.stock -= quantity
            product.save()

    request.session["cart"] = {}
    try:
        build_invoice_email(order).send()
    except OSError:
        messages.warning(
            request,
            "Your order was placed, but an invoice email could not be sent.",
        )
    return redirect("shop:invoice_confirmation", pk=order.pk)


# INVOICE
@login_required
def invoice_confirmation(request, pk):
    """
    Show an order's invoice to the buyer who placed it.
    """

    order = get_object_or_404(Order, pk=pk, buyer=request.user)
    return render(request, "shop/invoice_confirmation.html", {"order": order})
