"""Default English copy for About / Contacts (used by migrations and get_or_create)."""

ABOUT_DEFAULTS = {
    'browser_title': 'About — brainstorm.org',
    'title_h1': 'brainstorm.org',
    'lede': (
        'An independent space for posts, discussion, and ideas. We publish work on technology,\n'
        'science, and whatever matters to authors and readers.'
    ),
    'mission_heading': 'Why we’re here',
    'mission_item_1': 'Honest conversation without noise: strong writing and clear comments.',
    'mission_item_2': 'Practical tools for authors—publishing, discussion, and feedback.',
    'mission_item_3': 'Room for different views, with respect for community guidelines.',
    'facts_heading_hidden': 'At a glance',
    'fact1_label': 'Format',
    'fact1_value': 'Blog and feed with comments',
    'fact2_label': 'Language',
    'fact2_value': 'Primarily English',
    'fact3_label': 'Audience',
    'fact3_value': 'Readers and authors who care about depth, not just speed',
    'cta_link_text': 'Contact us',
    'cta_hint': ' — collaboration and general feedback.',
}

CONTACTS_DEFAULTS = {
    'browser_title': 'Contacts — brainstorm.org',
    'title_h1': 'Contacts',
    'lede_before': 'We usually reply within ',
    'lede_emphasis': '1–2 business days',
    'lede_after': '. For urgent technical issues,\nsay so briefly in the email subject line.',
    'channels_heading': 'How to reach us',
    'email_key': 'Email',
    'email_address': 'discover@brainstorm.org',
    'email_note': 'General questions and suggestions',
    'community_key': 'Community',
    'community_text': 'Add social links here when you have them.',
    'no_section_heading': 'What we don’t handle',
    'no_section_body': (
        'Support for third-party personal accounts, unsolicited advertising without editorial approval,\n'
        'and bulk mail we didn’t ask for—we won’t respond to these.'
    ),
    'footer_about_link_text': 'About',
}
