from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    """Sitemap for static pages."""
    priority = 0.8
    changefreq = 'weekly'
    protocol = 'https'

    def items(self):
        return [
            'home:home',
            'home:primary_swaps',
            'home:secondary_swaps',
            'users:login',
            'users:signup',
            'payments:subscription',
        ]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        # Home page gets highest priority
        if item == 'home:home':
            return 1.0
        # Main swap pages get high priority
        elif item in ['home:primary_swaps', 'home:secondary_swaps']:
            return 0.9
        # Subscription page
        elif item == 'payments:subscription':
            return 0.8
        # Auth pages get lower priority
        else:
            return 0.6

    def changefreq(self, item):
        # Swap pages change more frequently
        if item in ['home:primary_swaps', 'home:secondary_swaps']:
            return 'daily'
        # Home page changes weekly
        elif item == 'home:home':
            return 'weekly'
        # Auth and subscription pages rarely change
        else:
            return 'monthly'


