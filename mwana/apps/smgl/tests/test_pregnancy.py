from mwana.apps.locations.models import Location, LocationType
from mwana.apps.smgl.tests.shared import SMGLSetUp
from mwana.apps.smgl.models import PregnantMother, FacilityVisit,\
    ReminderNotification
from mwana.apps.smgl import const
from datetime import datetime, timedelta
from mwana.apps.smgl.reminders import (send_followup_reminders,
    send_upcoming_delivery_reminders_two_week, send_upcoming_delivery_reminders_three_week,
    send_upcoming_delivery_reminders_four_week, send_upcoming_delivery_reminders_five_week,
    send_upcoming_delivery_reminders_one_week)
from mwana.apps.smgl.app import BIRTH_REG_RESPONSE
from mwana.apps.smgl.tests.shared import create_mother


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
        resp = const.MOTHER_SUCCESS_REGISTERED % {"name": self.name,
                                                  "unique_id": "80403000000112"}
        script = """
            %(num)s > REG 80403000000112 Mary Soko none %(tomorrow)s R 80402404 %(earlier)s %(later)s
            %(num)s < %(resp)s
        """ % {"num": self.user_number, "resp": resp,
               "tomorrow": self.tomorrow.strftime("%d %m %Y"),
               "earlier": self.earlier.strftime("%d %m %Y"),
               "later": self.later.strftime("%d %m %Y")}
        self.runScript(script)
        self.assertSessionSuccess()
        self.assertEqual(1, PregnantMother.objects.count())
        mom = PregnantMother.objects.get(uid='80403000000112')
        self.assertEqual(self.user_number, mom.contact.default_connection.identity)
        self.assertEqual("Mary", mom.first_name)
        self.assertEqual("Soko", mom.last_name)
        self.assertEqual(self.earlier, mom.lmp)
        self.assertEqual(self.later, mom.edd)
        self.assertEqual(self.tomorrow, mom.next_visit)
        self.assertTrue(mom.risk_reason_none)
        self.assertEqual(["none"], list(mom.get_risk_reasons()))
        self.assertEqual("r", mom.reason_for_visit)

    def testRegisterWithFacilityVisit(self):
        """Should create a facility visit on registration."""
        self.testRegister()
        #A facility visit should have been registered by now.
        self.assertEqual(1, FacilityVisit.objects.filter(visit_type='anc').count())


    def testRegisterNotRegistered(self):
        script = """
            %(num)s > REG 80403000000112 Mary Soko none %(tomorrow)s R 80402404  %(earlier)s %(later)s
            %(num)s < %(resp)s
        """ % {"num": "notacontact", "resp": const.NOT_REGISTERED,
               "tomorrow": self.tomorrow.strftime("%d %m %Y"),
               "earlier": self.earlier.strftime("%d %m %Y"),
               "later": self.later.strftime("%d %m %Y")
        }
        self.runScript(script)
        self.assertSessionFail()

    def testRegisterMultipleReasons(self):
        resp = const.MOTHER_SUCCESS_REGISTERED % {"name": self.name,
                                                  "unique_id": "80403000000112"}
        reasons = "csec,cmp,gd,hbp"
        script = """
            %(num)s > REG 80403000000112 Mary Soko %(reasons)s %(tomorrow)s R 80402404 %(earlier)s %(later)s
            %(num)s < %(resp)s
        """ % {"num": self.user_number, "resp": resp, "reasons": reasons,
               "tomorrow": self.tomorrow.strftime("%d %m %Y"),
               "earlier": self.earlier.strftime("%d %m %Y"),
               "later": self.later.strftime("%d %m %Y")}
        self.runScript(script)
        self.assertSessionSuccess()

        mom = PregnantMother.objects.get(uid='80403000000112')
        rback = list(mom.get_risk_reasons())
        self.assertEqual(4, len(rback))
        for r in reasons.split(","):
            self.assertTrue(r in rback)
            self.assertTrue(mom.get_risk_reason(r))
            self.assertTrue(getattr(mom, "risk_reason_%s" % r))

    def testRegisterWithBadZone(self):
        resp = const.UNKOWN_ZONE % {"zone": "notarealzone"}
        script = """
            %(num)s > REG 80403000000112 Mary Soko none %(tomorrow)s R notarealzone %(earlier)s %(later)s
            %(num)s < %(resp)s
        """ % {"num": self.user_number, "resp": resp,
               "tomorrow": self.tomorrow.strftime("%d %m %Y"),
               "earlier": self.earlier.strftime("%d %m %Y"),
               "later": self.later.strftime("%d %m %Y")}
        self.runScript(script)
        self.assertSessionFail()
        self.assertEqual(0, PregnantMother.objects.count())
        self.assertEqual(0, FacilityVisit.objects.count())

    def testLayCounselorNotification(self):
        lay_num = "555666"
        lay_name = "lay_counselor"
        self.createUser(const.CTYPE_LAYCOUNSELOR, lay_num, lay_name, "80402404")
        resp = const.MOTHER_SUCCESS_REGISTERED % {"name": self.name,
                                                  "unique_id": "80403000000112"}
        lay_msg = const.NEW_MOTHER_NOTIFICATION % {"mother": "Mary Soko",
                                                   "unique_id": "80403000000112"}
        script = """
            %(num)s > REG 80403000000112 Mary Soko none %(tomorrow)s R 80402404 %(earlier)s %(later)s
            %(num)s < %(resp)s
            %(lay_num)s < %(lay_msg)s
        """ % {"num": self.user_number, "resp": resp,
               "lay_num": lay_num, "lay_msg": lay_msg,
               "tomorrow": self.tomorrow.strftime("%d %m %Y"),
               "earlier": self.earlier.strftime("%d %m %Y"),
               "later": self.later.strftime("%d %m %Y")}
        self.runScript(script)
        self.assertSessionSuccess()
        self.assertEqual(1, PregnantMother.objects.count())
        self.assertEqual(0, FacilityVisit.objects.count())

    def testDuplicateRegister(self):
        self.testRegister()
        resp = const.DUPLICATE_REGISTRATION % {"unique_id": "80403000000112"}
        script = """
            %(num)s > REG 80403000000112 Mary Someoneelse none %(tomorrow)s R 80402404 %(earlier)s %(later)s
            %(num)s < %(resp)s
        """ % {"num": self.user_number, "resp": resp,
               "tomorrow": self.tomorrow.strftime("%d %m %Y"),
               "earlier": self.earlier.strftime("%d %m %Y"),
               "later": self.later.strftime("%d %m %Y")}
        self.runScript(script)
        self.assertSessionFail()

        # make sure we didn't create a new one
        self.assertEqual(1, PregnantMother.objects.count())
        mom = PregnantMother.objects.get(uid='80403000000112')
        self.assertEqual("Soko", mom.last_name)

    def testFollowUp(self):
        self.testRegister()
        resp = const.FOLLOW_UP_COMPLETE % {"name": self.name,
                                           "unique_id": "80403000000112"}
        script = """
            %(num)s > FUP 80403000000112 R %(tomorrow)s %(later)s
            %(num)s < %(resp)s
        """ % {"num": self.user_number, "resp": resp,
               "tomorrow": self.tomorrow.strftime("%d %m %Y"),
               "later": self.later.strftime("%d %m %Y")
        }
        self.runScript(script)
        self.assertSessionSuccess()

        self.assertEqual(1, PregnantMother.objects.count())
        self.assertEqual(1, FacilityVisit.objects.count())

    def testFollowUpNotRegistered(self):
        script = """
            %(num)s > FUP 80403000000112 R %(tomorrow)s %(later)s
            %(num)s < %(resp)s
        """ % {"num": "notacontact", "resp": const.NOT_REGISTERED,
               "tomorrow": self.tomorrow.strftime("%d %m %Y"),
               "later": self.later.strftime("%d %m %Y")
              }
        self.runScript(script)
        self.assertSessionFail()

    def testFollowUpOptionalEdd(self):
        self.testRegister()
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        resp = const.FOLLOW_UP_COMPLETE % {"name": self.name,
                                           "unique_id": "80403000000112"}
        script = """
            %(num)s > FUP 80403000000112 r %(future)s
            %(num)s < %(resp)s
        """ % {"num": self.user_number, "resp": resp,
               "future": tomorrow.strftime("%d %m %Y"),
              }
        self.runScript(script)
        self.assertSessionSuccess()

        self.assertEqual(1, PregnantMother.objects.count())
        self.assertEqual(1, FacilityVisit.objects.count())

    def testFollowUpBadEdd(self):
        self.testRegister()
        resp = const.DATE_INCORRECTLY_FORMATTED_GENERAL % {"date_name": "EDD"}
        script = """
            %(num)s > FUP 80403000000112 r %(tomorrow)s not a date
            %(num)s < %(resp)s
        """ % {"num": self.user_number, "resp": resp,
               "tomorrow": self.tomorrow.strftime("%d %m %Y"),
               }
        self.runScript(script)
        self.assertSessionFail()

        self.assertEqual(1, PregnantMother.objects.count())
        self.assertEqual(0, FacilityVisit.objects.count())

    def testDatesInPastOrFuture(self):
        yesterday = (datetime.now() - timedelta(days=1)).date()
        tomorrow = (datetime.now() + timedelta(days=1)).date()

        # next visit in past
        script = """
            %(num)s > REG 80403000000112 Mary Soko none %(past)s R 80402404 %(past)s %(future)s
            %(num)s < %(resp)s
        """ % {"num": self.user_number, "past": yesterday.strftime("%d %m %Y"),
               "future": tomorrow.strftime("%d %m %Y"),
               "resp": const.DATE_MUST_BE_IN_FUTURE % {"date_name": "Next Visit",
                                                       "date": yesterday}}
        self.runScript(script)
        self.assertSessionFail()

        # lmp in future
        script = """
            %(num)s > REG 80403000000112 Mary Soko none %(future)s R 80402404 %(future)s %(future)s
            %(num)s < %(resp)s
        """ % {"num": self.user_number, "past": yesterday.strftime("%d %m %Y"),
               "future": tomorrow.strftime("%d %m %Y"),
               "resp": const.DATE_MUST_BE_IN_PAST % {"date_name": "LMP",
                                                     "date": tomorrow}}
        self.runScript(script)
        self.assertSessionFail()

        # edd in past
        script = """
            %(num)s > REG 80403000000112 Mary Soko none %(future)s R 80402404 %(past)s %(past)s
            %(num)s < %(resp)s
        """ % {"num": self.user_number, "past": yesterday.strftime("%d %m %Y"),
               "future": tomorrow.strftime("%d %m %Y"),
               "resp": const.DATE_MUST_BE_IN_FUTURE % {"date_name": "EDD",
                                                       "date": yesterday}}
        self.runScript(script)
        self.assertSessionFail()

    def testVisitReminders(self):
        self.testFollowUp()
        [mom] = PregnantMother.objects.all()
        visit = FacilityVisit.objects.get(mother=mom)
        self.assertEqual(False, visit.reminded)

        # set 10 days in the future, no reminder
        visit.next_visit = datetime.utcnow() + timedelta(days=10)
        visit.save()
        send_followup_reminders(router_obj=self.router)
        visit = FacilityVisit.objects.get(pk=visit.pk)
        self.assertEqual(False, visit.reminded)

        # set to 7 days, should now fall in threshold
        visit.next_visit = datetime.utcnow() + timedelta(days=7)
        visit.save()
        send_followup_reminders(router_obj=self.router)

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

    def testBirthCancelsVisitReminder(self):
        self.testFollowUp()
        [mom] = PregnantMother.objects.all()
        visit = FacilityVisit.objects.get(mother=mom)
        self.assertEqual(False, visit.reminded)

        # set to 7 days, should fall in threshold
        visit.next_visit = datetime.utcnow() + timedelta(days=7)
        visit.save()

        # but report a birth which should prevent the need
        resp = BIRTH_REG_RESPONSE % {"name": self.name,
                                     "unique_id": mom.uid}
        script = """
            %(num)s > birth %(id)s %(earlier)s bo h yes t2
            %(num)s < %(resp)s
        """ % {"num": self.user_number, "id": mom.uid, "resp": resp,
               "earlier": self.earlier.strftime("%d %m %Y"),
              }
        self.runScript(script)
        self.assertSessionSuccess()

        # send reminders and make sure they didn't actually fire on this one
        send_followup_reminders(router_obj=self.router)
        visit = FacilityVisit.objects.get(pk=visit.pk)
        self.assertFalse(visit.reminded)

    def testFollowUpCancelsVisitReminder(self):
        self.testFollowUp()
        [mom] = PregnantMother.objects.all()
        visit = FacilityVisit.objects.get(mother=mom)
        self.assertEqual(False, visit.reminded)

        # set to 7 days, should fall in threshold
        visit.next_visit = datetime.utcnow() + timedelta(days=7)
        visit.save()

        # but report a follow up which should prevent the need
        resp = const.FOLLOW_UP_COMPLETE % {"name": self.name,
                                           "unique_id": "80403000000112"}
        script = """
            %(num)s > FUP 80403000000112 R %(tomorrow)s %(later)s
            %(num)s < %(resp)s
        """ % {"num": self.user_number, "resp": resp,
               "tomorrow": (self.tomorrow + timedelta(days=7)).strftime("%d %m %Y"),
               "later": self.later.strftime("%d %m %Y")
               }
        self.runScript(script)
        self.assertSessionSuccess()

        [second_visit] = FacilityVisit.objects.filter(mother=mom).exclude(pk=visit.pk)
        self.assertTrue(second_visit.created_date > visit.created_date)
        # leave this one outside the reminder threshold
        second_visit.next_visit = datetime.utcnow() + timedelta(days=10)
        second_visit.save()

        # send reminders and make sure they didn't actually fire on either one
        send_followup_reminders(router_obj=self.router)
        visit = FacilityVisit.objects.get(pk=visit.pk)
        self.assertFalse(visit.reminded)
        second_visit = FacilityVisit.objects.get(pk=visit.pk)
        self.assertFalse(second_visit.reminded)

    def testEDDRemindersOneWeek(self):
        self.testRegister()
        [mom] = PregnantMother.objects.all()
        self.assertEqual(False, mom.one_week_away_reminded)

        # set 14 days in the future, no reminder since this is the one week before reminder
        mom.edd = datetime.utcnow().date() + timedelta(days=14)
        mom.save()
        send_upcoming_delivery_reminders_one_week(router_obj=self.router)
        mom = PregnantMother.objects.get(pk=mom.pk)
        self.assertEqual(False, mom.one_week_away_reminded)

        # set to 7 days, should now fall in threshold
        mom.edd = datetime.utcnow().date() + timedelta(days=7)
        mom.save()
        send_upcoming_delivery_reminders_one_week(router_obj=self.router)
        mom = PregnantMother.objects.get(pk=mom.pk)
        self.assertEqual(True, mom.one_week_away_reminded)

        reminder = const.REMINDER_UPCOMING_DELIVERY % {"name": "Mary Soko",
                                                       "unique_id": "80403000000112",
                                                       "date": mom.edd.strftime("%d %b %Y")}
        script = """
            %(num)s < %(msg)s
        """ % {"num": "456",
               "msg": reminder}
        self.runScript(script)

        [notif] = ReminderNotification.objects.all()
        self.assertEqual(mom, notif.mother)
        self.assertEqual(mom.uid, notif.mother_uid)
        self.assertEqual(self.cba, notif.recipient)
        self.assertEqual("edd_7", notif.type)

    def testEDDRemindersTwoWeek(self):
        self.testRegister()
        [mom] = PregnantMother.objects.all()
        self.assertEqual(False, mom.two_week_away_reminded)

        # set 15 days in the future, no reminder
        mom.edd = datetime.utcnow().date() + timedelta(days=15)
        mom.save()
        send_upcoming_delivery_reminders_two_week(router_obj=self.router)
        mom = PregnantMother.objects.get(pk=mom.pk)
        self.assertEqual(False, mom.two_week_away_reminded)

        # set to 14 days, should now fall in threshold
        mom.edd = datetime.utcnow().date() + timedelta(days=14)
        mom.save()
        send_upcoming_delivery_reminders_two_week(router_obj=self.router)
        mom = PregnantMother.objects.get(pk=mom.pk)
        self.assertEqual(True, mom.two_week_away_reminded)

        reminder = const.REMINDER_UPCOMING_DELIVERY % {"name": "Mary Soko",
                                                       "unique_id": "80403000000112",
                                                       "date": mom.edd.strftime("%d %b %Y")}
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

    def testEDDRemindersThreeWeek(self):
        self.testRegister()
        [mom] = PregnantMother.objects.all()
        self.assertEqual(False, mom.three_week_away_reminded)
        # set 15 days in the future, no reminder since it would be beyond the
        #threshold. of three weeks - 5 days (send_reminder_lower_bound)
        mom.edd = datetime.utcnow().date() + timedelta(days=15)
        mom.save()
        send_upcoming_delivery_reminders_three_week(router_obj=self.router)
        mom = PregnantMother.objects.get(pk=mom.pk)
        self.assertEqual(False, mom.three_week_away_reminded)
        # set to 21 days, should now fall in threshold
        mom.edd = datetime.utcnow().date() + timedelta(days=21)
        mom.save()
        send_upcoming_delivery_reminders_three_week(router_obj=self.router)
        mom = PregnantMother.objects.get(pk=mom.pk)
        self.assertEqual(True, mom.three_week_away_reminded)

        reminder = const.REMINDER_UPCOMING_DELIVERY % {"name": "Mary Soko",
                                                       "unique_id": "80403000000112",
                                                       "date": mom.edd.strftime("%d %b %Y")}
        script = """
            %(num)s < %(msg)s
        """ % {"num": "456",
               "msg": reminder}
        self.runScript(script)
        [notif] = ReminderNotification.objects.all()
        self.assertEqual(mom, notif.mother)
        self.assertEqual(mom.uid, notif.mother_uid)
        self.assertEqual(self.cba, notif.recipient)
        self.assertEqual("edd_21", notif.type)

    def testEDDRemindersFourWeek(self):
        self.testRegister()
        [mom] = PregnantMother.objects.all()
        self.assertEqual(False, mom.three_week_away_reminded)

        # set 22 days in the future, no reminder since it would be beyond the
        #threshold. of four weeks - 5 days (send_reminder_lower_bound)
        mom.edd = datetime.utcnow().date() + timedelta(days=22)
        mom.save()
        send_upcoming_delivery_reminders_four_week(router_obj=self.router)
        mom = PregnantMother.objects.get(pk=mom.pk)
        self.assertEqual(False, mom.four_week_away_reminded)

        # set to 28 days, should now fall in threshold
        mom.edd = datetime.utcnow().date() + timedelta(days=28)
        mom.save()
        send_upcoming_delivery_reminders_four_week(router_obj=self.router)
        mom = PregnantMother.objects.get(pk=mom.pk)
        self.assertEqual(True, mom.four_week_away_reminded)

        reminder = const.REMINDER_UPCOMING_DELIVERY % {"name": "Mary Soko",
                                                       "unique_id": "80403000000112",
                                                       "date": mom.edd.strftime("%d %b %Y")}
        script = """
            %(num)s < %(msg)s
        """ % {"num": "456",
               "msg": reminder}
        self.runScript(script)

        [notif] = ReminderNotification.objects.all()
        self.assertEqual(mom, notif.mother)
        self.assertEqual(mom.uid, notif.mother_uid)
        self.assertEqual(self.cba, notif.recipient)
        self.assertEqual("edd_28", notif.type)

    def testEDDRemindersFiveWeek(self):
        self.testRegister()
        [mom] = PregnantMother.objects.all()
        self.assertEqual(False, mom.three_week_away_reminded)

        # set 22 days in the future, no reminder since it would be beyond the
        #threshold. of four weeks - 5 days (send_reminder_lower_bound)
        mom.edd = datetime.utcnow().date() + timedelta(days=28)
        mom.save()
        send_upcoming_delivery_reminders_five_week(router_obj=self.router)
        mom = PregnantMother.objects.get(pk=mom.pk)
        self.assertEqual(False, mom.five_week_away_reminded)

        # set to 21 days, should now fall in threshold
        mom.edd = datetime.utcnow().date() + timedelta(days=35)
        mom.save()
        send_upcoming_delivery_reminders_five_week(router_obj=self.router)
        mom = PregnantMother.objects.get(pk=mom.pk)
        self.assertEqual(True, mom.five_week_away_reminded)

        reminder = const.REMINDER_UPCOMING_DELIVERY % {"name": "Mary Soko",
                                                       "unique_id": "80403000000112",
                                                       "date": mom.edd.strftime("%d %b %Y")}
        script = """
            %(num)s < %(msg)s
        """ % {"num": "456",
               "msg": reminder}
        self.runScript(script)

        [notif] = ReminderNotification.objects.all()
        self.assertEqual(mom, notif.mother)
        self.assertEqual(mom.uid, notif.mother_uid)
        self.assertEqual(self.cba, notif.recipient)
        self.assertEqual("edd_35", notif.type)

    def testValidLookUpMother(self):
        loc_type = LocationType.objects.get(singular='Zone')
        zone = Location.objects.filter(type=loc_type)[0]
        mom = create_mother(data={'first_name': 'Jane',
                                  'last_name': 'Doe',
                                  'uid': '333333',
                                  'location': zone})
        resp = const.LOOK_COMPLETE % {"unique_id": mom.uid}
        script = """
            %(num)s > look %(f_name)s %(l_name)s %(zone_id)s
            %(num)s < %(resp)s
        """ % {"f_name": mom.first_name, "l_name": mom.last_name,
               "zone_id": zone.slug, "resp": resp, "num": self.user_number}
        self.runScript(script)
        self.assertSessionSuccess()

    def testInvalidLookUpMother(self):
        resp = const.LOOK_MOTHER_DOES_NOT_EXIST
        script = """
            %(num)s > look does not exist
            %(num)s < %(resp)s
        """ % {"resp": resp, "num": self.user_number}
        self.runScript(script)
        self.assertSessionSuccess()
