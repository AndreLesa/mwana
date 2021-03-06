from django.core.management.base import BaseCommand
from scheduler.models import EventSchedule


class Command(BaseCommand):
    help = "Initialize static data for SMGL"

    def handle(self, *args, **options):
        # currently just the schedules

        daily_reminders = [
            "mwana.apps.smgl.reminders.send_followup_reminders",
            "mwana.apps.smgl.reminders.send_non_emergency_referral_reminders",
            #"mwana.apps.smgl.reminders.send_emergency_referral_reminders",
            "mwana.apps.smgl.reminders.send_no_outcome_reminder",
            "mwana.apps.smgl.reminders.send_upcoming_delivery_reminders_one_week",
            "mwana.apps.smgl.reminders.send_upcoming_delivery_reminders_two_week",
            "mwana.apps.smgl.reminders.send_upcoming_delivery_reminders_three_week",
            "mwana.apps.smgl.reminders.send_upcoming_delivery_reminders_four_week",
            "mwana.apps.smgl.reminders.send_upcoming_delivery_reminders_five_week",
            "mwana.apps.smgl.reminders.send_first_postpartum_reminders",
            "mwana.apps.smgl.reminders.send_second_postpartum_reminders",
            "mwana.apps.smgl.reminders.send_missed_postpartum_reminders",
            "mwana.apps.smgl.reminders.reactivate_user",
            #"mwana.apps.smgl.reminders.send_syphillis_reminders",
            "mwana.apps.smgl.reminders.send_inactive_notice_cbas",
            "mwana.apps.smgl.reminders.send_inactive_notice_data_clerks",
            "mwana.apps.smgl.reminders.send_no_outcome_superusers_reminder",
        ]
        weekly_reminders = [
            "mwana.apps.smgl.reminders.send_expected_deliveries"]
        #amb_reminders = ["mwana.apps.smgl.reminders.send_no_outcome_reminder"]
        referral_response_reminders = [
            "mwana.apps.smgl.reminders.send_resp_reminders_20_mins",
            "mwana.apps.smgl.reminders.send_resp_reminders_super_user"]

        _update_schedules(daily_reminders)
        _update_schedules(weekly_reminders, days=[0])
        #_update_schedules(amb_reminders, hours=[0, 12])

        _update_schedules(referral_response_reminders, hours=['*'], minutes=['*'])



def _update_schedules(paths, hours=[8], minutes=[0], days=[]):
    for func_abspath in paths:
        try:
            schedule = EventSchedule.objects.get(callback=func_abspath)
            schedule.hours = hours  # 8 in GMT is 10 in zambia
            schedule.minutes = minutes
            schedule.days_of_week = days
        except EventSchedule.DoesNotExist:
            schedule = EventSchedule(callback=func_abspath,
                                     hours=hours,
                                     minutes=minutes,
                                     days_of_week=days)
        schedule.save()
