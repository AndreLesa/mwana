from mwana.apps.smgl.tests.shared import SMGLSetUp 
from mwana.apps.smgl.models import PregnantMother, FacilityVisit
from mwana.apps.smgl import const


class SMGLPregnancyTest(SMGLSetUp):
    fixtures = ["initial_data.json"]
    
    def setUp(self):
        super(SMGLPregnancyTest, self).setUp()
        self.createDefaults()
        self.user_number = "15"
        self.name = "AntonDA"
        
    def testRegister(self):
        self.assertEqual(0, PregnantMother.objects.count())
        self.assertEqual(0, FacilityVisit.objects.count())
        resp = const.MOTHER_SUCCESS_REGISTERED % { "name": self.name,
                                                  "unique_id": "80403000000112" }
        script = """
            %(num)s > REG 80403000000112 Mary SOKO none 04 08 2012 R 80402404 12 02 2012 18 11 2012
            %(num)s < %(resp)s            
        """ % { "num": self.user_number, "resp": resp }
        self.runScript(script)
        
        self.assertEqual(1, PregnantMother.objects.count())
        self.assertEqual(1, FacilityVisit.objects.count())
    
    def testRegisterWithBadZone(self):
        self.assertEqual(0, PregnantMother.objects.count())
        self.assertEqual(0, FacilityVisit.objects.count())
        resp = const.UNKOWN_ZONE % { "zone": "notarealzone" }
        script = """
            %(num)s > REG 80403000000112 Mary SOKO none 04 08 2012 R notarealzone 12 02 2012 18 11 2012
            %(num)s < %(resp)s            
        """ % { "num": self.user_number, "resp": resp }
        self.runScript(script)
        self.assertEqual(0, PregnantMother.objects.count())
        self.assertEqual(0, FacilityVisit.objects.count())
    
    def testFollowUp(self):
        self.testRegister()
        resp = const.FOLLOW_UP_COMPLETE % { "name": self.name,
                                            "unique_id": "80403000000112" }
        script = """
            %(num)s > FUP 80403000000112 02 12 2012 R 18 11 2012
            %(num)s < %(resp)s            
        """ % { "num": self.user_number, "resp": resp }
        self.runScript(script)
        
        self.assertEqual(1, PregnantMother.objects.count())
        self.assertEqual(2, FacilityVisit.objects.count())
    