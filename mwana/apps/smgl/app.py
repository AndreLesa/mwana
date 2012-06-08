import datetime
import logging
from rapidsms.apps.base import AppBase

from .models import XFormKeywordHandler, FacilityVisit

from mwana.apps.agents.handlers.agent import get_unique_value
from mwana.apps.locations.models import Location, LocationType
from mwana.apps.contactsplus.models import ContactType
from mwana.apps.smgl.models import PregnantMother, AmbulanceRequest
from mwana import const

from rapidsms.models import Contact
from rapidsms.messages import OutgoingMessage

from dimagi.utils.modules import to_function

from django.core.exceptions import ObjectDoesNotExist
from smscouchforms.signals import xform_saved_with_session

# In RapidSMS, message translation is done in OutgoingMessage, so no need
# to attempt the real translation here.  Use _ so that makemessages finds
# our text.
_ = lambda s: s

#Values that are used to indicate 'no answer' in fields of a form (especially in the case of optional values)
NONE_VALUES = ['none', 'n', None]

# Begin Translatable messages
FACILITY_NOT_RECOGNIZED = _("Sorry, the facility '%(facility)s' is not recognized. Please try again.")
ALREADY_REGISTERED = _("%(name)s, you are already registered as a %(readable_user_type)s at %(facility)s but your details have been updated")
CONTACT_TYPE_NOT_RECOGNIZED = _("Sorry, the User Type '%(title)s' is not recognized. Please try again.")
ZONE_SPECIFIED_BUT_NOT_CBA = _("You can not specify a zone when registering as a %(reg_type)s!")
USER_SUCCESS_REGISTERED =  _("Thank you for registering! You have successfully registered as a %(readable_user_type)s at %(facility)s.")
MOTHER_SUCCESS_REGISTERED = _("Thank you, mother has been registered succesfully!")
NOT_REGISTERED_FOR_DATA_ASSOC = _("Sorry, this number is not registered. Please register with the JOIN keyword and try again")
NOT_A_DATA_ASSOCIATE = _("You are not registered as a Data Associate and are not allowed to register mothers!")
DATE_INCORRECTLY_FORMATTED_GENERAL = _("The date you entered for %(date_name)s is incorrectly formatted.  Format should be "
                                       "DD MM YYYY. Please try again.")
DATE_YEAR_INCORRECTLY_FORMATTED = _("The year you entered for date %(date_name)s is incorrectly formatted.  Should be in the format"
                                    "YYYY (four digit year). Please try again.")
NOT_PREREGISTERED = _('Sorry, you are not on the pre-registered users list. Please contact ZCAHRD for assistance')
DATE_ERROR = _('%(error_msg)s for %(date_name)s')
INITIAL_AMBULANCE_RESPONSE = _('Thank you.Your request for an ambulance has been received. Someone will be in touch with you shortly.If no one contacts you,please call the emergency number!')
ER_TO_DRIVER = _("Mother with ID:%(unique_id)s needs ER.Location:%(from_location)s,contact num:%(sender_phone_number)s. Plz SEND 'respond %(unique_id)s [status]' if you see this")
ER_TO_TRIAGE_NURSE = _("Mother with ID:%(unique_id)s needs ER.Location:%(from_location)s,contact num:%(sender_phone_number)s. Plz SEND 'confirm %(unique_id)s' if you see this")
ER_TO_OTHER = _("Mother with ID:%(unique_id)s needs ER.Location:%(from_location)s,contact num:%(sender_phone_number)s. Plz SEND 'confirm %(unique_id)s' if you see this")
FUP_MOTHER_DOES_NOT_EXIST = _("Sorry, the mother you are trying to Follow Up is not registered in the system. Please check the UID and try again or register her first.")
FOLLOW_UP_COMPLETE = _("Thanks! Follow up registration for Mother ID: %(unique_id)s is complete!.")
ER_CONFIRM_SESS_NOT_FOUND = _("The Emergency with ID:%(unique_id)s can not be found! Please try again or contact your DMO immediately.")
NOT_REGISTERED_TO_CONFIRM_ER = _("Sorry. You are not registered as Triage Nurse, Ambulance or DMO")
THANKS_ER_CONFIRM = _("Thank you for confirming. When you know the status of the Ambulance, please send RESP <RESPONSE_TYPE>!")
NOT_ALLOWED_ER_WORKFLOW = _("Sorry, your registration type is not allowed to send Emergency Response type messages")
AMB_RESPONSE_THANKS = _("Thank you. The ambulance for this request has been marked as %(response)s. We will notify the Rural Facility.")
AMB_CANT_FIND_UID = _("Sorry. We cannot find the Mother's Unique ID you specified. Please try again or contact the DMO")
AMB_RESPONSE_ORIGINATING_LOCATION_INFO = _("Emergency Response: The ambulance for the Unique ID: %(unique_id)s has been marked %(response)s")
AMB_OUTCOME_NO_OUTCOME = _("No OUTCOME Specified.  Please send an outcome!")
AMB_OUTCOME_MSG_RECEIVED = _("Thanks for your message! We have marked the patient with unique_id %(unique_id)s as outcome: %(outcome)s")
AMB_OUTCOME_ORIGINATING_LOCATION_INFO = _("We have been notified of the patient outcome for patient with unique_id: %(unique_id)s. Outcome: %(outcome)s")
AMB_OUTCOME_FILED = _("A patient outcome for an Emergency Response for Patient (%(unique_id)s) has been filed by %(name)s (%(contact_type)s)")
LMP_OR_EDD_DATE_REQUIRED = _("Sorry, either the LMP or the EDD must be filled in!")
DATE_NOT_OPTIONAL = _("This date is not optional!")
ER_TO_CLINIC_WORKER = _("This is an emergency message to the clinic. %(unique_id)s")
ER_STATUS_UPDATE = _("The Emergency Request for Mother with Unique ID: %(unique_id)s has been marked %(status)s by %(name)s (%(confirm_type)s)")

