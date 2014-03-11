# vim: ai ts=4 sts=4 et sw=4
from mwana.apps.smgl.tests.shared import SMGLSetUp
from mwana.apps.smgl.models import (Referral, PregnantMother,
    ReminderNotification, AmbulanceRequest, AmbulanceResponse)
from mwana.apps.smgl.app import FACILITY_NOT_RECOGNIZED, \
    AMB_RESPONSE_ALREADY_HANDLED
from mwana.apps.locations.models import Location
from mwana.apps.smgl import const
import datetime
from mwana.apps.smgl.reminders import (send_non_emergency_referral_reminders,
    send_emergency_referral_reminders, send_resp_reminders_20_mins,
    send_resp_reminders_super_user, send_no_outcome_reminder)

from mwana.apps.smgl.app import (ER_TO_TRIAGE_NURSE, ER_TO_DRIVER,
    ER_STATUS_UPDATE, AMB_RESPONSE_ORIGINATING_LOCATION_INFO,
    AMB_RESPONSE_NOT_AVAILABLE, ER_TO_CLINIC_WORKER, INITIAL_AMBULANCE_RESPONSE)


def _verbose_reasons(reasonstring):
    return ", ".join([Referral.REFERRAL_REASONS[r] for r in reasonstring.split(", ")])


