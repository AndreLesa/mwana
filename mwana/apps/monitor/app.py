# vim: ai ts=4 sts=4 et sw=4
import logging
import rapidsms
from scheduler.models import EventSchedule

logger = logging.getLogger(__name__)

class App (rapidsms.apps.base.AppBase):


    def start (self):
        #self.schedule_monitor_task()
        pass

    def schedule_monitor_task(self):
        callback = 'mwana.apps.monitor.tasks.send_monitor_report'
        EventSchedule.objects.filter(callback=callback).delete()
        EventSchedule.objects.create(callback=callback, hours=[8, 13, 16], minutes=[20],
                                     days_of_week=[0, 1, 2, 3, 4, 5, 6])
