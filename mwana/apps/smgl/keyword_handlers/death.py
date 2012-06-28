from mwana.apps.smgl.app import DEATH_REG_RESPONSE
from rapidsms.messages.outgoing import OutgoingMessage
from mwana.apps.smgl.utils import get_date, DateFormatError
from mwana.apps.smgl.models import DeathRegistration
from dimagi.utils.parsing import string_to_boolean

def death_registration(session, xform, router):
    """
    Keyword: death
    """
    name = session.connection.contact.name if session.connection.contact else ""
    
    try:
        date = get_date(xform, "death_date_dd", "death_date_mm", "death_date_yyyy")
    except DateFormatError:
        # TODO
        pass
        raise
    reg = DeathRegistration(contact=session.connection.contact,
                            connection=session.connection,
                            date=date,
                            unique_id=xform.xpath("form/unique_id"),
                            person=xform.xpath("form/death_type"),
                            place=xform.xpath("form/death_location"))
    reg.save()      
    resp = DEATH_REG_RESPONSE % {"name": name}
    router.outgoing(OutgoingMessage(session.connection, resp))
    