# Generated manually

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def seed_static_pages(apps, schema_editor):
    About = apps.get_model('pages', 'AboutPageContent')
    Contacts = apps.get_model('pages', 'ContactsPageContent')
    if not About.objects.filter(pk=1).exists():
        About.objects.create(
            pk=1,
            browser_title='About — BrainStorm',
            title_h1='BrainStorm',
            lede=(
                'An independent space for posts, discussion, and ideas. We publish work on technology,\n'
                'science, and whatever matters to authors and readers.'
            ),
            mission_heading='Why we’re here',
            mission_item_1='Honest conversation without noise: strong writing and clear comments.',
            mission_item_2='Practical tools for authors—publishing, discussion, and feedback.',
            mission_item_3='Room for different views, with respect for community guidelines.',
            facts_heading_hidden='At a glance',
            fact1_label='Format',
            fact1_value='Blog and feed with comments',
            fact2_label='Language',
            fact2_value='Primarily English',
            fact3_label='Audience',
            fact3_value='Readers and authors who care about depth, not just speed',
            cta_link_text='Contact us',
            cta_hint=' — collaboration and general feedback.',
        )
    if not Contacts.objects.filter(pk=1).exists():
        Contacts.objects.create(
            pk=1,
            browser_title='Contacts — BrainStorm',
            title_h1='Contacts',
            lede_before='We usually reply within ',
            lede_emphasis='1–2 business days',
            lede_after=(
                '. For urgent technical issues,\nsay so briefly in the email subject line.'
            ),
            channels_heading='How to reach us',
            email_key='Email',
            email_address='discover@brainstorm.com',
            email_note='General questions and suggestions',
            community_key='Community',
            community_text='Add social links here when you have them.',
            no_section_heading='What we don’t handle',
            no_section_body=(
                'Support for third-party personal accounts, unsolicited advertising without editorial approval,\n'
                'and bulk mail we didn’t ask for—we won’t respond to these.'
            ),
            footer_about_link_text='About',
        )


def unseed(apps, schema_editor):
    About = apps.get_model('pages', 'AboutPageContent')
    Contacts = apps.get_model('pages', 'ContactsPageContent')
    About.objects.filter(pk=1).delete()
    Contacts.objects.filter(pk=1).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AboutPageContent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('browser_title', models.CharField(default='About — BrainStorm', max_length=120)),
                ('title_h1', models.CharField(default='BrainStorm', max_length=200)),
                ('lede', models.TextField(default='')),
                ('mission_heading', models.CharField(default='Why we’re here', max_length=200)),
                ('mission_item_1', models.TextField(default='')),
                ('mission_item_2', models.TextField(default='')),
                ('mission_item_3', models.TextField(default='')),
                (
                    'facts_heading_hidden',
                    models.CharField(
                        default='At a glance',
                        help_text='Screen-reader only (visually hidden on site).',
                        max_length=120,
                    ),
                ),
                ('fact1_label', models.CharField(default='Format', max_length=120)),
                ('fact1_value', models.TextField(default='')),
                ('fact2_label', models.CharField(default='Language', max_length=120)),
                ('fact2_value', models.TextField(default='')),
                ('fact3_label', models.CharField(default='Audience', max_length=120)),
                ('fact3_value', models.TextField(default='')),
                ('cta_link_text', models.CharField(default='Contact us', max_length=120)),
                ('cta_hint', models.CharField(default=' — collaboration and general feedback.', max_length=255)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'updated_by',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='about_page_edits',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'About page content',
                'verbose_name_plural': 'About page content',
            },
        ),
        migrations.CreateModel(
            name='ContactsPageContent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('browser_title', models.CharField(default='Contacts — BrainStorm', max_length=120)),
                ('title_h1', models.CharField(default='Contacts', max_length=200)),
                ('lede_before', models.CharField(default='We usually reply within ', max_length=255)),
                ('lede_emphasis', models.CharField(default='1–2 business days', max_length=120)),
                ('lede_after', models.TextField(default='')),
                ('channels_heading', models.CharField(default='How to reach us', max_length=200)),
                ('email_key', models.CharField(default='Email', max_length=120)),
                ('email_address', models.CharField(default='discover@brainstorm.com', max_length=255)),
                ('email_note', models.CharField(default='General questions and suggestions', max_length=255)),
                ('community_key', models.CharField(default='Community', max_length=120)),
                ('community_text', models.TextField(default='')),
                ('no_section_heading', models.CharField(default='What we don’t handle', max_length=200)),
                ('no_section_body', models.TextField(default='')),
                ('footer_about_link_text', models.CharField(default='About', max_length=120)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'updated_by',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='contacts_page_edits',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'verbose_name': 'Contacts page content',
                'verbose_name_plural': 'Contacts page content',
            },
        ),
        migrations.RunPython(seed_static_pages, unseed),
    ]
