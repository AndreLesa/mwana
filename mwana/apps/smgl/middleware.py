# vim: ai ts=4 sts=4 et sw=4
from django.utils import timezone


class TimezoneMiddleware(object):
    def process_request(self, request):
        tz = request.session.get("tz_name")
        if tz:
            timezone.activate(tz)
        else:
            timezone.activate("Africa/Lusaka")