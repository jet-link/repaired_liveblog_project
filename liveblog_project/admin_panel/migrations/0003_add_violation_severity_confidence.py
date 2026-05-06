# Generated for User Trust Score System

from django.db import migrations, models

REASON_TO_SEVERITY = {
    'spam': 'low',
    'obscenity': 'medium',
    'other': 'medium',
    'abuse': 'high',
    'harassment': 'high',
}
REASON_DEFAULT_RATING = {
    'abuse': 0.92,
    'harassment': 0.88,
    'obscenity': 0.87,
    'spam': 0.75,
    'other': 0.80,
}


def backfill_severity_confidence(apps, schema_editor):
    ContentViolation = apps.get_model('admin_panel', 'ContentViolation')
    for v in ContentViolation.objects.all():
        severity = REASON_TO_SEVERITY.get(v.reason, 'medium')
        confidence = 1.0
        word = (v.detected_word or '').strip()
        if word.startswith('AI:'):
            parts = word[3:].split('=')
            if len(parts) >= 2:
                try:
                    confidence = max(0.0, min(1.0, float(parts[1])))
                except (ValueError, TypeError):
                    pass
        else:
            confidence = REASON_DEFAULT_RATING.get(v.reason, 0.80)
        ContentViolation.objects.filter(pk=v.pk).update(severity=severity, confidence=confidence)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("admin_panel", "0002_content_moderation_models"),
    ]

    operations = [
        migrations.AddField(
            model_name="contentviolation",
            name="severity",
            field=models.CharField(default="medium", max_length=20),
        ),
        migrations.AddField(
            model_name="contentviolation",
            name="confidence",
            field=models.FloatField(default=1.0),
        ),
        migrations.RunPython(backfill_severity_confidence, noop),
    ]
