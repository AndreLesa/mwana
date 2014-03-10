from datetime import datetime, timedelta

from django.db.models import Q, Count

from rapidsms import router
from rapidsms.models import Contact

from threadless_router.router import Router

from mwana.apps.contactsplus.models import ContactType

from mwana.apps.smgl import const
from mwana.apps.smgl.models import FacilityVisit, ReminderNotification, Referral,\
    PregnantMother, AmbulanceResponse, SyphilisTreatment, Location

from mwana.apps.smgl.utils import get_district_facility_zone, get_district_super_users

from mwana.apps.smgl.keyword_handlers.referrals import cba_initiated, _pick_er_drivers, _pick_er_triage_nurse, _get_people_to_notify, is_from_facility, is_from_hospital
from rapidsms.errors import MessageSendingError
# reminders will be sent up to this amount late (if, for example the system
# was down.
SEND_REMINDER_LOWER_BOUND = timedelta(days=5)
SEND_AMB_OUTCOME_LOWER_BOUND = timedelta(hours=1)
SEND_SYPHILIS_REMINDER_LOWER_BOUND = timedelta(days=2)


def _set_router(router_obj=None):
    # Set the router to the global router it one is not provided
    if not router_obj:
        router.router = Router()
    else:
        router.router = router_obj


def send_followup_reminders(router_obj=None):
    """
    Next visit date from Pregnancy registration or Follow-up visit should
    be used to generate reminder for the next appointment.

    To: CBA
    On: 7 days before visit date
    """
    _set_router(router_obj)

    def _visits_to_remind():
        now = datetime.utcnow().date()
        reminder_threshold = now + timedelta(days=7)
        visits_to_remind = FacilityVisit.objects.filter(
            next_visit__gte=reminder_threshold - SEND_REMINDER_LOWER_BOUND,
            next_visit__lte=reminder_threshold,
            reminded=False,
            visit_type='anc')

        for v in visits_to_remind:
            if v.mother.birthregistration_set.count() == 0 and \
               v.is_latest_for_mother():
                yield v

    for v in _visits_to_remind():
        found_someone = False
        for c in v.mother.get_laycounselors():
            if c.default_connection:
                found_someone = True
                c.message(const.REMINDER_FU_DUE,
                          **{"name": v.mother.name,
                             "unique_id": v.mother.uid,
                             "loc": v.location.name})
                _create_notification("nvd", c, v.mother.uid)
        if found_someone:
            v.reminded = True
            v.save()


def send_non_emergency_referral_reminders(router_obj=None):
    return False
    """
    Reminder for non-emergency referral.

    To: CBA
    On: 7 days after referral is registered in the system

    Reminder is not necessary if mother shows up in the referral center.
    Also If we don't have the mother details (safe motherhood ID, Zone...)
    then the server does nothing.
    """
    _set_router(router_obj)

    now = datetime.utcnow()
    reminder_threshold = now - timedelta(days=7)
    referrals_to_remind = Referral.non_emergencies().filter(
        reminded=False,
        date__gte=reminder_threshold - SEND_REMINDER_LOWER_BOUND,
        date__lte=reminder_threshold
    ).filter(Q(mother_showed=None) | Q(mother_showed=False))
    referrals_to_remind = referrals_to_remind.exclude(mother=None)
    for ref in referrals_to_remind:
        found_someone = False
        for c in ref.mother.get_laycounselors():
            if c.default_connection:
                found_someone = True
                c.message(const.REMINDER_NON_EMERGENCY_REFERRAL,
                          **{"name": ref.mother.name,
                             "unique_id": ref.mother.uid,
                             "loc": ref.facility.name})
                _create_notification("nem_ref", c, ref.mother.uid)
        if found_someone:
            ref.reminded = True
            ref.save()


