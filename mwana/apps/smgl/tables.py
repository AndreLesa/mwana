import datetime
from django.core.urlresolvers import reverse
from django.template import defaultfilters
from django.utils import timezone

from djtables import Table, Column
from djtables.column import DateColumn
from smsforms.models import XFormsSession
from .models import BirthRegistration, DeathRegistration, FacilityVisit, PregnantMother, ToldReminder
from utils import get_time_range, get_district_facility_zone
from rapidsms.contrib.messagelog.models import Message



class NamedColumn(Column):

    """
    A custom Column class that allows for a non-field based Column Name
    """

    def __init__(self, col_name=None, *args, **kwargs):
        super(NamedColumn, self).__init__(*args, **kwargs)
        self._col_name = col_name
        self._header_class = "upper"

    def __unicode__(self):
        return self._col_name or self.name


class AwareDateColumn(DateColumn):

    def render(self, cell, *args, **kwargs):
        value = self.value(cell)
        if value:
            #date_time = value
            try:
                date_time = value.astimezone(timezone.get_current_timezone())
            except AttributeError:
                date_time = value
        else:
            return ''
        return defaultfilters.date(
            date_time,
            self._format)


class PregnantMotherTable(Table):
    created_date = AwareDateColumn(format="Y m d H:i ")
    uid = Column(link=lambda cell: reverse(
        "mother-history", args=[cell.object.id]))
    location = Column()
    edd = AwareDateColumn(format="d/m/Y")
    risks = Column(value=lambda cell: ", ".join([x.upper()
                                                 for x in cell.object.get_risk_reasons(
                                                 )]),
                   sortable=False)
    Status = Column(value=lambda cell:"Delivered" if cell.object.has_delivered else 'Not Delivered')

    class Meta:
        order_by = "-created_date"


class MotherMessageTable(Table):
    date = AwareDateColumn(format="Y m d H:i ")
    msg_type = NamedColumn(col_name="Type",
                           value=lambda cell: cell.object.text.split(
                               ' ')[0].upper(),
                           sortable=False)
    contact = NamedColumn(col_name="Sender")
    facility = Column(
        value=lambda cell: cell.object.contact.location.name if cell.object.contact else '')
    text = NamedColumn(col_name="Message")

    class Meta:
        order_by = "-date"

class ErrorMessageTable(Table):
    date = AwareDateColumn(format="Y m d H:i ")
    msg_type = NamedColumn(col_name="Type",
                           value=lambda cell: cell.object.text.split(
                               ' ')[0].upper(),
                           sortable=False)
    contact = NamedColumn(col_name="Sender")
    facility = Column(
        value=lambda cell: cell.object.contact.location.name if cell.object.contact else '')
    text = NamedColumn(col_name="Message", value=lambda cell:cell.object.text)
    error_response = NamedColumn(col_name="Error Resp", value=lambda cell: get_response(cell.object))


    class Meta:
        order_by = "-date"

class NotificationsTable(Table):
    date = AwareDateColumn(format="Y m d H:i ")
    name = Column(
        value=lambda cell: cell.object.connection.contact if cell.object.connection else '', sortable=False)
    number = Column(
        value=lambda cell: cell.object.connection.identity if cell.object.connection else '', sortable=False)
    facility = Column(
        value=lambda cell: cell.object.contact.location.name if cell.object.contact else '')
    text = NamedColumn(col_name="Message")

    class Meta:
        order_by = "-date"


class ReferralsTable(Table):
    date = AwareDateColumn(format="Y m d H:i ")
    from_facility = Column()
    sender = Column(
        value=lambda cell: cell.object.session.connection.contact if cell.object.session.connection else '', sortable=False)
    number = Column(
        value=lambda cell: cell.object.session.connection.identity if cell.object.session.connection else '', sortable=False)
    response = Column(
        value=lambda cell: "Yes" if cell.object.has_seen_response else "No", sortable=False)
    confirm_amb = Column(
        value=lambda cell: cell.object.ambulance_response, sortable=False)
    outcome = Column(sortable=False)
    message = Column(
        value=lambda cell: cell.object.session.message_incoming.text if cell.object.session.message_incoming else '',
        sortable=False)
    flag = Column(value=lambda cell: '<div class="status {0}">&nbsp;</div>'.format(
        cell.object.flag), sortable=False, safe=True)

    class Meta:
        order_by = "-date"