# referrals
REFERRAL_RESPONSE = _("Thanks %(name)s! Referral for Mother ID %(unique_id)s is complete!")
CZ_TEST = _("Does this work? %(test)s!")
                     
logger = logging.getLogger(__name__)
class SMGL(AppBase):
    #overriding because seeing router|mixin is so unhelpful it makes me want to throw my pc out the window.
    @property
    def _logger(self):
        return logging.getLogger(__name__)
    def handle(self, msg):
        pass

    # We're handling the submission process using signal hooks
    # Code is located here (in app.py) for ease of finding for other devs.

def _generate_uid_for_er():
    #grab all the existing amb requests that have made up UIDs:
    ers = AmbulanceRequest.objects.filter(mother_uid__icontains='A')

    if not ers.count():
        uid = 'A1'
    else:
        counter = ers.count()
        uids = ers.values_list('mother_uid')
        uids = map(lambda x: x[0], uids) #gets us a nice list of uids
        uid = 'A%s' % counter #starting point
        counter += 1
        while uid in uids: #iterate until we find a good UID
            uid = 'A%s' % counter
            counter += 1

    return uid

def _send_msg(connection, txt, router, **kwargs):
    logger.debug('Sending Message: Connection: %s, txt: %s, kwargs: %s' % (connection, txt, kwargs))
    omsg = OutgoingMessage(connection, txt, **kwargs)
    router.outgoing(omsg)

def _get_value_for_command(command, xform):
    return xform.xpath('form/%s' % command)

def _get_valid_model(model,slug=None,name=None, iexact=False):
    if not slug and not name:
        logger.debug('No location name or slug specified while attempting to get valid model for %s' % model)
        return None
    try:
        if slug:
            if not iexact:
                return model.objects.get(slug=slug)
            else:
                return model.objects.get(slug__iexact=slug)
        else:
            if not iexact:
                return model.objects.get(name=name)
            else:
                return model.objects.get(name__iexact=name)
    except ObjectDoesNotExist:
        return None

 # Taken from mwana.apps.agents.handler.agrent.AgentHandler

def _get_or_create_zone(clinic, name):
    # create the zone if it doesn't already exist
    zone_type, _ = LocationType.objects.get_or_create(slug=const.ZONE_SLUGS[0])
    return Location.objects.get_or_create(name__iexact=name,
                                parent=clinic,
                                type=zone_type,
                                defaults={
                                    'name': name,
                                    'slug': get_unique_value(Location.objects, "slug", name),
                                })

def get_location(session, facility):
    return _get_valid_model(Location, slug=facility, iexact=True)
    
def get_contacttype(session, reg_type):
    contactType = _get_valid_model(ContactType, slug=reg_type, iexact=True)
    error = False
    if not contactType:
        error=True
    return contactType, error



def _get_allowed_ambulance_workflow_contact(session):
    connection = session.connection
    tn_type, error = get_contacttype(session, 'tn')
    amb_type, error = get_contacttype(session, 'am')
    other_type, error = get_contacttype(session, 'dmo')
    cw_type, error = get_contacttype(session, 'worker')
    types = [tn_type, amb_type, other_type, cw_type]
    try:
        contact = Contact.objects.get(connection=connection, types__in=types)
        return contact
    except ObjectDoesNotExist:
        return None