def send_emergency_referral_reminders(router_obj=None):
    """
    Reminder to collect outcomes for emergency referrals.

    To: Data Clerk operating at the referral facility
    On: 12 Hours after referral had been entered
    """
    _set_router(router_obj)
    now = datetime.utcnow()
    reminder_threshold = now - timedelta(hours=12)
    referrals_to_remind = Referral.objects.filter(
        reminded=False,
        responded=False,
        date__gte=reminder_threshold - SEND_REMINDER_LOWER_BOUND,
        date__lte=reminder_threshold
    ).exclude(mother_uid=None)
    for ref in referrals_to_remind:
        found_someone = False
        for c in ref.get_receiving_data_clerks():
            if c.default_connection:
                found_someone = True
                c.message(const.REMINDER_EMERGENCY_REFERRAL,
                          **{"unique_id": ref.mother_uid,
                             "date": ref.date.date(),
                             "loc": ref.referring_facility.name if ref.referring_facility else "?"})
                _create_notification("em_ref", c, ref.mother_uid)
        if found_someone:
            ref.reminded = True
            ref.save()

def send_upcoming_delivery_reminders_one_week(router_obj=None):
    """
    Reminders for upcoming delivery

    To: CBA
    On: 7 days prior to expected delivery day

    Cancel reminders after notification of birth.
    """
    _set_router(router_obj)
    now = datetime.utcnow().date()
    reminder_threshold = now + timedelta(days=7)
    moms_to_remind = PregnantMother.objects.filter(
        one_week_away_reminded=False,
        birthregistration__isnull=True,
        edd__gte=reminder_threshold - SEND_REMINDER_LOWER_BOUND,
        edd__lte=reminder_threshold
    )
    for mom in moms_to_remind:
        found_someone = False
        for c in mom.get_laycounselors():
            if c.default_connection:
                found_someone = True
                c.message(const.REMINDER_UPCOMING_DELIVERY,
                          **{"name": mom.name,
                             "unique_id": mom.uid,
                             "date": mom.edd.strftime('%d %b %Y')})
                _create_notification("edd_7", c, mom.uid)
        if found_someone:
            mom.one_week_away_reminded = True
            mom.save()

def send_upcoming_delivery_reminders_two_week(router_obj=None):
    """
    Reminders for upcoming delivery

    To: CBA
    On: 14 days prior to expected delivery day

    Cancel reminders after notification of birth.
    """
    _set_router(router_obj)
    now = datetime.utcnow().date()
    reminder_threshold = now + timedelta(days=14)
    moms_to_remind = PregnantMother.objects.filter(
        two_week_away_reminded=False,
        birthregistration__isnull=True,
        edd__gte=reminder_threshold - SEND_REMINDER_LOWER_BOUND,
        edd__lte=reminder_threshold
    )
    for mom in moms_to_remind:
        found_someone = False
        for c in mom.get_laycounselors():
            if c.default_connection:
                found_someone = True
                c.message(const.REMINDER_UPCOMING_DELIVERY,
                          **{"name": mom.name,
                             "unique_id": mom.uid,
                             "date": mom.edd.strftime('%d %b %Y')})
                _create_notification("edd_14", c, mom.uid)
        if found_someone:
            mom.two_week_away_reminded = True
            mom.save()

def send_upcoming_delivery_reminders_three_week(router_obj=None):
    """
    Reminders for upcoming delivery

    To: CBA
    On: 21 days prior to expected delivery day

    Cancel reminders after notification of birth.
    """
    _set_router(router_obj)
    now = datetime.utcnow().date()
    reminder_threshold = now + timedelta(days=21)
    moms_to_remind = PregnantMother.objects.filter(
        three_week_away_reminded=False,
        birthregistration__isnull=True,
        edd__gte=reminder_threshold - SEND_REMINDER_LOWER_BOUND,
        edd__lte=reminder_threshold
    )
    for mom in moms_to_remind:
        found_someone = False
        for c in mom.get_laycounselors():
            if c.default_connection:
                found_someone = True
                c.message(const.REMINDER_UPCOMING_DELIVERY,
                          **{"name": mom.name,
                             "unique_id": mom.uid,
                             "date": mom.edd.strftime('%d %b %Y')})
                _create_notification("edd_21", c, mom.uid)
        if found_someone:
            mom.three_week_away_reminded = True
            mom.save()