class StatisticsTable(Table):
    location = Column(header_class="location")
    pregnancies = Column()
    births_com = NamedColumn(col_name="COM")
    births_fac = NamedColumn(col_name="FAC")
    births_total = NamedColumn(col_name="Total")
    infant_deaths_com = NamedColumn(col_name="COM")
    infant_deaths_fac = NamedColumn(col_name="FAC")
    infant_deaths_total = NamedColumn(col_name="Total")
    mother_deaths_com = NamedColumn(col_name="COM")
    mother_deaths_fac = NamedColumn(col_name="FAC")
    mother_deaths_total = NamedColumn(col_name="Total")
    anc_total = NamedColumn(col_name='ANC Total')
    pos_total = NamedColumn(col_name='POS Total')
    """
    anc1 = NamedColumn(col_name="1 ANC")
    anc2 = NamedColumn(col_name="2 ANCs")
    anc3 = NamedColumn(col_name="3 ANCs")
    anc4 = NamedColumn(col_name="4 ANCs")
    pos1 = NamedColumn(col_name="1 POS")
    pos2 = NamedColumn(col_name="2 POS")
    pos3 = NamedColumn(col_name="3 POS")
    """

class StatisticsLinkTable(StatisticsTable):

    location = Column(link=lambda cell:
                      reverse("district-stats",
                              args=[cell.object['location_id']]
                              ),
                      header_class="location"
                      )
    pregnancies = Column()
    births_com = NamedColumn(col_name="COM")
    births_fac = NamedColumn(col_name="FAC")
    births_total = NamedColumn(col_name="Total")
    infant_deaths_com = NamedColumn(col_name="COM")
    infant_deaths_fac = NamedColumn(col_name="FAC")
    infant_deaths_total = NamedColumn(col_name="Total")
    mother_deaths_com = NamedColumn(col_name="COM")
    mother_deaths_fac = NamedColumn(col_name="FAC")
    mother_deaths_total = NamedColumn(col_name="Total")
    anc_total = NamedColumn(col_name='ANC Total')
    pos_total = NamedColumn(col_name='POS Total')
    """
    anc1 = NamedColumn(col_name="1 ANC")
    anc2 = NamedColumn(col_name="2 ANCs")
    anc3 = NamedColumn(col_name="3 ANCs")
    anc4 = NamedColumn(col_name="4 ANCs")
    pos1 = NamedColumn(col_name="1 POS")
    pos2 = NamedColumn(col_name="2 POS")
    pos3 = NamedColumn(col_name="3 POS")
    """


class ReminderStatsTable(Table):
    reminder_type = NamedColumn(col_name="Reminder Type")
    number = NamedColumn(col_name="# MOTHERS")
    scheduled_reminders = NamedColumn(col_name='Scheduled')
    sent_reminders = NamedColumn(col_name='Sent')
    reminded = NamedColumn(col_name='Reminded')
    birth_anc_pnc_ref = NamedColumn(col_name='ANC/PNC')
    told_and_showed = NamedColumn(col_name='TOLD & SHOWED')
    showed_on_time = NamedColumn(col_name='SHOWED W/O TOLD')

class ReminderStatsTableSMAG(Table):
    reminder_type = NamedColumn(sortable=False, col_name="Reminder Type")
    smag_number = NamedColumn(col_name="SCHEDULED VISITS")
    smag_scheduled_reminders = NamedColumn(col_name='Scheduled (SMAG)')
    smag_sent_reminders = NamedColumn(col_name='Sent (SMAG)')
    smag_tolds = NamedColumn(col_name='TOLD RECEIVED')
    response_rate = NamedColumn(col_name='Response rate')

class SummaryReportTable(Table):
    data = Column(sortable=False)
    value = Column(sortable=False)

