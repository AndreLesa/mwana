# In RapidSMS, message translation is done in OutgoingMessage, so no need
# to attempt the real translation here.  Use _ so that makemessages finds
# our text.
_ = lambda s: s

# location type slugs
LOCTYPE_ZONE = "zone"

# contact type slugs
CTYPE_LAYCOUNSELOR = "cba"
CTYPE_DATACLERK = "dc"
CTYPE_TRIAGENURSE = 'tn'
CTYPE_INCHARGE = 'incharge'
CTYPE_CLINICWORKER = 'worker'

# from forms

REFERRAL_OUTCOME_NOSHOW = "noshow"

# shared messages
DATE_INCORRECTLY_FORMATTED_GENERAL = _("The date you entered for %(date_name)s is incorrectly formatted.  Format should be "
                                       "DD MM YYYY. Please try again.")
DATE_YEAR_INCORRECTLY_FORMATTED = _("The year you entered for date %(date_name)s is incorrectly formatted.  Should be in the format "
                                    "YYYY (four digit year). Please try again.")
DATE_MUST_BE_IN_PAST = _("The date for %(date_name)s must be in the past. Please enter a date earlier than today. You entered %(date)s")
DATE_MUST_BE_IN_FUTURE = _("The date for %(date_name)s must be in the future. Please enter a date after today. You entered %(date)s")

DATE_NOT_OPTIONAL = _("This date is not optional!")
DATE_NOT_NUMBERS = _("Date format should include only numbers: 'dd mm yyyy'")
TIME_INCORRECTLY_FORMATTED = _("The time you entered (%(time)s) is not valid. Time should be a four-digit number, like 1500.")
UNKOWN_ZONE = _("There is no zone with code %(zone)s. Please check your code and try again.")

NOT_REGISTERED=_("This phone number is not registered in the system.")
NOT_REGISTERED_FOR_DATA_ASSOC = _("Sorry, this number is not registered. Please register with the JOIN keyword and try again")
NOT_A_DATA_ASSOCIATE = _("You are not registered as a Data Associate and are not allowed to register mothers!")
MOTHER_NOT_FOUND = _("The mother's ID: %(unique_id)s was not recognized, please check and send again. If the mother was not registered enter 'none' in the place of the ID.")
GENERAL_ERROR = _("Your message is either incomplete or incorrect. Please check and send again.")

# pregnancy messages
LMP_OR_EDD_DATE_REQUIRED = _("Sorry, either the LMP or the EDD must be filled in!")
MOTHER_SUCCESS_REGISTERED = _("Thanks %(name)s! Registration for Mother ID %(unique_id)s is complete!")
NEW_MOTHER_NOTIFICATION = _("A new mother named %(mother)s with ID # %(unique_id)s was registered in your zone. Please visit this mother and take note in your register.")
DUPLICATE_REGISTRATION = _("A mother with ID %(unique_id)s is already registered. Please check the ID and try again.")

# pregnancy follow up messages
FUP_MOTHER_DOES_NOT_EXIST = _("Sorry, the mother you are trying to follow up is not registered in the system. Check the safe motherhood number ( %(unique_id) ) and try again or register her first.")
FOLLOW_UP_COMPLETE = _("Thanks %(name)s! Follow up for Mother ID %(unique_id)s is complete!")

# pregnancy postpartum visit messages
PP_MOTHER_DOES_NOT_EXIST = _("Sorry, the mother you are trying to provide post partum data for is not registered in the system. Check the safe motherhood ID ( %(unique_id) ) and try again or register her first.")
PP_MOTHER_HAS_NOT_DELIVERED = _("Sorry, the mother with ID %(unique_id) you are trying to provide post partum data for has no birth registered.")
PP_NVD_REQUIRED = _("Sorry, the mother with ID %(unique_id) has had only %(num)s post partum followup(s). 3 are required and the NVD is missing.")
PP_COMPLETE = _("Thanks %(name)s! Post Partum visit for Mother ID %(unique_id)s is complete!")