def send_upcoming_delivery_reminders_four_week(router_obj=None):
    """
    Reminders for upcoming delivery

    To: CBA
    On: 28 days prior to expected delivery day

    Cancel reminders after notification of birth.
    """
    _set_router(router_obj)
    now = datetime.utcnow().date()
    reminder_threshold = now + timedelta(days=28)
    moms_to_remind = PregnantMother.objects.filter(
        four_week_away_reminded=False,
        birthregistration__isnull=True,
        edd__gte=reminder_threshold - SEND_REMINDER_LOWER_BOUND,
        edd__lte=reminder_threshold
    )
    for mom in moms_to_remind:
        found_someone = False
        for c in mom.get_laycounselors():
            if c.default_connection:
                found_someone = True
                c.message(const.REMINDER_UPCOMING_DELIVERY,
                          **{"name": mom.name,
                             "unique_id": mom.uid,
                             "date": mom.edd.strftime('%d %b %Y')})
                _create_notification("edd_28", c, mom.uid)
        if found_someone:
            mom.four_week_away_reminded = True
            mom.save()

def send_upcoming_delivery_reminders_five_week(router_obj=None):
    """
    Reminders for upcoming delivery

    To: CBA
    On: 35 days prior to expected delivery day

    Cancel reminders after notification of birth.
    """
    _set_router(router_obj)
    now = datetime.utcnow().date()
    reminder_threshold = now + timedelta(days=35)
    moms_to_remind = PregnantMother.objects.filter(
        five_week_away_reminded=False,
        birthregistration__isnull=True,
        edd__gte=reminder_threshold - SEND_REMINDER_LOWER_BOUND,
        edd__lte=reminder_threshold
    )
    for mom in moms_to_remind:
        found_someone = False
        for c in mom.get_laycounselors():
            if c.default_connection:
                found_someone = True
                c.message(const.REMINDER_UPCOMING_DELIVERY,
                          **{"name": mom.name,
                             "unique_id": mom.uid,
                             "date": mom.edd.strftime('%d %b %Y')})
                _create_notification("edd_35", c, mom.uid)
        if found_someone:
            mom.five_week_away_reminded = True
            mom.save()

def send_first_postpartum_reminders(router_obj=None):
    """
    To: CBA
    On: 3 Days before first postpartum visit
    """
    _set_router(router_obj)

    def _visits_to_remind():
        now = datetime.utcnow().date()
        # Get visits 3 days from now for 1st visit
        reminder_threshold = now + timedelta(days=3)
        visits_to_remind = FacilityVisit.objects.filter(
            next_visit__gte=reminder_threshold - SEND_REMINDER_LOWER_BOUND,
            next_visit__lte=reminder_threshold,
            reminded=False,
            visit_type='pos'
        )
        # Check if first visit for mother

        for v in visits_to_remind:
            if v.mother.facility_visits.filter(visit_type='pos').count() == 0 and \
               v.is_latest_for_mother():
                yield v

    for v in _visits_to_remind():
        found_someone = False
        for c in v.mother.get_laycounselors():
            if c.default_connection:
                found_someone = True
                c.message(const.REMINDER_PP_DUE,
                          **{"name": v.mother.name,
                             "unique_id": v.mother.uid,
                             "loc": v.location.name,
                             "num": 3})
                _create_notification("pos", c, v.mother.uid)
        if found_someone:
            v.reminded = True
            v.save()


def send_second_postpartum_reminders(router_obj=None):
    """
    To: CBA
    On: 7 days before second postpartum visit
    """
    _set_router(router_obj)

    def _visits_to_remind():
        now = datetime.utcnow().date()
        # Get visits 7 days from now for 2nd visit
        reminder_threshold = now + timedelta(days=7)
        visits_to_remind = FacilityVisit.objects.filter(
            next_visit__gte=reminder_threshold - SEND_REMINDER_LOWER_BOUND,
            next_visit__lte=reminder_threshold,
            reminded=False,
            visit_type='pos'
        )
        # Check if second visit

        for v in visits_to_remind:
            if v.mother.facility_visits.filter(visit_type='pos').count() == 1 and \
               v.is_latest_for_mother():
                yield v

    for v in _visits_to_remind():
        found_someone = False
        for c in v.mother.get_laycounselors():
            if c.default_connection:
                found_someone = True
                c.message(const.REMINDER_PP_DUE,
                          **{"name": v.mother.name,
                             "unique_id": v.mother.uid,
                             "loc": v.location.name,
                             "num": 7})
                _create_notification("pos", c, v.mother.uid)
        if found_someone:
            v.reminded = True
            v.save()


