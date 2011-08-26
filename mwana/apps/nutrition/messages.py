# vim: ai ts=4 sts=4 et sw=4

GENDER_MISMATCH = "Reported gender '%s' for Child ID %s does not match previously reported gender=%s."
DOB_MISMATCH = "Reported date of birth '%s' for Child ID %s does not match previosly reported DOB=%s."
REGISTER_BEFORE_REPORTING = "Please register before submitting survey: Send JOIN HSA <LOCATIONCODE> <ZONE> <FIRSTNAME> <LASTNAME>."
TOO_MANY_TOKENS = "Too much data!."
INVALID_ID = "Sorry, ID code '%s' is not valid for a %s."
INVALID_DOB = "Sorry I don't understand '%s' as a child's date of birth. Please use DDMMYY."
INVALID_GENDER = "Sorry I don't understand '%s' as a child's gender. Please use M for male or F for female."
INVALID_MEASUREMENT = "Possible measurement error. Please check height, weight, MUAC or age of child: %s."
REPORT_HELP = "To report measurements send: GM <CHILD ID> <GENDER> <BIRTHDATE> <WEIGHT> <HEIGHT> <OEDEMA> <MUAC>"
REPORT_CONFIRM = "Thanks, %s. Received %s."
INVALID_MESSAGE = "Sorry, I don't understand."
CANCEL_HELP = "To cancel the last report and assessment for a child send: CANCEL <CHILD ID>."
CANCEL_CONFIRM = "CANCELLED report submitted by %s (ID %s) on %s for Child ID %s."
CANCEL_ERROR = "Sorry, unable to locate report for Child ID %s."
REGISTER_HELP = "To register as an Interviewer send: REG <Interviewer ID> <NAME>."
REGISTER_CONFIRM = "Hello %s, thanks for registering as Interviewer ID %s!"
REGISTER_AGAIN = "Hello again, %s. You are already registered with RapidSMS."
REMOVE_HELP = "To remove an Interviewer send: REMOVE <Inteviewer ID>."
REMOVE_CONFIRM = "%s has been removed from Interviewer ID %s."
ADMIT_HELP = "To admit a child send: ADMIT <CHILD ID> <NAME>"
DISMISS_HELP = "To discharge a child send: DISMISS <CHILD_ID>"
# only for testing
ADMIT_HANDLE = "Admit is being handled. You sent the following text: %s."
