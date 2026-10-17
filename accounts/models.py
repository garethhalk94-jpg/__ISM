from django.conf import settings
from django.db import models


class ResetToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reset_tokens",
    )
    token = models.CharField(max_length=64)  # sha256 hash, never the raw token
    expiry_date = models.DateTimeField()
    used = models.BooleanField(default=False)

    def __str__(self):
        return f"Reset token for {self.user} (used: {self.used})"