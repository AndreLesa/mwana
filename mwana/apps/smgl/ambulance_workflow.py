import datetime
import logging
from rapidsms.models import Contact
from django.core.exceptions import ObjectDoesNotExist
from mwana.apps.smgl.app import get_value_from_form, send_msg, get_contacttype, ER_TO_DRIVER, ER_TO_TRIAGE_NURSE, ER_TO_OTHER, ER_TO_CLINIC_WORKER, _generate_uid_for_er, INITIAL_AMBULANCE_RESPONSE, _get_allowed_ambulance_workflow_contact, NOT_REGISTERED_TO_CONFIRM_ER, ER_CONFIRM_SESS_NOT_FOUND, AMB_CANT_FIND_UID, AMB_OUTCOME_NO_OUTCOME, NOT_ALLOWED_ER_WORKFLOW, AMB_OUTCOME_ORIGINATING_LOCATION_INFO,\
    ER_STATUS_UPDATE, AMB_OUTCOME_FILED
from mwana.apps.smgl.models import AmbulanceRequest, PregnantMother, AmbulanceResponse, AmbulanceOutcome
from mwana.apps.contactsplus.models import ContactType

logger = logging.getLogger(__name__)

# In RapidSMS, message translation is done in OutgoingMessage, so no need
# to attempt the real translation here.  Use _ so that makemessages finds
# our text.
_ = lambda s: s

AMBULANCE_WORKFLOW_SYMPTOMS = {
    #code: sympton_string
    "symptom_1": "Some symptom 1",
    "12": "Anemia",
}

def _get_symptom_from_code(xform):
    try:
        return AMBULANCE_WORKFLOW_SYMPTOMS[get_value_from_form('danger_signs', xform)]
    except KeyError:
        return get_value_from_form('danger_signs', xform)

def _get_receiving_facility(location):
    """
    Get the facility that should receive an emergency patient, based on the clinic they are coming from
    """
    #currently we're just directing patients to whatever is their parent location
    parent = location.parent_location
    return parent

def _pick_er_driver(session, xform):
    ad_type = ContactType.objects.get(slug__iexact='am')
    ads = Contact.objects.filter(types=ad_type)
    if ads.count():
        return ads[0]
    else:
        raise Exception('No Ambulance Driver type found!')

def _pick_other_er_recip(session, xform):
    other_type = ContactType.objects.get(slug__iexact='dmho')
    others = Contact.objects.filter(types=other_type)
    if others.count():
        return others[0]
    else:
        logger.error('No Other recipient type found for Ambulance Request Workflow!')

def _pick_er_triage_nurse(session, xform):
    tn_type = ContactType.objects.get(slug__iexact='tn')
    tns = Contact.objects.filter(types=tn_type)
    if tns.count():
        return tns[0]
    else:
        raise Exception('No Triage Nurse type found!')

def _pick_clinic_recip(session, xform):
    cw_type = ContactType.objects.get(slug__iexact='worker')
    cws = Contact.objects.filter(types=cw_type)
    if cws.count():
        return cws[0]
    else:
        logger.error('No clinic worker found!')

def _broadcast_to_ER_users(ambulance_session, session, xform, router, message=None):
    """
    Broadcasts a message to the Emergency Response users.  If message is not
    specified, will send the default initial ER message to each respondent.
    """
    #Figure out who to alert
    ambulance_driver = _pick_er_driver(session, xform)
    ambulance_session.ambulance_driver = ambulance_driver
    if ambulance_driver.default_connection:
        if message:
            send_msg(ambulance_driver.default_connection, message, router, **session.template_vars)
        else:
            send_msg(ambulance_driver.default_connection, ER_TO_DRIVER, router, **session.template_vars)
    else:
        logger.error('No Ambulance Driver found (or missing connection) for Ambulance Session: %s, XForm Session: %s, XForm: %s' % (ambulance_session, session, xform))

    tn = _pick_er_triage_nurse(session, xform)
    ambulance_session.triage_nurse = tn
    
    if tn.default_connection:
        if message:
            send_msg(tn.default_connection, message, router, **session.template_vars)
        else:
            send_msg(tn.default_connection, ER_TO_TRIAGE_NURSE, router, **session.template_vars)
    else:
        logger.error('No Triage Nurse found (or missing connection) for Ambulance Session: %s, XForm Session: %s, XForm: %s' % (ambulance_session, session, xform))

    other_recip = _pick_other_er_recip(session,xform)
    if other_recip: #less important, so not critical if this contact doesn't exist.
        ambulance_session.other_recipient = other_recip
        if other_recip.default_connection:
            if message:
                send_msg(other_recip.default_connection, message, router, **session.template_vars)
            else:
                send_msg(other_recip.default_connection, ER_TO_OTHER, router, **session.template_vars)
        else:
            #only warn because we may not have specified one on purpose
            logger.warn('No Other Recipient found (or missing connection) for Ambulance Session: %s, XForm Session: %s, XForm: %s' % (ambulance_session, session, xform))

    clinic_recip = _pick_clinic_recip(session, xform)
    if clinic_recip:
        ambulance_session.receiving_facility_recipient = clinic_recip
        if clinic_recip.default_connection:
            if message:
                send_msg(clinic_recip.default_connection, message, router, **session.template_vars)
            else:
                send_msg(clinic_recip.default_connection, ER_TO_CLINIC_WORKER, router, **session.template_vars)
        else:
            logger.error('No Receiving Clinic Worker found (or missing connection) for Ambulance Session: %s, XForm Session: %s, XForm: %s' % (ambulance_session, session, xform))

    ambulance_session.save()