def _make_date(dd, mm, yy, is_optional=False):
    """
    Returns a tuple: (datetime.date, ERROR_MSG)
    ERROR_MSG will be False if datetime.date is sucesfully constructed.
    Be sure to include the dictionary key-value "date_name": DATE_NAME
    when sending out the error message as an outgoing message.
    """
    logger.debug('in _make_date(). Trying to make a date from %s %s %s' % (dd,mm,yy))
    dd_is_none = dd.lower() in NONE_VALUES
    mm_is_none = mm.lower() in NONE_VALUES
    yy_is_none = yy.lower() in NONE_VALUES
    if dd_is_none and mm_is_none and yy_is_none and is_optional:
        return None, False, None
    elif dd_is_none or mm_is_none or yy_is_none:
        return None, True, DATE_NOT_OPTIONAL
    try:
        dd = int(dd)
        mm = int(mm)
        yy = int(yy)
    except ValueError as ve:
        logger.debug('In Make Date: ve %s' % ve)
        return None, True, DATE_INCORRECTLY_FORMATTED_GENERAL

    if yy < 1900: #Make sure yy is a 4 digit date
        return None, True, DATE_YEAR_INCORRECTLY_FORMATTED

    try:
        ret_date = datetime.date(yy,mm,dd)
    except ValueError as msg:
        logging.debug('Could not make a datetime. Exception: %s' % msg)
        return None, True, str(msg) #<-- will send descriptive message of exact error (like month not in 1..12, etc)

    return ret_date, False, None

###############################################################################
##              BEGIN RAPIDSMS_XFORMS KEYWORD HANDLERS                       ##
##===========================================================================##
def pregnant_registration(session, xform, router):
    """
    Handler for REG keyword (registration of pregnant mothers).
    Format:
    REG Mother_UID FIRST_NAME LAST_NAME HIGH_RISK_HISTORY FOLLOW_UP_DATE_dd FOLLOW_UP_DATE_mm FOLLOW_UP_DATE_yyyy \
        REASON_FOR_VISIT(ROUTINE/NON-ROUTINE) ZONE LMP_dd LMP_mm LMP_yyyy EDD_dd EDD_mm EDD_yyyy
    """
    logger.debug('Handling the REG keyword form')

    #Create a contact for this connection.  If it already exists,
    #Verify that it is a contact of the specified type. If not,
    #Add it.  If it does already have that type associated with it
    # Return a message indicating that it is already registered.
    #Same logic for facility.
    connection = session.connection

    #We must get the location from the Contact (Data Associate) who should be registered with this
    #phone number.  If the contact does not exist (unregistered) we throw an error.
    contactType, error = get_contacttype(session, 'da') #da = Data Associate
    if error:
        _send_msg(connection, NOT_A_DATA_ASSOCIATE, router)
        return True
    logging.debug('Data associate:: Connection: %s, Type: %s' % (connection, contactType))
    try:
        data_associate = Contact.objects.get(connection=connection, types=contactType)
    except ObjectDoesNotExist:
        logger.info("Data Associate Contact not found.  Mother cannot be correctly registered!")
        _send_msg(connection, NOT_REGISTERED_FOR_DATA_ASSOC, router)
        return True


    #get or create a new Mother Object without saving the object (and triggering premature errors)
    uid = _get_value_for_command('unique_id', xform)
    try:
        mother = PregnantMother.objects.get(uid=uid)
    except ObjectDoesNotExist:
        mother = PregnantMother()

    mother.first_name = _get_value_for_command('first_name', xform)
    mother.last_name = _get_value_for_command('last_name', xform)
    mother.uid = uid
    mother.high_risk_history = _get_value_for_command('high_risk_factor', xform)



    next_visit_dd = _get_value_for_command('next_visit_dd', xform)
    next_visit_mm = _get_value_for_command('next_visit_mm', xform)
    next_visit_yy = _get_value_for_command('next_visit_yy', xform)
    next_visit, error, error_msg = _make_date(next_visit_dd, next_visit_mm, next_visit_yy)
    date_dict = {
        "date_name": "Next Visit",
        "error_msg": error_msg,
        }
    session.template_vars.update(date_dict)
    if error:
        _send_msg(connection, DATE_ERROR, router, **session.template_vars)
        return True
    mother.next_visit = next_visit

    mother.reason_for_visit = _get_value_for_command('visit_reason', xform)
    zone_name = _get_value_for_command('zone', xform)

    lmp_dd = _get_value_for_command('lmp_dd', xform)
    lmp_mm = _get_value_for_command('lmp_mm', xform)
    lmp_yy = _get_value_for_command('lmp_yy', xform)
    lmp_date, lmp_error, error_msg = _make_date(lmp_dd, lmp_mm, lmp_yy, is_optional=True)
    date_dict = {
        "date_name": "LMP",
        "error_msg": error_msg,
        }
    session.template_vars.update(date_dict)
    if lmp_error:
        _send_msg(connection, DATE_ERROR, router,  **session.template_vars)
        return True

    edd_dd = _get_value_for_command('edd_dd', xform)
    edd_mm = _get_value_for_command('edd_mm', xform)
    edd_yy = _get_value_for_command('edd_yy', xform)
    edd_date, edd_error, error_msg = _make_date(edd_dd, edd_mm, edd_yy, is_optional=True)
    date_dict = {
        "date_name": "EDD",
        "error_msg": error_msg,
        }
    session.template_vars.update(date_dict)
    if edd_error:
        _send_msg(connection, DATE_ERROR, router,  **session.template_vars)
        return True

    if lmp_date is None and edd_date is None:
        _send_msg(connection, LMP_OR_EDD_DATE_REQUIRED, router,  **session.template_vars)

    mother.lmp = lmp_date
    mother.edd = edd_date

    logger.debug('Mother UID: %s' % mother.uid)

    #Create the mother model obj if it doesn't exist
    mother.location = data_associate.location
    if zone_name:
        mother.zone = _get_or_create_zone(mother.location, zone_name)

    mother.contact = data_associate
    mother.save()

    #Create a facility visit object and link it to the mother
    visit = FacilityVisit()
    visit.location = mother.location
    visit.visit_date = datetime.date.today()
    visit.reason_for_visit = 'initial_registration'
    visit.next_visit = mother.next_visit
    visit.mother = mother
    visit.contact = data_associate
    visit.save()

    _send_msg(connection, MOTHER_SUCCESS_REGISTERED, router,  **session.template_vars)
    #prevent default response
    return True