def send_missed_postpartum_reminders(router_obj=None):
    """
    To: CBA
    On: 2 Days after a missing postpartum visit
    """
    _set_router(router_obj)

    def _visits_to_remind():
        now = datetime.utcnow().date()
        # Get visits -2 days from now if no POS registered
        reminder_threshold = now - timedelta(days=2)
        visits_to_remind = FacilityVisit.objects.filter(
            next_visit__gte=reminder_threshold - SEND_REMINDER_LOWER_BOUND,
            next_visit__lte=reminder_threshold,
            reminded=False,
            visit_type='pos'
        )
        # Check if missed

        for v in visits_to_remind:
            if v.mother.facility_visits.filter(visit_type='pos',
                                               visit_date=reminder_threshold)\
                .count() == 1 and \
               v.is_latest_for_mother():
                yield v

    for v in _visits_to_remind():
        found_someone = False
        for c in v.mother.get_laycounselors():
            if c.default_connection:
                found_someone = True
                c.message(const.REMINDER_PP_MISSED,
                          **{"name": v.mother.name,
                             "unique_id": v.mother.uid,
                             "loc": v.location.name})
                _create_notification("pos", c, v.mother.uid)
        if found_someone:
            v.reminded = True
            v.save()


def reactivate_user(router_obj=None):
    """
    Looks up Contacts that are set to is_active=False and have a return date
    of today. Activates user.
    """
    _set_router(router_obj)

    def _contacts_to_activate():
        now = datetime.utcnow().date()

        contacts_to_activate = Contact.objects.filter(
            return_date__gte=now - SEND_REMINDER_LOWER_BOUND,
            return_date__lte=now,
            is_active=False,
        )
        return contacts_to_activate

    for c in _contacts_to_activate():
        if c.default_connection:
            c.return_date = None
            c.is_active = True
            c.save()
            c.message(const.IN_REACTIVATE)


def send_syphillis_reminders(router_obj=None):
    """
    Next visit date from SyphilisTreatment should
    be used to generate reminder for the next appointment.

    To: CBA
    On: 2 days before visit date
    """
    _set_router(router_obj)

    def _visits_to_remind():
        now = datetime.utcnow().date()
        reminder_threshold = now + timedelta(days=2)
        visits_to_remind = SyphilisTreatment.objects.filter(
            next_visit_date__gte=reminder_threshold -
            SEND_SYPHILIS_REMINDER_LOWER_BOUND,
            next_visit_date__lte=reminder_threshold,
            reminded=False)

        for v in visits_to_remind:
            if v.is_latest_for_mother():
                yield v

    for v in _visits_to_remind():
        found_someone = False
        for c in v.mother.get_laycounselors():
            if c.default_connection:
                found_someone = True
                c.message(const.REMINDER_SYP_TREATMENT_DUE,
                          **{"name": v.mother.name,
                             "unique_id": v.mother.uid,
                             "loc": v.mother.location.name})
                _create_notification("syp", c, v.mother.uid)
        if found_someone:
            v.reminded = True
            v.save()


def send_inactive_notice_cbas(router_obj=None):
    """
    Automated Reminder for inactive users

    To: Active CBAs
    On: 60th day after Contact.latest_sms_date who are marked as
        Contact.is_active=True
    """
    _set_router(router_obj)
    cba = ContactType.objects.get(slug='cba')

    def _contacts_to_remind():
        now = datetime.utcnow().date()
        inactive_threshold = now - timedelta(days=60)
        contacts = Contact.objects.filter(types=cba, is_active=True)

        for c in contacts:
            last_sent = c.latest_sms_date
            if last_sent and last_sent.date() == inactive_threshold:
                yield c

    for c in _contacts_to_remind():
        if c.default_connection:
            c.message(const.INACTIVE_CONTACT, **{'days': 60})


def send_inactive_notice_data_clerks(router_obj=None):
    """
    Automated Reminder for inactive users

    To: Data Clerks
    On: 14th day after Contact.latest_sms_date who are marked as
        Contact.is_active=True
    """
    _set_router(router_obj)
    data_clerk = ContactType.objects.get(slug='dc')

    def _contacts_to_remind():
        now = datetime.utcnow().date()
        inactive_threshold = now - timedelta(days=14)
        contacts = Contact.objects.filter(types=data_clerk, is_active=True)

        for c in contacts:
            last_sent = c.latest_sms_date
            if last_sent and last_sent.date() == inactive_threshold:
                yield c

    for c in _contacts_to_remind():
        if c.default_connection:
            c.message(const.INACTIVE_CONTACT, **{'days': 14})