message_types = {
    'REG': 'Pregnancy',
    'REFOUT': 'Ref. Outcome',
    'RESP': 'Ref. Response',
    'REFER': 'Referral',
             'LOOK': 'Lookup',
             'FUP': 'ANC',
             'JOIN': 'User',
             'PP': 'PNC'
}


def get_msg_type(message):
    if message.direction == "I":
        keyword = message.text.split(' ')[0]
        try:
            title = message_types[keyword.upper()]
        except KeyError:
            title = keyword
        finally:
            return title
    else:
        # This will need to be filled a little more to so that we can
        # distinguish between valid and error messages.
        try:
            XFormsSession.objects.get(message_outgoing=message, has_error=True)
        except XFormsSession.DoesNotExist:
            return 'Response'
        else:
            return 'Error Response'


class CanNotGetKeywordMotherID(Exception):
    pass


def get_keyword_mother_id(message):

    if not message.text.strip():
        raise CanNotGetKeywordMotherID
    try:
        keyword = message.text.split(' ')[0]
        mother_id = message.text.split(' ')[1]
    except IndexError:
        raise CanNotGetKeywordMotherID
    return keyword.upper(), mother_id


def get_facility_visit(mother_id, limit_time):
    # Returns a facility visit given a motherid and some time to limit against
    time_range = get_time_range(limit_time, seconds=3600)
    try:
        facility_visit = FacilityVisit.objects.filter(
            mother__uid=mother_id, created_date__range=time_range)[0]
    except IndexError:
        return None
    else:
        return facility_visit


def get_pregnant_mother(mother_id, limit_time):
    time_range = get_time_range(limit_time, seconds=3600)
    try:
        pregnant_mother = PregnantMother.objects.filter(
            uid=mother_id, created_date__range=time_range)[0]
    except IndexError:
        return None
    else:
        return pregnant_mother


def get_death_registration(mother_id):
    try:
        death_registration = DeathRegistration.objects.filter(
            unique_id=mother_id)[0]
    except IndexError:
        return None
    else:
        return death_registration


def get_told_reminders(mother_id):
    try:
        told_reminder = ToldReminder.objects.filter(mother__uid=mother_id)[0]
    except IndexError:
        return None
    else:
        return told_reminder


def get_birth_registrations(mother_id):
    try:
        birth = BirthRegistration.objects.filter(mother__uid=mother_id)[0]
    except IndexError:
        return None
    else:
        return birth


def map_message_fields(message):
    # Returns an incoming message text with the various fields mapped to value. Some of the keywords have database objects that easily map to
    # session id and we can easily find the associated object, others require
    # a little more work.
    text = message.text
    # only process the incoming messages, outgoing messages will continue just
    # using the message text.
    if message.direction == "I":
        database_obj = None
        try:
            keyword, mother_id = get_keyword_mother_id(message)
        except CanNotGetKeywordMotherID:
            return text
        if keyword == 'FUP' or keyword == 'PP':
            database_obj = get_facility_visit(mother_id, message.date)
        elif keyword == 'REG':
            database_obj = get_pregnant_mother(mother_id, message.date)
        elif keyword == 'DEATH':
            database_obj = get_death_registration(mother_id)
        elif keyword == 'TOLD':
            database_obj = get_told_reminders(mother_id)
        elif keyword == "BIRTH":
            database_obj = get_birth_registrations(mother_id)

        if database_obj:
            text = database_obj.get_field_value_mapping()

    return text


class SMSRecordsTable(Table):

    date = AwareDateColumn(format="Y m d H:i")
    phone_number = NamedColumn(
        col_name="Phone Number", value=lambda cell: cell.object.connection.identity)
    user_name = NamedColumn(link=lambda cell: reverse("sms-user-history", args=[
                            cell.object.connection.contact.id]), col_name="User Name", value=lambda cell: cell.object.connection.contact.name.title())
    msg_type = NamedColumn(col_name="Type",
                           value=lambda cell: get_msg_type(cell.object),
                           sortable=False
                           )
    facility = Column(
        value=lambda cell: cell.object.connection.contact.location if cell.object.connection.contact else '')
    text = NamedColumn(
        col_name="Message", value=lambda cell: map_message_fields(cell.object))

    class Meta:
        order_by = "-date"


