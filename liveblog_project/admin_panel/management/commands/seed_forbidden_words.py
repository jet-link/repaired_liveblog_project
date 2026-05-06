"""Seed sample forbidden words and patterns for content moderation."""
from django.core.management.base import BaseCommand

from admin_panel.models import ForbiddenWord, ForbiddenPattern


class Command(BaseCommand):
    help = 'Seed sample forbidden words and regex patterns (idempotent).'

    def handle(self, *args, **options):
        defaults = [
            # Obscenity (EN)
            ('shit', 'obscenity'),
            ('fuck', 'obscenity'),
            ('fucking', 'obscenity'),
            ('asshole', 'obscenity'),
            ('damn', 'obscenity'),
            ('bitch', 'obscenity'),
            ('crap', 'obscenity'),
            ('bastard', 'obscenity'),
            ('dick', 'obscenity'),
            ('idiot', 'obscenity'),
            ('stupid', 'obscenity'),
            ('moron', 'obscenity'),
            ('dumbass', 'obscenity'),
            ('pig', 'harassment'),
            # Obscenity (RU)
            ('идиот', 'obscenity'),
            ('дурак', 'obscenity'),
            ('сука', 'obscenity'),
            ('мразь', 'harassment'),
            ('скотина', 'harassment'),
            # Spam
            ('spam', 'spam'),
            ('viagra', 'spam'),
            ('casino', 'spam'),
            ('lottery', 'spam'),
            ('click here', 'spam'),
            ('buy now', 'spam'),
            ('free money', 'spam'),
            # Harassment / Abuse
            ('harassment', 'harassment'),
            ('abuse', 'abuse'),
            ('kill', 'abuse'),
            ('die', 'abuse'),
            ('hurt', 'abuse'),
            ('hate', 'abuse'),
        ]
        for word, reason in defaults:
            _, created = ForbiddenWord.objects.get_or_create(
                word=word,
                defaults={'reason': reason, 'is_active': True}
            )
            if created:
                self.stdout.write(f'  + {word} ({reason})')

        patterns = [
            (r'https?://[^\s]+', 'spam'),  # URLs
            (r'[s5\$][h4][i1!][t7]', 'obscenity'),  # shit-like obfuscation
            (r'[f4][u][c+][k]', 'obscenity'),  # fuck-like obfuscation
            (r'(.)\1{4,}', 'spam'),  # repeated chars (aaaaa)
            (r'\b(?:viagra|cialis|casino)\b', 'spam'),
            (r'(?:click|buy|free)\s+(?:here|now|money)', 'spam'),
        ]
        for pattern, reason in patterns:
            if not ForbiddenPattern.objects.filter(pattern=pattern).exists():
                ForbiddenPattern.objects.create(pattern=pattern, reason=reason, is_active=True)
                self.stdout.write(f'  + pattern {pattern[:40]}... ({reason})')

        self.stdout.write(self.style.SUCCESS('Seed complete.'))
