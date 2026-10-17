import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from .models import ResetToken

from django.contrib.auth import get_user_model, login, logout, authenticate
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.core.validators import validate_email
from django.views.decorators.http import require_POST


User = get_user_model()

GROUPS_BY_TYPE = {
    "buyers": "Buyers",
    "vendors": "Vendors",
}

SESSION_TIMEOUT = 3600


# Create your views here.
def register(request):
    if request.method != "POST":
        return render(request, "accounts/register.html")

    username = request.POST.get("username", "").strip()
    password = request.POST.get("password", "")
    password_confirm = request.POST.get("password_confirm", "")
    email = request.POST.get("email", "").strip()
    account_type = request.POST.get("account_type")

    # List to hold errors as they arise (to be displayed after)
    errors = []

    # Username validation
    if not username:
        errors.append("Please enter a valid username.")

    if User.objects.filter(username=username).exists():
        errors.append("Username is already in use.")

    # Validate email
    try:
        validate_email(email)
    except ValidationError:
        errors.append("Please enter a valid email.")
    else:
        if User.objects.filter(email__iexact=email).exists():
            errors.append("Email is already in use.")

    # Validate password
    try:
        validate_password(password)
    except ValidationError as e:
        errors.extend(e.messages)
    if password != password_confirm:
        errors.append("Passwords do not match")

    # Group type
    if account_type in GROUPS_BY_TYPE:
        try:
            group = Group.objects.get(name=GROUPS_BY_TYPE[account_type])
        except Group.DoesNotExist:
            errors.append("Group does not exist.")
    else:
        errors.append("Please choose an account type.")

    # Fetch and diplay errors, if applicable
    if errors:
        return render(request, "accounts/register.html", {
            "errors": errors,
            "form_data": {
                "username": username,
                "email": email,
                "account_type": account_type,
            },
        })

    user = User.objects.create_user(
        username=username,
        password=password,
        email=email
    )
    user.groups.add(group)
    login(request, user)
    return redirect("shop:home")


def login_user(request):
    if request.method != "POST":
        return render(request, "accounts/login.html")

    username = request.POST.get("username", "").strip()
    password = request.POST.get("password", "")

    user = authenticate(request, username=username, password=password)
    if user is None:
        return render(request, "accounts/login.html", {
            "error": "Invalid username or password",
            "form_data": {"username": username},
        })

    login(request, user)
    request.session.set_expiry(SESSION_TIMEOUT)
    return redirect("shop:home")


@require_POST
def logout_user(request):
    logout(request)
    return redirect("accounts:login")

RESET_TOKEN_MINUTES = 15


def hash_token(raw_token):
    return hashlib.sha256(raw_token.encode()).hexdigest()


def get_valid_token(raw_token):
    """Return the matching unused, unexpired token, or None."""
    return (
        ResetToken.objects.select_related("user")
        .filter(
            token=hash_token(raw_token),
            used=False,
            expiry_date__gt=timezone.now(),
        )
        .first()
    )


def build_reset_email(user, reset_url):
    body = (
        f"Hi {user.username},\n\n"
        f"Here is your link to reset your password:\n{reset_url}\n\n"
        f"It expires in {RESET_TOKEN_MINUTES} minutes. If you didn't "
        f"request this, you can ignore this email.\n"
    )
    return EmailMessage(
        subject="CAPITAL ISM password reset",
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )


def forgot_password(request):
    if request.method != "POST":
        return render(request, "accounts/forgot_password.html")

    email = request.POST.get("email", "").strip()

    user = None
    if email:
        user = User.objects.filter(email__iexact=email).first()

    if user is not None:
        # Only the newest link should work
        ResetToken.objects.filter(user=user, used=False).update(used=True)

        raw_token = secrets.token_urlsafe(32)
        expires = timezone.now() + timedelta(minutes=RESET_TOKEN_MINUTES)
        ResetToken.objects.create(
            user=user,
            token=hash_token(raw_token),
            expiry_date=expires,
        )
        reset_url = request.build_absolute_uri(
            reverse("accounts:reset_password", args=[raw_token])
        )
        try:
            build_reset_email(user, reset_url).send()
        except OSError:
            # Stay silent: an error here would reveal that the email exists
            pass

    # Same message whether or not the email exists
    messages.success(
        request,
        "A reset link has been sent.",
    )
    return redirect("accounts:login")


def reset_password(request, token):
    reset_token = get_valid_token(token)
    if reset_token is None:
        messages.error(
            request,
            "That reset link is invalid or has expired. "
            "Please request a new one.",
        )
        return redirect("accounts:forgot_password")

    if request.method != "POST":
        return render(request, "accounts/reset_password.html")

    password = request.POST.get("password", "")
    password_confirm = request.POST.get("password_confirm", "")

    errors = []
    try:
        validate_password(password, reset_token.user)
    except ValidationError as e:
        errors.extend(e.messages)

    if password != password_confirm:
        errors.append("Passwords do not match.")

    if errors:
        return render(request, "accounts/reset_password.html", {
            "errors": errors,
        })

    with transaction.atomic():
        user = reset_token.user
        user.set_password(password)
        user.save()
        reset_token.used = True
        reset_token.save()

    messages.success(request, "Your password has been changed. Please log in.")
    return redirect("accounts:login")
