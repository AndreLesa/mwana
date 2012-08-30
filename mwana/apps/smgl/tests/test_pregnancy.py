from mwana.apps.smgl.tests.shared import SMGLSetUp 
from mwana.apps.smgl.models import PregnantMother, FacilityVisit,\
    ReminderNotification
from mwana.apps.smgl import const
from datetime import date, datetime, timedelta
from mwana.apps.smgl.reminders import send_followup_reminders,\
    send_upcoming_delivery_reminders


class SMGLPregnancyTest(SMGLSetUp):
    fixtures = ["initial_data.json"]
    
    def setUp(self):
        super(SMGLPregnancyTest, self).setUp()
        ReminderNotification.objects.all().delete()
        
        self.createDefaults()
        self.user_number = "15"
        self.name = "AntonDA"
        self.cba = self.createUser("cba", "456", location="80402404")
        
        self.assertEqual(0, PregnantMother.objects.count())
        self.assertEqual(0, FacilityVisit.objects.count())
        
        
    def testRegister(self):
        resp = const.MOTHER_SUCCESS_REGISTERED % { "name": self.name,
                                                   "unique_id": "80403000000112" }
        script = """
            %(num)s > REG 80403000000112 Mary Soko none 04 08 2012 R 80402404 12 02 2012 18 11 2012
            %(num)s < %(resp)s            
        """ % { "num": self.user_number, "resp": resp }
        self.runScript(script)
        
        self.assertEqual(1, PregnantMother.objects.count())
        mom = PregnantMother.objects.get(uid='80403000000112')
        self.assertEqual(self.user_number, mom.contact.default_connection.identity)
        self.assertEqual("Mary", mom.first_name)
        self.assertEqual("Soko", mom.last_name)
        self.assertEqual(date(2012, 2, 12), mom.lmp)
        self.assertEqual(date(2012, 11, 18), mom.edd)
        self.assertEqual(date(2012, 8, 4), mom.next_visit)
        self.assertTrue(mom.risk_reason_none)
        self.assertEqual(["none"], list(mom.get_risk_reasons()))
        self.assertEqual("r", mom.reason_for_visit)
        
        self.assertEqual(1, FacilityVisit.objects.count())
        visit = FacilityVisit.objects.get(mother=mom)
        self.assertEqual(self.user_number, visit.contact.default_connection.identity)
        self.assertEqual("804024", visit.location.slug)
        self.assertEqual("r", visit.reason_for_visit)
        self.assertEqual(date(2012, 11, 18), visit.edd)
        self.assertEqual(date(2012, 8, 4), visit.next_visit)
        
    def testRegisterNotRegistered(self):
        script = """
            %(num)s > REG 80403000000112 Mary Soko none 04 08 2012 R 80402404 12 02 2012 18 11 2012
            %(num)s < %(resp)s
        """ % {"num": "notacontact", "resp": const.NOT_REGISTERED}
        self.runScript(script)
    
    def testRegisterMultipleReasons(self):
        resp = const.MOTHER_SUCCESS_REGISTERED % { "name": self.name,
                                                   "unique_id": "80403000000112" }
        reasons = "csec,cmp,gd,hbp"
        script = """
            %(num)s > REG 80403000000112 Mary Soko %(reasons)s 04 08 2012 R 80402404 12 02 2012 18 11 2012
            %(num)s < %(resp)s            
        """ % { "num": self.user_number, "resp": resp, "reasons": reasons }
        self.runScript(script)
        
        mom = PregnantMother.objects.get(uid='80403000000112')
        rback = list(mom.get_risk_reasons())
        self.assertEqual(4, len(rback))
        for r in reasons.split(","):
            self.assertTrue(r in rback)
            self.assertTrue(mom.get_risk_reason(r))
            self.assertTrue(getattr(mom, "risk_reason_%s" % r))
        
    def testRegisterWithBadZone(self):
        resp = const.UNKOWN_ZONE % { "zone": "notarealzone" }
        script = """
            %(num)s > REG 80403000000112 Mary Soko none 04 08 2012 R notarealzone 12 02 2012 18 11 2012
            %(num)s < %(resp)s            
        """ % { "num": self.user_number, "resp": resp }
        self.runScript(script)
        self.assertEqual(0, PregnantMother.objects.count())
        self.assertEqual(0, FacilityVisit.objects.count())
    
    def testLayCounselorNotification(self):
        lay_num = "555666"
        lay_name = "lay_counselor"
        self.createUser(const.CTYPE_LAYCOUNSELOR, lay_num, lay_name, "80402404")
        resp = const.MOTHER_SUCCESS_REGISTERED % {"name": self.name,
                                                  "unique_id": "80403000000112" }
        lay_msg = const.NEW_MOTHER_NOTIFICATION % {"mother": "Mary Soko",
                                                   "unique_id": "80403000000112" }
        script = """
            %(num)s > REG 80403000000112 Mary Soko none 04 08 2012 R 80402404 12 02 2012 18 11 2012
            %(num)s < %(resp)s
            %(lay_num)s < %(lay_msg)s
        """ % { "num": self.user_number, "resp": resp, 
                "lay_num": lay_num, "lay_msg": lay_msg }
        self.runScript(script)
        self.assertEqual(1, PregnantMother.objects.count())
        self.assertEqual(1, FacilityVisit.objects.count())
    
    def testFollowUp(self):
        self.testRegister()
        resp = const.FOLLOW_UP_COMPLETE % { "name": self.name,
                                            "unique_id": "80403000000112" }
        script = """
            %(num)s > FUP 80403000000112 R 18 11 2012 02 12 2012 
            %(num)s < %(resp)s            
        """ % { "num": self.user_number, "resp": resp }
        self.runScript(script)
        
        self.assertEqual(1, PregnantMother.objects.count())
        self.assertEqual(2, FacilityVisit.objects.count())
    
    def testFollowUpNotRegistered(self):
        script = """
            %(num)s > FUP 80403000000112 R 18 11 2012 02 12 2012 
            %(num)s < %(resp)s
        """ % {"num": "notacontact", "resp": const.NOT_REGISTERED}
        self.runScript(script)
    
    def testFollowUpOptionalEdd(self):
        self.testRegister()
        resp = const.FOLLOW_UP_COMPLETE % { "name": self.name,
                                            "unique_id": "80403000000112" }
        script = """
            %(num)s > FUP 80403000000112 r 16 10 2012
            %(num)s < %(resp)s            
        """ % { "num": self.user_number, "resp": resp }
        self.runScript(script)
        
        self.assertEqual(1, PregnantMother.objects.count())
        self.assertEqual(2, FacilityVisit.objects.count())
    
    def testFollowUpBadEdd(self):
        self.testRegister()
        resp = const.DATE_INCORRECTLY_FORMATTED_GENERAL % { "date_name": "EDD" }
        script = """
            %(num)s > FUP 80403000000112 r 16 10 2012 not a date
            %(num)s < %(resp)s            
        """ % { "num": self.user_number, "resp": resp }
        self.runScript(script)
        
        self.assertEqual(1, PregnantMother.objects.count())
        self.assertEqual(1, FacilityVisit.objects.count())
    
    def testDatesInPastOrFuture(self):
        yesterday = (datetime.now() - timedelta(days=1)).date()
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        
        # next visit in past
        script = """
            %(num)s > REG 80403000000112 Mary Soko none %(past)s R 80402404 %(past)s %(future)s
            %(num)s < %(resp)s            
        """ % { "num": self.user_number, "past": yesterday.strftime("%d %m %Y"), 
                "future": tomorrow.strftime("%d %m %Y"), 
                "resp": const.DATE_MUST_BE_IN_FUTURE % {"date_name": "Next Visit", 
                                                       "date": yesterday}}
        self.runScript(script)
        
        # lmp in future
        script = """
            %(num)s > REG 80403000000112 Mary Soko none %(future)s R 80402404 %(future)s %(future)s
            %(num)s < %(resp)s            
        """ % { "num": self.user_number, "past": yesterday.strftime("%d %m %Y"), 
                "future": tomorrow.strftime("%d %m %Y"), 
                "resp": const.DATE_MUST_BE_IN_PAST % {"date_name": "LMP", 
                                                       "date": yesterday}}
        # edd in past
        script = """
            %(num)s > REG 80403000000112 Mary Soko none %(future)s R 80402404 %(past)s %(past)s
            %(num)s < %(resp)s            
        """ % { "num": self.user_number, "past": yesterday.strftime("%d %m %Y"), 
                "future": tomorrow.strftime("%d %m %Y"), 
                "resp": const.DATE_MUST_BE_IN_FUTURE % {"date_name": "EDD", 
                                                        "date": yesterday}}
        self.runScript(script)
        
        
    def testTold(self):
        self.testRegister()
        resp = const.TOLD_COMPLETE % { "name": self.name }
        script = """
            %(num)s > told 80403000000112 edd
            %(num)s < %(resp)s            
        """ % { "num": self.user_number, "resp": resp }
        self.runScript(script)
        
    def testToldNotRegistered(self):
        script = """
            %(num)s > told 80403000000112 edd
            %(num)s < %(resp)s
        """ % {"num": "notacontact", "resp": const.NOT_REGISTERED}
        self.runScript(script)
    
        
    def testVisitReminders(self):
        self.testRegister()
        [mom] = PregnantMother.objects.all()
        visit = FacilityVisit.objects.get(mother=mom)
        self.assertEqual(False, visit.reminded)
        
        # set 10 days in the future, no reminder
        visit.next_visit = datetime.utcnow() + timedelta(days=10)
        visit.save()
        send_followup_reminders()
        visit = FacilityVisit.objects.get(pk=visit.pk)
        self.assertEqual(False, visit.reminded)
        
        # set to 7 days, should now fall in threshold
        visit.next_visit = datetime.utcnow() + timedelta(days=7)
        visit.save()
        send_followup_reminders()
        
        reminder = const.REMINDER_FU_DUE % {"name": "Mary Soko",
                                            "unique_id": "80403000000112",
                                            "loc": "Chilala"}
        script = """ 
            %(num)s < %(msg)s
        """ % {"num": "456", 
               "msg": reminder}
        self.runScript(script)
        
        visit = FacilityVisit.objects.get(pk=visit.pk)
        self.assertEqual(True, visit.reminded)
        
        [notif] = ReminderNotification.objects.all()
        self.assertEqual(visit.mother, notif.mother)
        self.assertEqual(visit.mother.uid, notif.mother_uid)
        self.assertEqual(self.cba, notif.recipient)
        self.assertEqual("nvd", notif.type)
        
    def testEDDReminders(self):
        self.testRegister()
        [mom] = PregnantMother.objects.all()
        self.assertEqual(False, mom.reminded)
        
        # set 15 days in the future, no reminder
        mom.edd = datetime.utcnow().date() + timedelta(days=15)
        mom.save()
        send_upcoming_delivery_reminders()
        mom = PregnantMother.objects.get(pk=mom.pk)
        self.assertEqual(False, mom.reminded)
        
        # set to 14 days, should now fall in threshold
        mom.edd = datetime.utcnow().date() + timedelta(days=14)
        mom.save()
        send_upcoming_delivery_reminders()
        mom = PregnantMother.objects.get(pk=mom.pk)
        self.assertEqual(True, mom.reminded)
        
        reminder = const.REMINDER_UPCOMING_DELIVERY % {"name": "Mary Soko",
                                                       "unique_id": "80403000000112",
                                                       "date": mom.edd}
        script = """ 
            %(num)s < %(msg)s
        """ % {"num": "456", 
               "msg": reminder}
        self.runScript(script)
        
        
        [notif] = ReminderNotification.objects.all()
        self.assertEqual(mom, notif.mother)
        self.assertEqual(mom.uid, notif.mother_uid)
        self.assertEqual(self.cba, notif.recipient)
        self.assertEqual("edd_14", notif.type)
        
        