def send_expected_deliveries(router_obj=None):
    """
    Weekly reminder for expected deliveries

    To: In Charge Contacts
    On: Weekly
    """
    _set_router(router_obj)

    incharge = ContactType.objects.get(slug='incharge')
    now = datetime.utcnow().date()
    next_week = now + timedelta(days=7)

    contacts = Contact.objects.filter(is_active=True, types=incharge,
                                      location__pregnantmother__edd__gte=now,
                                      location__pregnantmother__edd__lte=next_week) \
        .annotate(num_edds=Count('location__pregnantmother'))

    for c in contacts:
        if c.default_connection:
            c.message(const.EXPECTED_EDDS, **{"edd_count": c.num_edds, })


def send_resp_reminders_20_mins(router_obj=None):
    # Send reminder for referrals that have no Resp after 20 mins
    _set_router(router_obj)
    now = datetime.utcnow()
    reminder_threshold = now - timedelta(minutes=60)
    twenty_mins_ago = now - timedelta(minutes=20)
    referrals_to_remind = Referral.objects.filter(
        has_response=False,
        responded=False,
        response_reminded=False,
        date__gte=reminder_threshold,
        date__lte=twenty_mins_ago,
        re_referral__isnull=True
    ).exclude(mother_uid=None)
    for referral in referrals_to_remind:
        found_someone = False
        people_to_notify = []
        if cba_initiated(referral.session.connection.contact):
            for person in _get_people_to_notify(referral, excluded=const.CTYPE_INCHARGE):
                people_to_notify.append(person)

        elif is_from_facility(referral.session.connection.contact):
            for person in _get_people_to_notify(referral, excluded=const.CTYPE_INCHARGE):
                people_to_notify.append(person)
            for person in _pick_er_drivers(referral.facility):
                people_to_notify.append(person)
        elif is_from_hospital(referral.session.connection.contact):
            for person in _pick_er_drivers(referral.from_facility):
                people_to_notify.append(person)
            for person in [_pick_er_triage_nurse(referral.facility)]:
                people_to_notify.append(person)

        for person in people_to_notify:
            if person.default_connection:
                found_someone = True
                past_reminders = ReminderNotification.objects.filter(
                    mother_uid=referral.mother_uid,
                    type="ref_resp_reminder",
                    recipient=person,
                    date__gte=twenty_mins_ago,
                    date__lte=now)
                #Ensure reminders are not sent twice
                if not past_reminders:
                    try:
                        person.message(const.REMINDER_REFERRAL_RESP,
                                       **{"unique_id": referral.mother_uid,
                                          "from_facility": referral.referring_facility.name if referral.referring_facility else "?"})
                    except MessageSendingError:
                        pass
                    else:
                        _create_notification(
                        "ref_resp_reminder", person, referral.mother_uid)
        if found_someone:
            referral.response_reminded = True
            referral.save()


def send_resp_reminders_super_user(router_obj=None):
    # Notify the super user  that a referral has gone unresponded to in the past
    # 30 minutes, This should come 30 minutes after referral and 10 minutes after
    # The actual destination users have been notified.
    _set_router(router_obj)
    now = datetime.utcnow()
    reminder_threshold = now - timedelta(hours=60)
    thirty_mins_ago = now - timedelta(minutes=30)
    # We need referral where the facility users have been reminded(response_reminded) but there still
    # is no response and there is still no refout(responded)
    referrals_to_remind = Referral.objects.filter(
        has_response=False,
        responded=False,
        super_user_notified=False,
        date__gte=reminder_threshold,
        date__lte=thirty_mins_ago,
    ).exclude(mother_uid=None)
    for ref in referrals_to_remind:
        if not ref.re_referral:
            found_someone = False
            ref_district, facility, zone = get_district_facility_zone(ref.facility)
            district_super_users = get_district_super_users(ref_district)
            for user in district_super_users:
                if user.default_connection:
                    found_someone = True
                    #Ensure that we don't send twice.
                    past_reminders = ReminderNotification.objects.filter(
                        mother_uid=ref.mother_uid,
                        type="super_user_ref_resp",
                        recipient=user,
                        date__gte=thirty_mins_ago,
                        date__lte=now)
                    if not past_reminders:
                        try:
                            user.message(const.REMINDER_SUPER_USER_REF,
                                      **{"unique_id": ref.mother_uid,
                                         "dest_facility": ref.facility,
                                         "from_facility": ref.from_facility if ref.from_facility else "?",
                                         "phone": ref.session.connection.identity})
                        except MessageSendingError:
                            pass
                        else:
                            _create_notification("super_user_ref_resp", user, ref.mother_uid)
            if found_someone:
                ref.super_user_notified = True
                ref.save()