class ANCDeliveryTable(Table):
    location = NamedColumn(col_name='Location')
    pregnancies = NamedColumn(col_name='Pregnant Women')
    anc2 = NamedColumn(col_name='2 ANC')
    anc3 = NamedColumn(col_name='3 ANC')
    anc4 = NamedColumn(col_name='4+ ANC')
    facility = NamedColumn(col_name='Facility')
    home = NamedColumn(col_name='Home')
    unknown = NamedColumn(col_name='Unregistered')
    gestational_age = NamedColumn(col_name='Gestational Age @ First ANC')


class PNCReportTable(Table):
    location = NamedColumn(col_name='Location')
    registered_deliveries = NamedColumn(col_name='Registered Deliveries')
    facility = NamedColumn(col_name='Facility')
    home = NamedColumn(col_name='Community')
    six_day_pnc = NamedColumn(col_name='6 Day PNC')
    six_week_pnc = NamedColumn(col_name='6 Week PNC')
    complete_pnc = NamedColumn(col_name='Complete PNC')


class ReferralReportTable(Table):
    referrals = NamedColumn(col_name='Referrals')
    referral_responses = NamedColumn(col_name='Ref. W/ Resp')
    referral_response_outcome = NamedColumn(
        col_name='Ref. W/ Resp-Out.')
    transport_by_ambulance = NamedColumn(col_name='Trans. Amb')
    average_turnaround_time = NamedColumn(col_name='Avg. Time')
    most_common_reason = NamedColumn(col_name='Common Ref. Reason')


class UserReport(Table):
    clinic_workers_registered = NamedColumn(col_name='Registered')
    clinic_workers_active = NamedColumn(col_name='Active')
    clinic_workers_error_rate = NamedColumn(
        col_name='Error Rate')
    data_clerks_registered = NamedColumn(col_name='Registered')
    data_clerks_active = NamedColumn(col_name='Active')
    data_clerks_error_rate = NamedColumn(col_name='Error Rate')
    cbas_registered = NamedColumn(col_name='Registered')
    cbas_active = NamedColumn(col_name='Active')
    cbas_error_rate = NamedColumn(col_name='Error Rate')


class SMSUsersTable(Table):
    created_date = DateColumn(format="Y m d ")
    name = Column(link=lambda cell: reverse("sms-user-history",
        args=[cell.object.id]))
    number = Column(
        value=lambda cell: cell.object.default_connection.identity if cell.object.default_connection else '',
        sortable=False)
    user_type = NamedColumn(
        name='USER TYPE',
        value=lambda cell: ", ".join([contact_type.name for contact_type in cell.object.types.all()]),
        sortable=False)
    facility = Column(
        value=lambda cell:cell.object.get_current_facility())
    last_active = DateColumn(value=lambda cell: cell.object.latest_sms_date,
                             format="Y m d H:i",
                             sortable=False)
    location = Column(
        value=lambda cell: cell.object.location.name if cell.object.location else '',)
    active_status = Column(value=lambda cell: '<div class="status {0}">&nbsp;</div>'.format(
        cell.object.active_status), sortable=False, safe=True)

    class Meta:
        order_by = "-created_date"


class SMSUserMessageTable(Table):
    date = AwareDateColumn(format="Y m d H:i")
    msg_type = NamedColumn(col_name="Type",
                           value=lambda cell: cell.object.text.split(
                               ' ')[0].upper(),
                           sortable=False
                           )
    text = NamedColumn(col_name="Message")

    class Meta:
        order_by = "-date"


def find_help_message(help_request):
    #we find the help message that was sent by the user by looking
    #at the messages received from them within one minute of the
    #generated help request.
    messages = Message.objects.filter(connection=help_request.requested_by)
    one_min_before = help_request.requested_on - datetime.timedelta(minutes=1)
    one_min_after = help_request.requested_on + datetime.timedelta(minutes=1)
    help_messages = messages.filter(text__icontains='help',
        date__gte=one_min_before,
        date__lte=one_min_after,
        direction='I')

    try:
        help_message = help_messages[0]
    except IndexError:
        return 'Help'
    else:
        return help_message.text