class SMGLReferTest(SMGLSetUp):
    fixtures = ["initial_data.json"]

    def setUp(self):
        #Chilala is default facility
        super(SMGLReferTest, self).setUp()
        Referral.objects.all().delete()
        ReminderNotification.objects.all().delete()
        self.user_number = "123"
        self.cba_number = "456"
        self.name = "Anton"
        self.worker = self.createUser("worker", self.user_number, location="804034")
        self.cba = self.createUser("cba", self.cba_number, location="80402404")
        self.dc = self.createUser(const.CTYPE_DATACLERK, "666777",
                                  location=self.worker.location.parent.slug)

        self.tn = self.createUser(const.CTYPE_TRIAGENURSE, "666888",
                                  location=self.worker.location.parent.slug)

        self.am = self.createUser("AM", "666555")
        self.amb_tn = self.createUser(const.CTYPE_TRIAGENURSE, "222222")
        self.ha = self.createUser("worker", "666111")
        self.ha.is_help_admin = True
        self.ha.save()

        self.refferring_dc = self.createUser(const.CTYPE_DATACLERK, "666999",
                                             location="804034")
        self.refferring_ic = self.createUser(const.CTYPE_INCHARGE, "666000",
                                             location="804034")
        self.assertEqual(0, Referral.objects.count())
        self._facility_string = "Mawaya (in Kalomo District Hospital HAHC)"

    def testRefer(self):
        #Facility to Facility
        referral_facility = Location.objects.get(slug="804024")#chilala
        success_resp = const.REFERRAL_RESPONSE % {"name": self.name,
                                                  "unique_id": "1234",
                                                  "facility_name":referral_facility.name}
        notif = const.REFERRAL_FACILITY_TO_HOSPITAL_NOTIFICATION % {"unique_id": "1234",
                                               "facility_name": self.worker.location.name,
                                               "phone":self.user_number,
                                               "reason":"High Blood Pressure"
                                                }
        script = """
            %(num)s > refer 1234 %(facility_slug)s hbp 1200
            %(num)s < %(resp)s
            %(tnnum)s < %(notif)s
            %(amb_driver_num)s < %(notif)s
        """ % {"num": self.user_number, "resp": success_resp,
               "amb_driver_num": "666555", "tnnum": "222222", "notif": notif,
               "facility_slug":referral_facility.slug}
        self.runScript(script)
        self.assertSessionSuccess()

        [referral] = Referral.objects.all()
        self.assertEqual("1234", referral.mother_uid)
        self.assertEqual(Location.objects.get(slug__iexact="804024"), referral.facility)
        self.assertEqual(Location.objects.get(slug__iexact="804034"), referral.from_facility)
        self.assertTrue(referral.reason_hbp)
        self.assertEqual(["High Blood Pressure"], list(referral.get_reasons()))
        self.assertEqual(datetime.time(12, 00), referral.time)
        self.assertFalse(referral.responded)
        self.assertEqual(None, referral.mother_showed)

    def testNoRespReminder(self):
        self.testRefer()
        referral = Referral.objects.all()[0]
        send_resp_reminders_20_mins(router_obj=self.router)#Should do nothing
        self.assertEqual(False, referral.response_reminded)

        #Now set the time back by 20 mins
        referral.date = referral.date - datetime.timedelta(minutes=20)
        referral.save()
        send_resp_reminders_20_mins(router_obj=self.router)
        reminder = const.REMINDER_REFERRAL_RESP % {"unique_id": "1234",
                                                   "from_facility":referral.from_facility}
        script = """
            %(num)s < %(msg)s
            %(amb_num)s < %(msg)s
        """ % {
                "amb_num": "666555",
               "num": "222222",
               "msg": reminder}
        self.runScript(script)
        ref = Referral.objects.get(pk=referral.pk)
        self.assertEqual(True, ref.response_reminded)
        notif = ReminderNotification.objects.all()[0]
        self.assertEqual(ref.mother, notif.mother)
        self.assertEqual(ref.mother_uid, notif.mother_uid)
        self.assertEqual("ref_resp_reminder", notif.type)

    def testNoRespSuperUserNotification(self):
        #First run the first reminder to the users.
        self.testNoRespReminder()
        #Ensure we have a super user
        self.super_user = self.createUser('DC', '1500')
        self.super_user.is_super_user = True
        self.super_user.save()
        #Try to send the super user reminder which shouldn't happen as we are not
        #in range.
        send_resp_reminders_super_user(router_obj=self.router)
        referral = Referral.objects.all()[0]
        self.assertEqual(False, referral.super_user_notified)

        #Now we set the time back by 10 mins, since it is already 20 mins past
        referral.date = referral.date - datetime.timedelta(minutes=10)
        referral.save()

        send_resp_reminders_super_user(router_obj=self.router)
        send_resp_reminders_super_user(router_obj=self.router)#Don't send twice

        referral = Referral.objects.get(pk=referral.pk)
        self.assertEqual(True, referral.super_user_notified)

        ref = Referral.objects.get(pk=referral.pk)
        notif = ReminderNotification.objects.filter(type="super_user_ref_resp")[0]
        self.assertEqual(ref.mother, notif.mother)
        self.assertEqual(ref.mother_uid, notif.mother_uid)
        self.assertEqual("super_user_ref_resp", notif.type)


    def testReferNEM(self):
        #Facility to hospital, Added this one in addition to the above so that we can properly test the
        #non emergency referral.
        referral_facility = Location.objects.get(slug="804024")
        #we already have the triage nurse but we need also a data clerk for a full test
        self.data_clerk_num = "32123"
        self.data_clerk = self.createUser(const.CTYPE_DATACLERK, self.data_clerk_num)
        success_resp = const.REFERRAL_RESPONSE % {"name": self.name,
                                                  "unique_id": "1234",
                                                  "facility_name":referral_facility.name}
        notif = const.REFERRAL_NOTIFICATION % {"unique_id": "1234",
                                               "facility": "Mawaya",
                                               "reason": _verbose_reasons("hbp"),
                                               "time": "12:00",
                                               "is_emergency": "no"}
        script = """
            %(num)s > refer 1234 804024 hbp 1200 nem
            %(num)s < %(resp)s
            %(danum)s < %(notif)s
            %(tnnum)s < %(notif)s
        """ % {"num": self.user_number, "resp": success_resp,
               "danum": self.data_clerk_num, "tnnum": "222222", "notif": notif}
        self.runScript(script)
        self.assertSessionSuccess()

        [referral] = Referral.objects.all()
        self.assertEqual("1234", referral.mother_uid)
        self.assertEqual(Location.objects.get(slug__iexact="804024"), referral.facility)
        self.assertEqual(Location.objects.get(slug__iexact="804034"), referral.from_facility)
        self.assertTrue(referral.reason_hbp)
        self.assertEqual(["hbp"], list(referral.get_reasons()))
        self.assertEqual("nem", referral.status)
        self.assertEqual(datetime.time(12, 00), referral.time)
        self.assertFalse(referral.responded)
        self.assertEqual(None, referral.mother_showed)

    def testReferCBAToFacility(self):
        success_resp = const.REFERRAL_CBA_THANKS % {"facility_name":self.cba.location.parent.name,
                                                  "name":self.cba.name}
        notif = const.REFERRAL_CBA_NOTIFICATION % {"unique_id": "1234",
                                               "village": self.cba.location.name,
                                               "phone":self.cba_number,
                                               "reason":"Not Specified"}

        #Register another health worker
        self.other_worker = self.createUser("worker", "777222")
        script = """
            %(num)s > refer 1234
            %(num)s < %(resp)s
            %(in_charge_worker_num)s < %(notif)s
            %(ordinary_worker)s < %(notif)s
        """ % {"num": self.cba_number, "resp": success_resp,
                "in_charge_worker_num": "666111", "notif": notif,
                "ordinary_worker": 777222}
        self.runScript(script)
        self.assertSessionSuccess()

        [referral] = Referral.objects.all()
        self.assertEqual("1234", referral.mother_uid)
        self.assertEqual(Location.objects.get(slug__iexact="804024"), referral.facility)
        self.assertEqual(Location.objects.get(slug__iexact="80402404"), referral.from_facility)
        self.assertFalse(referral.responded)
        self.assertEqual(None, referral.mother_showed)

    def testReferCBAToFacilityReason(self):
        success_resp = const.REFERRAL_CBA_THANKS % {"facility_name":self.cba.location.parent.name,
                                                  "name":self.cba.name}
        notif = const.REFERRAL_CBA_NOTIFICATION % {"unique_id": "1234",
                                               "village": self.cba.location.name,
                                               "phone":self.cba_number,
                                               "reason":"High Blood Pressure"}

        #Register another health worker
        self.other_worker = self.createUser("worker", "777222")
        script = """
            %(num)s > refer 1234 hbp
            %(num)s < %(resp)s
            %(in_charge_worker_num)s < %(notif)s
            %(ordinary_worker)s < %(notif)s
        """ % {"num": self.cba_number, "resp": success_resp,
                "in_charge_worker_num": "666111", "notif": notif,
                "ordinary_worker": 777222}
        self.runScript(script)
        self.assertSessionSuccess()

        [referral] = Referral.objects.all()
        self.assertEqual("1234", referral.mother_uid)
        self.assertEqual(Location.objects.get(slug__iexact="804024"), referral.facility)
        self.assertEqual(Location.objects.get(slug__iexact="80402404"), referral.from_facility)
        self.assertFalse(referral.responded)
        self.assertEqual(None, referral.mother_showed)

    def testReferHospitalToHospital(self):

        self.smh_id = "1234"
        self.initiator_driver_no = "2342"
        self.initiator_tn_no = "3412"
        self.destination_tn_no = "7562"
        initiator_facility = "804031" #Zimba Mission Hospital HAHC
        initiator_facility_driver = self.createUser("AM", self.initiator_driver_no, location=initiator_facility)
        incharge = self.createUser("incharge", "1300", location=initiator_facility)
        #test that clinic workers get response
        initiator_clinic_worker = self.createUser("worker", "3000", location=initiator_facility)
        self.initiator_facility_tn = self.createUser("TN", self.initiator_tn_no, location=initiator_facility)
        destination_facility = "804030" #Kalomo Mission Hospital HAHC
        self.destination_facility_tn = self.createUser("TN", self.destination_tn_no, location=destination_facility)
        amb_status = "OTW"
        server_resp = const.REFERRAL_RESPONSE % {"name": self.name,
                                                  "unique_id": self.smh_id,
                                                  "facility_name":self.destination_facility_tn.location.name}
        dest_nurse_notif = const.REFERRAL_TO_DESTINATION_HOSPITAL_NURSE  %{
            "unique_id":self.smh_id,
            "reason":"High Blood Pressure",
            "from_facility":"Zimba Mission Hospital HAHC",
            "referral_facility": "Kalomo District Hospital HAHC",
            "name":"Anton",
            "title": "Triage Nurse",
            "phone": "3412"}
        amb_status_notif = const.REFERRAL_AMBULANCE_STATUS_TO_REFERRING_HOSPITAL %{ 'unique_id':self.smh_id,
                                                                                                 'status':amb_status,
                                                                                                 'phone':initiator_facility_driver.default_connection.identity}
        initiator_hosp_notif = const.REFERRAL_TO_HOSPITAL_DRIVER %{"referring_facility":self.initiator_facility_tn.location.name,
                                                                 "referral_facility":self.destination_facility_tn.location.name
                                                                }

        script = """
        %(initiator_facility_tn)s > REFER %(smh_id)s %(destination_facility)s hbp 1200 em
        %(initiator_facility_tn)s < %(server_resp)s
        %(initiator_facility_driver)s < %(initiator_hosp_notif)s
        %(initiator_facility_tn)s < %(initiator_hosp_notif)s
        %(destination_facility_nurse)s < %(dest_nurse_notif)s
        """%{'initiator_facility_tn':self.initiator_tn_no, 'smh_id':self.smh_id, 'destination_facility':destination_facility,
            'server_resp':server_resp, 'initiator_facility_driver':self.initiator_driver_no,
             'initiator_facility_nurse':self.initiator_tn_no, 'destination_facility_nurse':self.destination_tn_no,
             'amb_status_notif':amb_status, "initiator_hosp_notif":initiator_hosp_notif, "dest_nurse_notif":dest_nurse_notif}

        self.runScript(script)
        self.assertSessionSuccess()
        [referral] = Referral.objects.filter(from_facility__slug="804031")
        self.assertEqual("1234", referral.mother_uid)
        self.assertEqual(Location.objects.get(slug__iexact="804030"), referral.facility)
        self.assertEqual(Location.objects.get(slug__iexact="804031"), referral.from_facility)
        self.assertTrue(referral.reason_hbp)
        self.assertEqual(["High Blood Pressure"], list(referral.get_reasons()))
        self.assertEqual("em", referral.status)
        self.assertEqual(datetime.time(12, 00), referral.time)
        self.assertFalse(referral.responded)
        self.assertEqual(None, referral.mother_showed)

    def testReferResponseHospitalToHospital(self):
        self.testReferHospitalToHospital()
        amb_status = "OTW"
        amb_status_notif = const.AMB_RESP_STATUS%{
                                                    "unique_id":self.smh_id,
                                                    "status":amb_status,
                                                    "phone":self.initiator_driver_no
                                                           }
        resp_notif =const.REF_TRIAGE_NURSE_RESP_NOTIF%{
                                        "unique_id":self.smh_id,
                                        "phone":self.destination_tn_no,
                                        "title": "Triage Nurse",
                                        "name": "Anton"
                                        }
        resp_thanks = const.RESP_THANKS %{
                                          "name":self.name,
                                          "unique_id":self.smh_id
                                          }

        script = """
        %(initiator_facility_driver)s > RESP %(smh_id)s %(amb_status)s
        666888 < %(amb_status_notif)s
        %(destination_facility_nurse)s < %(amb_status_notif)s
        %(initiator_facility_tn)s < %(amb_status_notif)s
        """%{"initiator_facility_driver":self.initiator_driver_no, "initiator_facility_tn":self.initiator_tn_no, "smh_id":self.smh_id, "amb_status":amb_status,
             "amb_status_notif":amb_status_notif, "resp_thanks":resp_thanks, "resp_notif":resp_notif, "destination_facility_nurse":self.destination_tn_no}
        self.runScript(script)

    def testReferResponseHospitalToHospitalTriageNurse(self):
        self.testReferHospitalToHospital()
        amb_status = "OTW"
        amb_status_notif = const.AMB_RESP_STATUS%{
                                                    "unique_id":self.smh_id,
                                                    "status":amb_status,
                                                    "phone":self.initiator_driver_no
                                                           }
        resp_notif =const.REF_TRIAGE_NURSE_RESP_NOTIF%{
                                        "unique_id":self.smh_id,
                                        "phone":self.destination_tn_no,
                                        "title":"Triage Nurse",
                                        "name":"Anton"
                                        }
        resp_thanks = const.RESP_THANKS %{
                                          "name":self.name,
                                          "unique_id":self.smh_id
                                          }

        script = """
        %(destination_facility_nurse)s > RESP %(smh_id)s
        666888 < %(resp_notif)s
        %(destination_facility_nurse)s < %(resp_thanks)s
        %(initiator_facility_driver)s < %(resp_notif)s
        %(initiator_facility_tn)s < %(resp_notif)s
        """%{"initiator_facility_driver":self.initiator_driver_no, "initiator_facility_tn":self.initiator_tn_no, "smh_id":self.smh_id, "amb_status":amb_status,
             "amb_status_notif":amb_status_notif, "resp_thanks":resp_thanks, "resp_notif":resp_notif, "destination_facility_nurse":self.destination_tn_no}
        self.runScript(script)

    def testReferResponseCommunityToFacility(self):
        self.testReferCBAToFacility()
        thank_message = const.RESP_THANKS % {
            "unique_id": 1234,
            "name": self.amb_tn.name
        }
        notify_others = const.REFERRAL_RESPONSE_NOTIFICATION_OTHER_USERS%{
            "unique_id": 1234,
            "name": self.amb_tn.name,
            "user_type": "Triage Nurse"
        }
        script = """
        %(facility_tn)s > RESP %(unique_id)s OTW
        %(facility_tn)s < %(thanks)s
        %(num)s < %(resp)s
        %(other_health_worker)s < %(notify_others)s
        %(health_worker)s < %(notify_others)s
        """%{"unique_id":"1234",
             "facility_tn":"222222",
             "num":"456",
             "resp":const.RESP_CBA_UPDATE,
             "thanks": thank_message,
             "health_worker": "666111",
             "other_health_worker": "777222",
             "notify_others":notify_others}
        self.runScript(script)

    def testReferRefOutCommunityToFacility(self):
        self.testReferResponseCommunityToFacility()

        script = """
        %(facility_tn)s > refout 1234 stb cri vag
        """%{
            "facility_tn":222222
        }
        self.runScript(script)

    def testMultiAmbDriverResponse(self):
        #Test that when an ambulance driver responds the other driver is notified and
        self.second_amb_driver = self.createUser("AM", "777888")
        self.testRefer()
        #At this point all the drivers have received the notification
        script = """
        %(second_driver)s > RESP 1234 OTW
        """%{
            "second_driver":777888
        }
        self.runScript(script)

    def testReferForwarding(self):
        #Used to test referrals that have been forwarded from one facility to another.
        self.testRefer()#at this point, the referred mother should be at chilala
        referring_facility = Location.objects.get(slug="804024")#chilala
        dest_facility = Location.objects.get(slug="804030")#Kalomo
        self.amb_driver_no = "43422"
        self.dc_no = "3452"
        self.dest_tn = "666888" #self.tn is 666888 and is at Kalomo (From the SetUp method)

        self.dc = self.createUser(const.CTYPE_DATACLERK, self.dc_no, location=referring_facility.slug)
        self.dest_amb = self.createUser("AM", self.amb_driver_no, location=dest_facility.slug)

        success_resp = const.REFERRAL_RESPONSE % {"name": self.name,
                                                  "unique_id": "1234",
                                                  "facility_name":dest_facility.name}
        notif = const.REFERRAL_FACILITY_TO_HOSPITAL_NOTIFICATION % {"unique_id": "1234",
                                               "facility_name": referring_facility.name,
                                               "phone":self.dc_no,
                                               "reason": "HBP",

                                                }
        script = """
            %(num)s > refer 1234 %(facility_slug)s hbp 1200
            %(num)s < %(resp)s
            %(tnnum)s < %(notif)s
            %(amb_driver_num)s < %(notif)s
        """ % {"num": self.dc_no, "resp": success_resp,
               "amb_driver_num": self.amb_driver_no, "tnnum": self.dest_tn, "notif": notif,
               "facility_slug":dest_facility.slug}
        self.runScript(script)
        self.assertSessionSuccess()


    def testReferFowardResponse(self):
        #This is specifically for when a triage nurse responds
        #Mother has been referred from community to Chilala, then from Chilala to Kalomo
        self.testReferForwarding()
        resp_notif = const.REF_TRIAGE_NURSE_RESP_NOTIF %{
                                                "unique_id":1234,
                                                "phone":self.dest_tn
                                                                           }
        resp_notif_status = const.REF_TRIAGE_NURSE_RESP_NOTIF_STATUS %{
                    "unique_id": "1234",
                    "phone": self.dest_tn,
                    "title": ",".join([contact_type.name for contact_type in self.tn.types.all()]),
                    "status": "otw"
                }
        thank_message = const.RESP_THANKS %{
                                          "name":self.tn.name,
                                          "unique_id":"1234"
                                          }

        script = """
            %(tn)s > resp 1234 otw
            %(tn)s < %(thank_message)s
            %(origin_dc)s < %(resp_notif_status)s
            """ %{
                  "tn":self.dest_tn,
                  "resp_notif":resp_notif,
                  "resp_notif_status":resp_notif_status,
                  "thank_message":thank_message,
                  "origin_dc":self.dc_no
                  }
        self.runScript(script)


    def testReferFowardRefout(self):
        self.testReferFowardResponse()
        notification_origin =  const.REFERRAL_OUTCOME_NOTIFICATION % {
            "unique_id": "1234",
            "date": datetime.datetime.now().date().strftime('%d %b %Y'),
            "mother_outcome": "stable",
            "baby_outcome": "critical",
            "delivery_mode": "vaginal"
        }

        notification_dest = const.REFERRAL_OUTCOME_NOTIFICATION_DEST %\
            {
                "unique_id":"1234",
                "name": self.tn.name,
                "date":datetime.datetime.now().date().strftime('%d %b %Y'),
                "origin":"Chilala"
            }
        thank_message = const.REFERRAL_OUTCOME_RESPONSE % {"name": self.name,
                                                  "unique_id": "1234"}
        script = """
            %(tn)s > refout 1234 stb cri vag otw
            666777 < %(refout_dest)s
            666999 < %(refout_origin)s
            %(origin_dc)s < %(refout_origin)s
            %(old_origin)s < %(refout_origin)s
            666000 < %(refout_origin)s
            666111 < %(refout_origin)s
            43422 < %(refout_origin)s
            %(tn)s < %(thank_message)s
            """%{
                 "tn":self.dest_tn,
                 "refout_origin":notification_origin,
                 "thank_message":thank_message,
                 "origin_dc": self.dc_no,
                 "old_origin":"123",
                 "refout_dest": notification_dest}
        self.runScript(script)
        self.assertSessionSuccess()

    def testReferForwardRefoutReminder(self):
        #Test for reminders for refout that should go to only the latest facility
        #where the referral is and not the past ones.
        self.testReferFowardResponse()
        first_ref, second_ref = Referral.objects.all()
        #Try to send out the reminders, shouldn't do anything since not in time range
        send_no_outcome_reminder(router_obj=self.router)
        self.assertEqual(False, first_ref.reminded)
        self.assertEqual(False, second_ref.reminded)

        #Set the time back
        first_ref.date = first_ref.date - datetime.timedelta(hours=12)
        first_ref.save()
        second_ref.date = second_ref.date - datetime.timedelta(hours=12)
        second_ref.save()


        #Send the reminders, they should only go to the latest referral since it
        #is a re-referral based on the first one. Wouldn't make sense to ask the
        #first people for out come when they already referred.
        send_no_outcome_reminder(router_obj=self.router)
        first_ref = Referral.objects.get(pk=first_ref.pk)
        second_ref = Referral.objects.get(pk=second_ref.pk)
        self.assertEqual(False, first_ref.reminded)
        self.assertEqual(True, second_ref.reminded)


    def testTemp(self):
        script = """
        123 > refer 1234 804031 hbp 1200
        """
        self.runScript(script)

    def testRefoutReminderHospital(self):
        self.testTemp()
        self.testReferHospitalToHospital()
        first_ref, second_ref = Referral.objects.all()
        #Try to send out the reminders, shouldn't do anything since not in time range
        send_no_outcome_reminder(router_obj=self.router)
        self.assertEqual(False, first_ref.reminded)
        self.assertEqual(False, second_ref.reminded)

        #Set the time back
        first_ref.date = first_ref.date - datetime.timedelta(hours=13)
        first_ref.save()
        second_ref.date = second_ref.date - datetime.timedelta(hours=12)
        second_ref.save()

        #Send the reminders, they should only go to the latest referral since it
        #is a re-referral based on the first one. Wouldn't make sense to ask the
        #first people for out come when they already referred.
        send_no_outcome_reminder(router_obj=self.router)
        first_ref = Referral.objects.get(pk=first_ref.pk)
        second_ref = Referral.objects.get(pk=second_ref.pk)
        self.assertEqual(False, first_ref.reminded)
        self.assertEqual(True, second_ref.reminded)



    def testReferForwardSuperUserReminder(self):
        self.testReferForwardRefoutReminder()
        self.super_user = self.createUser('DC', '1500')
        self.super_user.is_super_user = True
        self.super_user.save()

        first_ref, second_ref = Referral.objects.all()
        send_resp_reminders_super_user(router_obj=self.router)

        #set the time back by another 12 hours since it is currently 12 hours behind
        first_ref.date = first_ref.date - datetime.timedelta(hours=12)
        first_ref.save()

        second_ref.date = second_ref.date - datetime.timedelta(hours=12)
        second_ref.save()

        send_resp_reminders_super_user(router_obj=self.router)



    def testReferPick(self):
        self.testReferHospitalToHospital()
        pick_thanks = const.PICK_THANKS %{
                                          "unique_id":self.smh_id
                                          }

        script = """
        %(amb_driver)s > PICK %(smh_id)s
        %(amb_driver)s < %(pick_thanks)s
        """%{
             "amb_driver":self.initiator_driver_no,
             "smh_id":self.smh_id,
             "pick_thanks":pick_thanks
             }
        self.runScript(script)

    def testReferDrop(self):
        self.testReferPick()

        drop_thanks = const.DROP_THANKS %{
                                          "unique_id":self.smh_id
                                          }

        script = """
        %(amb_driver)s > DROP %(smh_id)s
        %(amb_driver)s < %(drop_thanks)s
        """%{
             "amb_driver":self.initiator_driver_no,
             "smh_id":self.smh_id,
             "drop_thanks":drop_thanks
             }
        self.runScript(script)


    def testReferNotRegistered(self):
        script = """
            %(num)s > refer 1234 804024 hbp 1200 nem
            %(num)s < %(resp)s
        """ % {"num": "notacontact", "resp": const.NOT_REGISTERED}
        self.runScript(script)
        self.assertSessionFail()

    def testMultipleResponses(self):
        referral_facility = Location.objects.get(slug="804030")
        success_resp = const.REFERRAL_FACILITY_TO_HOSPITAL_NOTIFICATION % {"name": self.name,
                                                  "unique_id": "1234",
                                                  "facility_name":referral_facility.name,
                                                  "phone": self.user_number,
                                                  "reason": ""
                                                  }
        notif = const.REFERRAL_NOTIFICATION % {"unique_id": "1234",
                                               "facility": self.worker.location.name,
                                               "reason": _verbose_reasons("ec, fd, hbp, pec"),
                                               "time": "12:00",
                                               "is_emergency": "no",
                                                }
        script = """
            %(num)s > refer 1234 %(facility_slug)s hbp,fd,pec,ec 1200 nem
            %(num)s < %(resp)s
            %(tnnum)s < %(notif)s
            %(danum)s < %(notif)s
        """ % {"num": self.user_number, "resp": success_resp,
               "danum": "666777", "tnnum": "666888", "notif": notif,
               "facility_slug":referral_facility.slug}
        self.runScript(script)
        self.assertSessionSuccess()
        [referral] = Referral.objects.all()
        self.assertEqual("1234", referral.mother_uid)
        self.assertEqual(Location.objects.get(slug__iexact="804030"), referral.facility)
        self.assertTrue(referral.reason_hbp)
        reasons = list(referral.get_reasons())
        self.assertEqual(4, len(reasons))
        for r in "hbp,fd,pec,ec".split(","):
            self.assertTrue(referral.get_reason(r))
        self.assertEqual("nem", referral.status)

    def testReferBadCode(self):
        bad_code_resp = 'Answer must be one of the choices for "Reason for referral, choices: fd, pec, ec, hbp, pph, aph, pl, cpd, oth, pp"'
        script = """
            %(num)s > refer 1234 804024 foo 1200 nem
            %(num)s < %(resp)s
        """ % {"num": self.user_number, "resp": bad_code_resp}
        self.runScript(script)
        # self.assertSessionFail() # TODO: this is a real error that needs fixing
        self.assertEqual(0, Referral.objects.count())

    def testReferBadLocation(self):
        bad_loc_resp = FACILITY_NOT_RECOGNIZED % {"facility": "notaplace"}
        script = """
            %(num)s > refer 1234 notaplace hbp 1200 nem
            %(num)s < %(resp)s
        """ % {"num": self.user_number, "resp": bad_loc_resp}
        self.runScript(script)
        self.assertSessionFail()
        self.assertEqual(0, Referral.objects.count())

    def testReferBadTimes(self):
        for bad_time in ["foo", "13", "55555", "013A", "A130"]:
            resp = const.TIME_INCORRECTLY_FORMATTED % {"time": bad_time}
            script = """
                %(num)s > refer 1234 804024 hbp %(time)s nem
                %(num)s < %(resp)s
            """ % {"num": self.user_number, "time": bad_time, "resp": resp}
            self.runScript(script)
            self.assertSessionFail()
            self.assertEqual(0, Referral.objects.count())

    def testReferGoodTimes(self):
        referral_facility = Location.objects.get(slug="804024")
        resp = const.REFERRAL_RESPONSE % {"name": self.name,
                                          "unique_id": "1234",
                                          "facility_name":referral_facility.name}
        for good_time in ["0900", "900"]:
            script = """
                %(num)s > refer 1234 804024 hbp %(time)s nem
                %(num)s < %(resp)s
            """ % {"num": self.user_number, "time": good_time, "resp": resp}
            self.runScript(script)
            self.assertSessionSuccess()
            self.assertEqual(1, Referral.objects.count())
            Referral.objects.all().delete() # cleanup for the next one

    def testReferralOutcome(self):
        self.testRefer()
        resp = const.REFERRAL_OUTCOME_RESPONSE % {"name": self.name,
                                                  "unique_id": "1234"}

        self.dest_ic = self.createUser(const.CTYPE_INCHARGE, "9834",
                                             location="804024")

        notify = const.REFERRAL_OUTCOME_NOTIFICATION % {
            "unique_id": "1234",
            "date": datetime.datetime.now().strftime('%d %b %Y'),
            "mother_outcome": "critical",
            "baby_outcome": "critical",
            "delivery_mode": "vaginal"
       }

        notification_dest = const.REFERRAL_OUTCOME_NOTIFICATION_DEST %\
            {
                "unique_id":"1234",
                "name": self.worker.name,
                "date":datetime.datetime.now().strftime('%d %b %Y'),
                "origin":"Mawaya"
            }
        script = """
            666111 > refout 1234 cri cri vag
            %(num)s < %(notify)s
            %(dc_num)s < %(notify)s
            %(ic_num)s < %(notify)s
            %(dest_ic)s < %(dest_notif)s
            666111 < %(resp)s

        """ % {"num": self.user_number, "resp": resp,
               "notify": notify, "dest_notif":notification_dest,
               "dc_num": "666999", "ic_num": "666000", "dest_ic":self.dest_ic.default_connection.identity}
        self.runScript(script)
        self.assertSessionSuccess()
        [ref] = Referral.objects.all()
        self.assertTrue(ref.responded)
        self.assertTrue(ref.mother_showed)
        self.assertEqual("cri", ref.mother_outcome)
        self.assertEqual("cri", ref.baby_outcome)
        self.assertEqual("vag", ref.mode_of_delivery)

    def testReferralOutcomeDOTW(self):
        self.testRefer()
        resp = const.REFERRAL_OUTCOME_RESPONSE % {"name": self.name,
                                                  "unique_id": "1234"}

        self.dest_ic = self.createUser(const.CTYPE_INCHARGE, "9834",
                                             location="804024")

        notify = const.REFERRAL_OUTCOME_NOTIFICATION % {
            "unique_id": "1234",
            "date": datetime.datetime.now().strftime('%d %b %Y'),
            "mother_outcome": "Dead on the Way",
            "baby_outcome": "Dead on the Way",
            "delivery_mode": "none"
       }

        notification_dest = const.REFERRAL_OUTCOME_NOTIFICATION_DEST %\
            {
                "unique_id":"1234",
                "name": self.worker.name,
                "date":datetime.datetime.now().strftime('%d %b %Y'),
                "origin":"Mawaya"
            }
        script = """
            666111 > refout 1234 dotw dotw none
            %(num)s < %(notify)s
            %(dc_num)s < %(notify)s
            %(ic_num)s < %(notify)s
            %(dest_ic)s < %(dest_notif)s
            666111 < %(resp)s

        """ % {"num": self.user_number, "resp": resp,
               "notify": notify, "dest_notif":notification_dest,
               "dc_num": "666999", "ic_num": "666000", "dest_ic":self.dest_ic.default_connection.identity}
        self.runScript(script)
        self.assertSessionSuccess()
        [ref] = Referral.objects.all()
        self.assertTrue(ref.responded)
        self.assertTrue(ref.mother_showed)
        self.assertEqual("dotw", ref.mother_outcome)
        self.assertEqual("dotw", ref.baby_outcome)
        self.assertEqual("none", ref.mode_of_delivery)

    def testReferralOutcomeNoShow(self):
        self.testRefer()
        resp = const.REFERRAL_OUTCOME_RESPONSE % {"name": self.name,
                                                  "unique_id": "1234"}
        notify = const.REFERAL_OUTCOME_NOTIFICATION_NOSHOW % {
            "unique_id": "1234",
            "date": datetime.datetime.now().strftime("%d %b %Y"),
       }
        script = """
            %(num)s > refout 1234 noshow
            %(num)s < %(resp)s
            %(num)s < %(notify)s
            %(dc_num)s < %(notify)s
            %(ic_num)s < %(notify)s
        """ % {"num": self.user_number, "resp": resp, "notify": notify,
                "dc_num": "666999", "ic_num": "666000"}
        self.runScript(script)
        self.assertSessionSuccess()
        [ref] = Referral.objects.all()
        self.assertTrue(ref.responded)
        self.assertFalse(ref.mother_showed)

    def testReferralOutcomeNoRef(self):
        resp = const.REFERRAL_NOT_FOUND % {"unique_id": "1234"}
        script = """
            %(num)s > refout 1234 stb stb vag
            %(num)s < %(resp)s

        """ % {"num": self.user_number, "resp": resp}
        self.runScript(script)
        self.assertSessionFail()

    def testReferWithMother(self):
        yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).date()
        tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).date()
        resp = const.MOTHER_SUCCESS_REGISTERED % {"name": self.name,
                                                   "unique_id": "1234"}
        script = """
            %(num)s > REG 1234 Mary Soko none %(future)s R 80402404 %(past)s %(future)s
            %(num)s < %(resp)s
        """ % {"num": "666777", "resp": resp,
               "past": yesterday.strftime("%d %m %Y"),
               "future": tomorrow.strftime("%d %m %Y")}
        self.runScript(script)
        self.assertSessionSuccess()
        mom = PregnantMother.objects.get(uid='1234')
        self.testReferNEM()
        [ref] = Referral.objects.all()
        self.assertEqual(mom.uid, ref.mother_uid)
        self.assertEqual(mom, ref.mother)

    def testNonEmergencyReminders(self):
        self.testReferWithMother()
        [ref] = Referral.objects.all()
        self.assertEqual(False, ref.reminded)
        self.assertEqual(1, Referral.non_emergencies().count())

        # this should do nothing because it's not in range
        send_non_emergency_referral_reminders(router_obj=self.router)
        ref = Referral.objects.get(pk=ref.pk)
        self.assertEqual(False, ref.reminded)

        # set the date back so it triggers a reminder
        ref.date = ref.date - datetime.timedelta(days=7)
        ref.save()
        send_non_emergency_referral_reminders(router_obj=self.router)
        reminder = const.REMINDER_NON_EMERGENCY_REFERRAL % {"name": "Mary Soko",
                                                            "unique_id": "1234",
                                                            "loc": "Chilala"}
        script = """
            %(num)s < %(msg)s
        """ % {"num": self.cba_number,
               "msg": reminder}
        self.runScript(script)

        ref = Referral.objects.get(pk=ref.pk)
        self.assertEqual(True, ref.reminded)
        [notif] = ReminderNotification.objects.all()
        self.assertEqual(ref.mother, notif.mother)
        self.assertEqual(ref.mother_uid, notif.mother_uid)
        self.assertEqual(self.cba, notif.recipient)
        self.assertEqual("nem_ref", notif.type)

    def testEmergencyReminders(self):
        self.testReferWithMother()
        [ref] = Referral.objects.all()
        ref.status = 'em'
        ref.save()
        self.assertEqual(False, ref.reminded)
        self.assertEqual(1, Referral.emergencies().count())

        em_dc = self.createUser(const.CTYPE_DATACLERK, "777777",
                                location='804030')

        # this should do nothing because it's not in range
        send_emergency_referral_reminders(router_obj=self.router)
        ref = Referral.objects.get(pk=ref.pk)
        self.assertEqual(False, ref.reminded)

        # set the time back so it triggers a reminder
        ref.date = ref.date - datetime.timedelta(hours=12)
        ref.save()
        send_emergency_referral_reminders(router_obj=self.router)
        reminder = const.REMINDER_EMERGENCY_REFERRAL % {"unique_id": "1234",
                                                        "date": ref.date.date(),
                                                        "loc": "Mawaya"}


        script = """
            %(num)s < %(msg)s
        """ % {"num": "222222",
               "msg": reminder}
        self.runScript(script)

        ref = Referral.objects.get(pk=ref.pk)
        self.assertEqual(True, ref.reminded)
        notif = ReminderNotification.objects.all()[0]
        self.assertEqual(ref.mother, notif.mother)
        self.assertEqual(ref.mother_uid, notif.mother_uid)
        self.assertEqual(self.data_clerk, notif.recipient)
        self.assertEqual("em_ref", notif.type)

    def testReferEmNotAvailableWorkflow(self):
        tnnum = '222222'
        referral_facility = Location.objects.get(slug="804024")
        success_resp = const.REFERRAL_RESPONSE % {"name": self.name,
                                                  "unique_id": "1234",
                                                  "facility_name":referral_facility.name}
        notif = const.REFERRAL_FACILITY_TO_HOSPITAL_NOTIFICATION % {"unique_id": "1234",
                                               "facility_name": self.worker.location.name,
                                               "phone":self.user_number
                                                }
        script = """
            %(num)s > refer 1234 804024 hbp 1200
            %(num)s < %(resp)s
            %(tnnum)s < %(tn_notif)s
            %(amnum)s < %(am_notif)s
        """ % {"num": self.user_number, "amnum": "666555", "tnnum": tnnum,
               "resp": success_resp,
               "tn_notif": notif,
               "am_notif": notif}
        self.runScript(script)
        self.assertSessionSuccess()

        [referral] = Referral.objects.all()
        self.assertEqual("1234", referral.mother_uid)
        self.assertEqual(Location.objects.get(slug__iexact="804024"), referral.facility)
        self.assertEqual(Location.objects.get(slug__iexact="804034"), referral.from_facility)
        self.assertTrue(referral.reason_hbp)
        self.assertEqual(["hbp"], list(referral.get_reasons()))
        self.assertEqual("em", referral.status)
        self.assertEqual(datetime.time(12, 00), referral.time)
        self.assertFalse(referral.responded)
        self.assertEqual(None, referral.mother_showed)

        [amb_req] = AmbulanceRequest.objects.all()
        self.assertEqual("1234", amb_req.mother_uid)
        self.assertEqual("666555", amb_req.ambulance_driver.default_connection.identity)
        self.assertEqual(tnnum, amb_req.triage_nurse.default_connection.identity)

        # Test NA Response
        self.assertEqual(0, AmbulanceResponse.objects.count())
        d = {
            "unique_id": '1234',
            "status": "NA",
            "confirm_type": "Triage Nurse",
            "name": "Anton",
            "from_location": 'Mawaya',
            "sender_phone_number": self.user_number
       }

        response_string = ER_STATUS_UPDATE % d
        d['response'] = 'NA'
        response_to_referrer_string = AMB_RESPONSE_ORIGINATING_LOCATION_INFO % d
        amb_na_string = AMB_RESPONSE_NOT_AVAILABLE % d

        script = """
            %(tnnum)s > resp 1234 na

            %(sunum)s < %(su_notif)s
        """ % {"num": self.user_number, "amnum": "666555", "tnnum": tnnum,
               "sunum": "666111",
               "resp": response_string,
               "su_notif": amb_na_string,
               "notif": response_to_referrer_string}
        self.runScript(script)
        self.assertSessionSuccess()
        [amb_req] = AmbulanceRequest.objects.all()
        [amb_resp] = AmbulanceResponse.objects.all()
        self.assertEqual(amb_req, amb_resp.ambulance_request)
        self.assertEqual("1234", amb_resp.mother_uid)
        self.assertEqual("na", amb_resp.response)
        self.assertEqual(tnnum, amb_resp.responder.default_connection.identity)