# "told" messages
TOLD_COMPLETE = _("Thanks %(name)s for reminding mother with ID %(unique_id)s.")
TOLD_MOTHER_HAS_ALREADY_DELIVERED = _('Mother ID %(unique_id)s has already delivered')
TOLD_MOTHER_HAS_NO_NVD = _('Mother ID %(unique_id)s has no scheduled NVD')
TOLD_MOTHER_HAS_NO_REF = _('Mother ID %(unique_id)s has no scheduled REF')

# lookup messages
LOOK_MOTHER_DOES_NOT_EXIST = _('Sorry, the mother you are trying to lookup (%(first_name)s %(last_name)s) does not exist. Please check the supplied zone id, first and last name values.')
LOOK_COMPLETE = _("The Mother ID is %(unique_id)s.")

# referrals
REFERRAL_RESPONSE = _("Thanks %(name)s! Referral for Mother ID %(unique_id)s to %(facility_name)s is complete!")
REFERRAL_TO_HOSPITAL_DRIVER = _("A mother has been referred from %(referring_facility)s to %(referral_facility)s. Make yourself available to transport patient.")
REFERRAL_TO_DESTINATION_HOSPITAL_NURSE = _("Mother with %(unique_id)s needs EmONC and was referred to your Hospital. Plz respond to this message with RESP %(unique_id)s.")
REFERRAL_OUTCOME_RESPONSE = _("Thanks %(name)s! Referral outcome for Mother ID %(unique_id)s was received.")
REFERRAL_OUTCOME_NOTIFICATION = _("This is outcome for Mother ID %(unique_id)s sent on %(date)s: mother is %(mother_outcome)s, Baby is %(baby_outcome)s, Mode of delivery was %(delivery_mode)s.")
REFERRAL_OUTCOME_NOTIFICATION_NOSHOW = _("This is outcome for Mother ID %(unique_id)s sent on %(date)s: mother did not show up.")
REFERRAL_NOT_FOUND = _("No referrals for Mother ID %(unique_id)s were found. Please check the mother's ID.")
REFERRAL_ALREADY_RESPONDED = _("The latest referral for Mother ID %(unique_id)s was already responded to. Please check the mother's ID.")
AMB_OUTCOME_ORIGINATING_LOCATION_INFO = _("We have been notified of the patient outcome for patient with unique_id: %(unique_id)s. Outcome: %(outcome)s")
AMB_OUTCOME_NO_OUTCOME = _("Kindly register OUTCOME for Mother :%(unique_id)s.  Please send an outcome!")
REFERRAL_CBA_THANKS = _("Thanks %(name)s. A health worker at %(facility_name)s has been alerted.")
REFERRAL_CBA_NOTIFICATION_CLINIC_WORKER = _("Mother with ID: %(unique_id)s from %(village)s needs EmONC. Contact: %(phone)s. Plz send 'RESP %(unique_id)s' if you see this.")
REFERRAL_CBA_NOTIFICATION = _("Mother with ID: %(unique_id)s from %(village)s needs EmONC. Contact: %(phone)s.")

REFERRAL_FACILITY_TO_HOSPITAL_NOTIFICATION = _("Mother with ID: %(unique_id)s needs ER. Location: %(facility_name)s, contact num: %(phone)s Plz SEND 'RESP %(unique_id)s ....OTW, DL or NA' if you see this.")
REFERRAL_NOTIFICATION = _("A referral for Mother ID %(unique_id)s has been sent from %(facility)s. Please expect the mother. Reason: %(reason)s. Time: %(time)s. Emergency: %(is_emergency)s")
RESP_THANKS = _("Thanks %(name)s. Your response for referral of mother with ID: %(unique_id)s was well received")
RESP_CBA_UPDATE = _("A health worker has responded to your referral and is waiting for the mother at the facility.")
RESP_NOTIF = _("Emergency Response for mother with ID %(unique_id)s:  You can contact driver at %(phone)s.")
AMB_RESP_STATUS = _("Ambulance Response for mother with ID %(unique_id)s: Ambulance is %(status)s You can contact driver at %(phone)s.")
REFERRAL_AMBULANCE_STATUS_TO_REFERRING_HOSPITAL =_("Ambulance Response for mother with ID %(unique_id)s: You can contact driver at %(phone)s.")
REFERRAL_RESPONSE_NOTIFICATION_TO_REFERRING_HOSPITAL = _("Emergency Response for mother with ID %(unique_id)s: You can contact driver at %(phone)s.")
REF_TRIAGE_NURSE_RESP_NOTIF = _("Emergency response for mother with ID %(unique_id)s: You can contact the Triage nurse at %(phone)s.")