def send_no_outcome_reminder(router_obj=None):
    # Send the outcome reminder at 12 hours.
    _set_router(router_obj)
    now = datetime.utcnow()
    reminder_threshold = now - timedelta(hours=48)
    twelve_hours_ago = now - timedelta(hours=12)
    referrals_to_remind = Referral.objects.filter(
        reminded=False,
        responded=False,
        has_response=True,
        date__gte=reminder_threshold,
        date__lte=twelve_hours_ago,
    ).exclude(mother_uid=None)

    for referral in referrals_to_remind:
        found_someone = False
        if not referral.re_referral:
            people_to_notify = []
            if cba_initiated(referral.session.connection.contact):
                for person in _get_people_to_notify(ref):
                    people_to_notify.append(person)
            elif is_from_facility(referral.session.connection.contact):
                for person in _pick_er_drivers(referral.facility):
                    people_to_notify.append(person)
                for person in [_pick_er_triage_nurse(referral.facility)]:
                    people_to_notify.append(person)
            elif is_from_hospital(referral.session.connection.contact):
                for person in [_pick_er_triage_nurse(referral.facility)]:
                    people_to_notify.append(person)

            for person in people_to_notify:
                if person.default_connection:
                    found_someone = True
                    person.message(const.AMB_OUTCOME_NO_OUTCOME,
                                   **{"unique_id": referral.mother_uid,
                                      "date": referral.date.strftime('%d %b %Y'),
                                      "from_facility": referral.from_facility})
                    _create_notification(
                        "no_refout_reminder_staff", person, referral.mother_uid)
            if found_someone:
                referral.reminded = True
                referral.save()

"""
def send_no_outcome_superusers_reminder(router_obj=None):

    #Send reminders to super users for Referrals
    #that have no Outcome and are @ 24 hours old


    def _responses_to_remind():
        now = datetime.utcnow()
        # Get AmbulanceResponses @ 24 hours old
        twenty_four_hours_ago = now - timedelta(hours=24)
        referrals_to_remind = Referral.objects.filter(
            has_response=True,
            responded=False,
            reminded=True,
            date__gte=twenty_four_hours_ago-timedelta(hours=12),
            date__lte=twenty_four_hours_ago,
            re_referral__isnull=True
        ).exclude(mother_uid=None)
        return referrals_to_remind

    users = Contact.objects.filter(is_super_user=True)
    users_per_district_super_users = []
    kalomo_district_super_users = []
    for user in users:
        district, facility, zone = get_district_facility_zone(user.location)
        if district == 'Kalomo District':
            kalomo_district_super_users.append(user)
        elif district == 'Choma District':
            choma_district_super_users.append(user)

    for referral in _responses_to_remind():
        receiving_facility = referral.facility
        district_users = None
        if referral.facility.district == 'Kalomo District':
            district_users = kalomo_district_super_users
        elif referral.facility.district == 'Choma District':
            district_users = choma_district_super_users

        for u in district_users:
            if u.default_connection:
                u.message(const.AMB_OUTCOME_NO_OUTCOME,
                          **{"unique_id": referral.mother_uid,
                             "date": referral.date.strftime("%d %B %Y")})
"""

def _create_notification(type, contact, mother_id):
    notif = ReminderNotification(type=type,
                                 recipient=contact,
                                 date=datetime.utcnow())
    notif.set_mother(mother_id)
    notif.save()
    return notif