class HelpRequestTable(Table):
    id = Column(link=lambda cell: reverse(
        "help-manager", args=[cell.object.id]))
    requested_on = AwareDateColumn(format="Y m d H:i ")
    phone = Column(value=lambda cell: cell.object.requested_by.identity)
    name = Column(value=lambda cell:
                  cell.object.requested_by.contact.name if cell.object.requested_by.contact else '')
#    title = Column(value=lambda cell: ", ".join([x for x in cell.object.requested_by.contact.types.all()]) if cell.object.requested_by.contact else '',
#                   sortable=False)
    facility = Column(
        value=lambda cell: cell.object.requested_by.contact.location if cell.object.requested_by.contact else '')
    additional_text = NamedColumn(col_name='message', value=lambda cell:find_help_message(cell.object))
    resolved_by = Column(
        value=lambda cell: cell.object.resolved_by or 'Unresolved')
    status = Column(value=lambda cell: '<div class="status {0}">&nbsp;</div>'.format(
        cell.object.get_status_display), sortable=False, safe=True)

    class Meta:
        order_by = "-requested_on"

def get_response(message):
    #Get the response that was most likely sent out as a response to an
    #incoming message.
    try:
        session = message.message_incoming.all()[0]
    except IndexError:
        #Look a little deeper for the outgoing message that might have
        #generated by this message
        secs = datetime.timedelta(seconds=30) #Try to find any outgoing message that
                                        #that might have generated the response
        connection = message.connection
        try:
            message = connection.message_set.filter(
            date__range=[message.date, message.date+secs],
            direction="O")[0]
        except IndexError:
            return None
        else:
            return message.text
    else:
        return session.message_outgoing.text if session.message_outgoing else ""

class ErrorTable(Table):
    date = AwareDateColumn(format='Y m d H:i ')
    type = NamedColumn(col_name="Type",
                      value=lambda cell: get_msg_type(cell.object),
                      sortable=False
                    )
    user_number = NamedColumn(link=lambda cell: reverse("error-history", args=[
        cell.object.connection.contact.id
        ]),
    col_name="User Number",
    value=lambda cell: cell.object.connection.identity
    )
    user_name = NamedColumn(link=lambda cell: reverse("error-history", args=[
        cell.object.connection.contact.id
        ]),
    col_name="User Name",
    value=lambda cell: cell.object.connection.contact.name
    )

    user_type = NamedColumn(col_name="User Type", value=lambda cell: ", ".join(
        [x.name for x in cell.object.connection.contact.types.all()]))
    district = Column(value=lambda cell: cell.object.connection.contact.get_current_district()
                      if cell.object.connection.contact else '')
    facility = Column(
        value=lambda cell: cell.object.connection.contact.location if cell.object.connection.contact else '')
    text = NamedColumn(
        col_name="Message", value=lambda cell: cell.object.text)
    error_response = NamedColumn(col_name="Error Resp", value=lambda cell: get_response(cell.object))


class SMSRecordsTable(Table):
    date = AwareDateColumn(format="Y m d H:i")
    type = NamedColumn(col_name="Type",
                      value=lambda cell: get_msg_type(cell.object),
                      sortable=False
                    )
    phone_number = NamedColumn(
        col_name="Phone Number", value=lambda cell: cell.object.connection.identity)
    user_name = NamedColumn(link=lambda cell: reverse("sms-user-history", args=[
                            cell.object.connection.contact.id]), col_name="User Name", value=lambda cell: cell.object.connection.contact.name.title())
    user_type = Column(value=lambda cell: ", ".join(
        [x.name for x in cell.object.connection.contact.types.all()]))

    facility = Column(
        value=lambda cell: cell.object.connection.contact.location if cell.object.connection.contact else '')
    text = NamedColumn(
        col_name="Message", value=lambda cell: map_message_fields(cell.object))

    class Meta:
        order_by = "-date"
