# -*- coding: utf-8 -*-
{
    'name': 'GlobeTrotter — Personalized Travel Planning Platform',
    'version': '1.0.0',
    'category': 'Services/Travel',
    'summary': 'Multi-city itinerary planner with activity discovery, dynamic budgeting, travel intelligence, and public sharing',
    'description': """
GlobeTrotter — Empowering Personalized Travel Planning
======================================================
GlobeTrotter is a full-featured travel planning platform built for Odoo Hackathon.

Key Features:
-------------
* Multi-City Itinerary Builder: Create, order, and customize stops with precise dates
* Activity Discovery & Assignment: Search activities by category, budget, duration and schedule to day plans
* Expense & Budget Engine: Dynamic calculation of total cost, cost per traveler, cost per day, category breakdowns
* Rule-Based Budget Intelligence: Transparent warnings for over-budget trips, expensive days, and lodging dominance
* Travel Balance Score: Real-time 0-100 score analyzing pacing, density, dwell time, and budget alignment
* Dual View Modes: Interactive Calendar grid & Vertical Timeline progression
* Presentation Showcase Mode: Polished executive summary suitable for live demos
* Secure Sharing & 1-Click Copy: Shareable read-only URLs with token access and instant itinerary duplication
* Multi-tenant Security: ACLs and Record Rules ensuring complete isolation between users
    """,
    'author': 'GlobeTrotter Engineering Team',
    'website': 'https://globetrotter.travel',
    'depends': ['base', 'web'],
    'data': [
        'security/globetrotter_security.xml',
        'security/ir.model.access.csv',
        'views/menu_views.xml',
        'views/city_views.xml',
        'views/activity_views.xml',
        'views/trip_views.xml',
        'views/hotel_views.xml',
        'views/expense_views.xml',
    ],
    'demo': [
        'data/seed_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'globetrotter/static/src/css/backend.css',
        ],
        'web.assets_frontend': [
            'globetrotter/static/src/css/style.css',
            'globetrotter/static/src/js/app.js',
        ],
    },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