def ambulance_request(session, xform, router):
    logger.debug('POST PROCESSING FOR AMB KEYWORD')
    connection = session.connection
    unique_id = get_value_from_form('unique_id', xform)
    danger_signs = _get_symptom_from_code(xform)

    session.template_vars.update({"sender_phone_number": connection.identity})
    amb = AmbulanceRequest()
    amb.danger_sign = danger_signs
    amb.connection = connection
    contact = None
    try:
        contact = Contact.objects.get(connection=connection)
    except ObjectDoesNotExist:
        pass
    amb.contact = contact
    if contact:
        amb.from_location = contact.location
        session.template_vars.update({"from_location": str(contact.location.name)})
    else:
        session.template_vars.update({"from_location": "UNKNOWN"})

    if not unique_id:
        unique_id = _generate_uid_for_er()

    session.template_vars.update({'unique_id': unique_id})
    amb.mother_uid = unique_id

    #try match uid to mother
    mother = None
    try:
        mother = PregnantMother.objects.get(uid=unique_id)
    except ObjectDoesNotExist:
        pass
    amb.mother = mother
    amb.save()

    #Respond that we're on it.
    send_msg(connection, INITIAL_AMBULANCE_RESPONSE, router, **session.template_vars)

    _broadcast_to_ER_users(amb, session, xform, router=router)


    return True

def ambulance_response(session, xform, router):
    """
    This handler deals with a status update from an ER user about a specific ambulance
    i.e. Ambulance confirmed/cancelled/pending
    """
    logger.debug('POST PROCESSING FOR RESP KEYWORD')
    connection = session.connection
    contact = _get_allowed_ambulance_workflow_contact(session)
    if not contact:
        send_msg(connection, NOT_REGISTERED_TO_CONFIRM_ER, router, **session.template_vars)
        return True

    ambulance_response = AmbulanceResponse()
    ambulance_response.responder = contact

    unique_id = get_value_from_form('unique_id', xform)
    ambulance_response.mother_uid = unique_id
    session.template_vars.update({'unique_id': unique_id})
    #try match uid to mother
    mother = None
    logger.debug('Attempting to find Pregnant mother linked to this case with UID: %s' % unique_id)
    try:
        mother = PregnantMother.objects.get(uid=unique_id)
    except ObjectDoesNotExist:
        logger.debug('Could not find PregnantMother with UID: %s' % unique_id)
        pass
    ambulance_response.mother = mother
    ambulance_response.mother_uid = unique_id

    status = get_value_from_form('status', xform).lower()
    ambulance_response.response = status
    session.template_vars.update({"status": status.upper()})

    #we might be dealing with a mother that has gone through ER multiple times
    ambulance_requests = AmbulanceRequest.objects.filter(mother_uid=unique_id)\
                .exclude(received_response=True)\
                .order_by('-requested_on')
    if not ambulance_requests.count():
        #session doesn't exist or it has already been confirmed
        send_msg(connection, ER_CONFIRM_SESS_NOT_FOUND, router, **session.template_vars)
        return True

    #take the latest one in case this mother has been ER'd a bunch
    ambulance_response.ambulance_request = ambulance_request =  ambulance_requests[0]
    ambulance_request.received_response = True

    confirm_contact_type = contact.types.all()[0]
    session.template_vars.update({"confirm_type": confirm_contact_type,
                                  "name": contact.name})

    _broadcast_to_ER_users(ambulance_request, session, xform,
        message=_(ER_STATUS_UPDATE), router=router)

    ambulance_request.save()
    ambulance_response.save()
    return True

def ambulance_outcome(session, xform, router):
    connection = session.connection
    contact = _get_allowed_ambulance_workflow_contact(session)
    if not contact:
        send_msg(connection, NOT_ALLOWED_ER_WORKFLOW, router,
            **session.template_vars)
        return True

    unique_id = get_value_from_form('unique_id', xform)
    outcome_string = get_value_from_form('outcome', xform)
    session.template_vars.update({
        "unique_id": unique_id,
        "outcome": outcome_string
    })

    if not outcome_string:
        send_msg(connection, AMB_OUTCOME_NO_OUTCOME, router,
            **session.template_vars)
        return True

    req = AmbulanceRequest.objects.filter(mother_uid=unique_id).order_by('-requested_on')
    if not req.count():
        send_msg(connection, AMB_CANT_FIND_UID, router, **session.template_vars)
        return True
    req = req[0] #select latest one

    outcome = AmbulanceOutcome()
    outcome.ambulance_request = req
    outcome.mother_uid = unique_id
    outcome.outcome = outcome_string
    try:
        mother = PregnantMother.objects.get(uid=unique_id)
    except ObjectDoesNotExist:
        mother = None
    outcome.mother = mother
    outcome.save()
    session.template_vars.update({"contact_type": contact.types.all()[0],
                                  "name": contact.name})
    _broadcast_to_ER_users(req,session, xform,
                           message=_(AMB_OUTCOME_FILED), router=router)
    send_msg(req.connection, AMB_OUTCOME_ORIGINATING_LOCATION_INFO, router, **session.template_vars)
    return True