def follow_up(session, xform, router):
    connection = session.connection
    try:
        da_type, error = get_contacttype(session, 'da')
        contact = Contact.objects.get(types=da_type, connection=connection)
    except ObjectDoesNotExist:
        _send_msg(connection, NOT_A_DATA_ASSOCIATE, router, **session.template_vars)
        return True
    unique_id = _get_value_for_command('unique_id', xform)
    session.template_vars.update({"unique_id": unique_id})
    try:
        mother = PregnantMother.objects.get(uid=unique_id)
    except ObjectDoesNotExist:
        _send_msg(connection, FUP_MOTHER_DOES_NOT_EXIST, router, **session.template_vars)
        return True

    edd_dd = _get_value_for_command('edd_dd', xform)
    edd_mm = _get_value_for_command('edd_mm', xform)
    edd_yy = _get_value_for_command('edd_yy', xform)
    edd_date, error, error_msg = _make_date(edd_dd, edd_mm, edd_yy)
    date_dict = {
        "date_name": "EDD",
        "error_msg": error_msg,
        }
    session.template_vars.update(date_dict)
    if error:
        _send_msg(connection, DATE_ERROR, router, **session.template_vars)
        return True

    visit_reason = _get_value_for_command('visit_reason', xform)

    next_visit_dd = _get_value_for_command('next_visit_dd', xform)
    next_visit_mm = _get_value_for_command('next_visit_mm', xform)
    next_visit_yy = _get_value_for_command('next_visit_yy', xform)
    next_visit, error, error_msg = _make_date(next_visit_dd, next_visit_mm, next_visit_yy)
    date_dict = {
        "date_name": "Next Visit",
        "error_msg": error_msg,
        }
    session.template_vars.update(date_dict)
    if error:
        _send_msg(connection, DATE_ERROR, router, **session.template_vars)
        return True

    #Make the follow up facility visit thinger.
    visit = FacilityVisit()
    visit.mother = mother
    visit.contact = contact
    visit.location = contact.location
    visit.edd = edd_date
    visit.reason_for_visit = visit_reason
    visit.next_visit = next_visit
    visit.save()

    _send_msg(connection, FOLLOW_UP_COMPLETE, router, **session.template_vars)


def referral(submission, xform, router):
    pass

def birth_registration(submission, xform, router):
    """
    Keyword: BIRTH
    """
    print 'Got the xform and submission for the BIRTH Keyword!!'
    print 'Submission: %s' % submission
    print 'Xform: %s' % xform
    logging.debug('-================================++!!!!!!!!!!!!!!!!!!!!+===========-')

def death_registration(submission, xform, **args):
    pass
###############################################################################


# define a listener
def handle_submission(sender, **args):
    session = args['session']
    xform = args['xform']
    router = args['router']
    xform.initiating_phone_number = session.connection.identity

    keyword = session.trigger.trigger_keyword
    
    logger.debug('Attempting to post-process submission. Keyword: %s  Session is: %s' % (keyword, session))

    try:
        kw_handler = XFormKeywordHandler.objects.get(keyword=keyword)
    except ObjectDoesNotExist:
        logger.debug('No keyword handler found for the xform submission with keyword: %s' % keyword)
        return
    
    func = to_function(str(kw_handler.function_path), True)
    session.template_vars = {} #legacy from using rapidsms-xforms
    for k,v in xform.top_level_tags().iteritems():
        session.template_vars[k] = v

    #call the actual handling function
    return func(session, xform, router)

# then wire it to the xform_received signal
xform_saved_with_session.connect(handle_submission)