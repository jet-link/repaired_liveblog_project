"""Report service for create/update/cancel reports."""

from django.db import IntegrityError

from smart_blog.models import ContentReport

VALID_REASONS = set(dict(ContentReport.REASON_CHOICES))
MIN_OTHER_DETAILS = 2
MAX_OTHER_DETAILS = 300


class ReportService:
    @staticmethod
    def create_or_update_report(user, item=None, comment=None, reason=None, reasons=None, details=""):
        """
        Create or update a report. Exactly one of item or comment must be provided.
        Accepts reason (single) or reasons (list). If reasons provided, uses it; else [reason].
        Returns (report, error_message). error_message is None on success.
        """
        if not user or not user.is_authenticated:
            return None, "Authentication required."

        if (item is None and comment is None) or (item is not None and comment is not None):
            return None, "Exactly one of item or comment must be provided."

        reasons_list = list(reasons) if reasons else ([reason] if reason else [])
        reasons_list = [r for r in reasons_list if r and str(r).strip()]

        if not reasons_list:
            return None, "At least one reason is required."

        for r in reasons_list:
            if r not in VALID_REASONS:
                return None, f"Invalid reason: {r}"

        has_other = ContentReport.REASON_OTHER in reasons_list
        if has_other:
            details_stripped = (details or "").strip()
            if len(details_stripped) < MIN_OTHER_DETAILS or len(details_stripped) > MAX_OTHER_DETAILS:
                return None, "Please write other reasons."

        # Self-report check
        if item and item.author_id == user.pk:
            return None, "You cannot report your own post."
        if comment and comment.author_id == user.pk:
            return None, "You cannot report your own comment."

        primary_reason = reasons_list[0]
        defaults = {
            "reason": primary_reason,
            "reasons": reasons_list,
            "details": (details or "").strip(),
            "status": ContentReport.STATUS_OPEN,
            "admin_hidden": False,  # Re-show in admin when user updates reason after Clear
        }

        if item is not None:
            report, created = ContentReport.objects.update_or_create(
                reporter=user,
                item=item,
                defaults={"comment": None, **defaults},
            )
        else:
            report, created = ContentReport.objects.update_or_create(
                reporter=user,
                comment=comment,
                defaults={"item": None, **defaults},
            )

        if not created:
            report.touch_updated()  # Refresh updated_at from model (user changed report)

        return report, None

    @staticmethod
    def get_user_report(user, item=None, comment=None):
        """Return the user's existing report for the given item or comment, or None."""
        if not user or not user.is_authenticated:
            return None
        if item is not None and comment is None:
            return ContentReport.objects.filter(item=item, reporter=user).first()
        if comment is not None and item is None:
            return ContentReport.objects.filter(comment=comment, reporter=user).first()
        return None

    @staticmethod
    def cancel_report(user, report):
        """
        Delete the report if the user is the reporter.
        Returns (success: bool, error_message: str | None).
        """
        if not user or not user.is_authenticated:
            return False, "Authentication required."
        if report.reporter_id != user.pk:
            return False, "You can only cancel your own report."
        report.delete()
        return True, None
