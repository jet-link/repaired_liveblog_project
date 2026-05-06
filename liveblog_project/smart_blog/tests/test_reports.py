"""Tests for Reports system."""

from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse

from django.contrib.auth import get_user_model
from smart_blog.models import Item, Comment, ContentReport
from smart_blog.services.reports import ReportService
from smart_blog.services.report_limits import can_user_report
from smart_blog.selectors import has_user_reported_item, has_user_reported_comment

User = get_user_model()


class ReportModelConstraintsTest(TestCase):
    """Test ContentReport constraints."""

    def setUp(self):
        self.user1 = User.objects.create_user("u1", "u1@test.com", "pass")
        self.user2 = User.objects.create_user("u2", "u2@test.com", "pass")
        self.item = Item.objects.create(
            author=self.user1,
            title="Test",
            text="Test",
            slug="test-report-1",
            is_published=True,
        )
        self.comment = Comment.objects.create(
            item=self.item,
            author=self.user2,
            text="Comment",
            is_draft=False,
        )

    def test_unique_user_item_report(self):
        """User cannot report same item twice (constraint forces update)."""
        ReportService.create_or_update_report(
            self.user2, item=self.item, reason="spam", details=""
        )
        report2, err = ReportService.create_or_update_report(
            self.user2, item=self.item, reason="abuse", details=""
        )
        self.assertIsNone(err)
        self.assertEqual(ContentReport.objects.filter(item=self.item, reporter=self.user2).count(), 1)
        self.assertEqual(report2.reason, "abuse")

    def test_report_updates_correctly(self):
        """Report updates reason and details when it exists."""
        ReportService.create_or_update_report(
            self.user2, item=self.item, reason="spam", details="old"
        )
        report, err = ReportService.create_or_update_report(
            self.user2, item=self.item, reason="harassment", details="new details"
        )
        self.assertIsNone(err)
        report.refresh_from_db()
        self.assertEqual(report.reason, "harassment")
        self.assertEqual(report.details, "new details")

    def test_cannot_report_own_content(self):
        """User cannot report own post or comment."""
        _, err = ReportService.create_or_update_report(
            self.user1, item=self.item, reason="spam", details=""
        )
        self.assertIsNotNone(err)
        self.assertIn("own", err.lower())

        _, err = ReportService.create_or_update_report(
            self.user2, comment=self.comment, reason="spam", details=""
        )
        self.assertIsNotNone(err)
        self.assertIn("own", err.lower())

    def test_rate_limit_works(self):
        """Rate limit 30/24h applies."""
        other_user = User.objects.create_user("u3", "u3@test.com", "pass")
        items = []
        for i in range(35):
            item = Item.objects.create(
                author=self.user1,
                title=f"Item {i}",
                text="x",
                slug=f"test-rate-{i}",
                is_published=True,
            )
            items.append(item)

        for i in range(30):
            ReportService.create_or_update_report(
                other_user, item=items[i], reason="spam", details=""
            )
        allowed, _ = can_user_report(other_user)
        self.assertFalse(allowed)

        # Old reports should not count
        ContentReport.objects.filter(reporter=other_user).update(
            created_at=timezone.now() - timedelta(hours=25)
        )
        allowed, _ = can_user_report(other_user)
        self.assertTrue(allowed)

    def test_check_constraint_exactly_one_target(self):
        """Report must have exactly one of item or comment (valid creates succeed)."""
        r, _ = ReportService.create_or_update_report(
            self.user2, item=self.item, reason="spam", details=""
        )
        self.assertIsNotNone(r)
        self.assertIsNone(r.comment_id)
        self.assertEqual(r.item_id, self.item.pk)
        r2, _ = ReportService.create_or_update_report(
            self.user1, comment=self.comment, reason="spam", details=""
        )
        self.assertIsNotNone(r2)
        self.assertIsNone(r2.item_id)
        self.assertEqual(r2.comment_id, self.comment.pk)


class ReportSelectorsTest(TestCase):
    """Test selectors."""

    def setUp(self):
        self.user = User.objects.create_user("u1", "u1@test.com", "pass")
        self.other = User.objects.create_user("u2", "u2@test.com", "pass")
        self.item = Item.objects.create(
            author=self.other,
            title="Test",
            text="T",
            slug="test-sel-1",
            is_published=True,
        )
        self.comment = Comment.objects.create(
            item=self.item,
            author=self.other,
            text="C",
            is_draft=False,
        )

    def test_has_user_reported_item(self):
        self.assertFalse(has_user_reported_item(self.user, self.item))
        ReportService.create_or_update_report(self.user, item=self.item, reason="spam", details="")
        self.assertTrue(has_user_reported_item(self.user, self.item))

    def test_has_user_reported_comment(self):
        self.assertFalse(has_user_reported_comment(self.user, self.comment))
        ReportService.create_or_update_report(
            self.user, comment=self.comment, reason="spam", details=""
        )
        self.assertTrue(has_user_reported_comment(self.user, self.comment))
