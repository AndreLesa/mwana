from mwana.apps.smgl.tests.shared import SMGLSetUp, create_prereg_user
from mwana.apps.smgl.app import USER_SUCCESS_REGISTERED


class SMGLJoinTest(SMGLSetUp):
    fixtures = ["initial_data.json"]

    def testCreateUser(self):
        create_prereg_user("Anton", "804024", "11", "TN", "en")
        script = """
            11 > join Anton en
            11 < %s

        """ % (USER_SUCCESS_REGISTERED % {"name": "Anton",
                                          "readable_user_type": "Triage Nurse",
                                          "facility": "Chilala"})  # TODO:Is this bad testing style?
        self.runScript(script)

        script = """
            11 > join Anton sw
            11 < Anton, you are already registered as a Triage Nurse at Chilala but your details have been updated
        """
        self.runScript(script)

    def testJoin(self):
        self.createDefaults()

    def testNotPreRegd(self):
        #Will return response in Tonga since it is the default.
        script = """
            12 > join Foo Foo en
            12 < Amutujatile, tamulembedwe mumulongolongo wasikubelesya. Twakomba mutuma ku ZCAHRD kutegwa mujane lugwasyo
        """
        self.runScript(script)

    def testLeave(self):
        self.testJoin()
        script = """
        11 > leave now
        """
        self.runScript(script)

    def testQuit(self):
        self.testJoin()
        script = """
        11 > quit now
        """
        self.runScript(script)

    def testBack(self):
        self.testLeave()

        script = """
        11 > BACK now
        """
        self.runScript(script)
