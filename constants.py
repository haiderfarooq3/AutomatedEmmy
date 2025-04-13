"""Constants module for the Gmail Assistant application."""

# HTML character replacements for sanitizing text
HTML_REPLACEMENTS = {
    '<': '&lt;',
    '>': '&gt;',
    '&': '&amp;',
    '"': '&quot;',
    "'": '&#39;',
    '/': '&#x2F;',
    '`': '&#x60;',
    '=': '&#x3D;'
}

# User-friendly names for email categories
CATEGORY_DISPLAY_NAMES = {
    'important': 'Important',
    'main': 'Primary',
    'promotional': 'Promotions',
    'social': 'Social',
    'updates': 'Updates',
    'forums': 'Forums',
    'priority_inbox': 'Priority',
    'main_inbox': 'Primary',
    'urgent_alerts': 'Urgent Alerts',
    'basic_alerts': 'Notifications',
    'fyi_cc': 'FYI & CC',
    'billing_finance': 'Billing & Finance',
    'scheduling_calendars': 'Calendar Events',
    'marketing_promotions': 'Marketing',
    'team_internal': 'Team',
    'projects_clients': 'Projects & Clients',
    'needs_review': 'Needs Review',
    'rules_in_training': 'Training'
}

# Auto-response categories options
AUTO_RESPONSE_CATEGORIES = {
    'Priority Inbox Only': ['priority_inbox'],
    'All Important': ['priority_inbox', 'urgent_alerts', 'team_internal', 'projects_clients'],
    'Business Related': ['priority_inbox', 'billing_finance', 'team_internal', 'projects_clients'],
    'Everything': 'all',
    'Custom': []  # To be configured per user preference
}

# Auto-response waiting time options (in minutes)
AUTO_RESPONSE_WAITING_TIMES = {
    'Immediate': 0,
    'Quick': 2,
    'Standard': 5,
    'Delayed': 15,
    'Custom': 0  # To be configured per user preference
}