PICK_THANKS = _("Thanks for picking mother with ID %(unique_id)s")
DROP_THANKS = _("Thanks for dropping mother with ID %(unique_id)s")
# death registration
DEATH_REG_RESPONSE = _("Thanks %(name)s! the Facility/Community death for mother with ID %(unique_id)s has been registered.")
DEATH_ALREADY_REGISTERED = ("Death for mother with ID %(unique_id)s and type  %(person)s has already been registered")

# reminders
REMINDER_SUPER_USER_REF = _("No response received for referral of mother with ID:%(unique_id)s from %(from_facility)s to %(dest_facility)s by %(phone)s. Kindly follow up.")
REMINDER_REFERRAL_RESP = _("Please submit RESPONSE for mother with ID %(unique_id)s referred from %(from_facility)s.")
REMINDER_FU_DUE = _("Mother named %(name)s with ID # %(unique_id)s is due to visit health center %(loc)s for a follow-up visit.")
REMINDER_NON_EMERGENCY_REFERRAL = _("Mother named %(name)s with ID # %(unique_id)s should visit hospital %(loc)s as referred.")
REMINDER_EMERGENCY_REFERRAL = _("Please submit outcome SMS (REFOUT) for mother with ID %(unique_id)s referred on %(date)s from %(loc)s")
REMINDER_UPCOMING_DELIVERY = _("Mother named %(name)s with ID # %(unique_id)s is due for delivery on %(date)s please follow-up visit.")
REMINDER_PP_DUE = _("Mother named %(name)s with ID # %(unique_id)s is due to visit health center %(loc)s for a postpartum visit in %(num)s days.")
REMINDER_PP_MISSED = _("Mother named %(name)s with ID # %(unique_id)s is overdue to visit health center %(loc)s for a postpartum visit.")
REMINDER_SYP_TREATMENT_DUE = _("This is a reminder: Mother named %(name)s should visit the health center for follow-up on %(date)s")

# LEAVE
LEAVE_COMPLETE = _("Thanks %(name)s. You have deactivated your account.")
DEACTIVATED = _("This phone number has been deactivated.")

#QUIT
QUIT_COMPLETE = _("Good bye %(name)s. You have quit mUbumi.")

# IN
IN_COMPLETE = _("Thanks %(name)s. Welcome back!")
IN_REACTIVATE = _("Your account has been reactivated. Welcome back!")

# OUT
OUT_COMPLETE = _("Thanks %(name)s. Your account will be re-activated on %(date)s.")

# Syphilis
SYP_TEST_COMPLETE = _("Thanks %(name)s. A Syphilis Test Result has been recorded for %(unique_id)s. Please register the first treatment when it is given.")
SYP_TREATMENT_COMPLETE = _("Thanks %(name)s. A Syphilis Treatment has been recorded for %(unique_id)s.")

# MISC OUTBOUND SCHEDULED MESSAGES
INACTIVE_CONTACT = _("We have not heard from you for the past %(days)s days. Please send help to mUbumi (0974148753)")
EXPECTED_EDDS = _("We want to inform you that according to our records, your clinic should expect %(edd_count)s deliveries in the next 7 days. From SMGL/mUbumi")
