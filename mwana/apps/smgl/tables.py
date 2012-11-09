from django.core.urlresolvers import reverse

from djtables import Table, Column
from djtables.column import DateColumn


class NamedColumn(Column):
    """
    A custom Column class that allows for a non-field based Column Name
    """
    def __init__(self, col_name=None, *args, **kwargs):
        super(NamedColumn, self).__init__(*args, **kwargs)
        self._col_name = col_name
        self._header_class = "upper"

    def __unicode__(self):
        return self._col_name or self.name


class PregnantMotherTable(Table):
    created_date = DateColumn(format="Y m d H:i ")
    uid = Column(link=lambda cell: reverse("mother-history", args=[cell.object.id]))
    location = Column()
    edd = DateColumn(format="d/m/Y")
    risks = Column(value=lambda cell: ", ".join([x.upper() \
                                     for x in cell.object.get_risk_reasons()]),
                   sortable=False)

    class Meta:
        order_by = "-created_date"


class HistoryTable(Table):
    date = Column()
    type = Column()
    sender = Column()
    facility = Column()
    message = Column()

    class Meta:
        order_by = "-date"


class StatisticsTable(Table):
    location = Column()
    births_com = NamedColumn(col_name="COM")
    births_fac = NamedColumn(col_name="FAC")
    births_total = NamedColumn(col_name="Total")
    infant_deaths_com = NamedColumn(col_name="COM")
    infant_deaths_fac = NamedColumn(col_name="FAC")
    infant_deaths_total = NamedColumn(col_name="Total")
    mother_deaths_com = NamedColumn(col_name="COM")
    mother_deaths_fac = NamedColumn(col_name="FAC")
    mother_deaths_total = NamedColumn(col_name="Total")
    anc1 = NamedColumn(col_name="1 ANC")
    anc2 = NamedColumn(col_name="2 ANCs")
    anc3 = NamedColumn(col_name="3 ANCs")
    anc4 = NamedColumn(col_name="4 ANCs")
    pos1 = NamedColumn(col_name="1 POS")
    pos2 = NamedColumn(col_name="2 POS")
    pos3 = NamedColumn(col_name="3 POS")

    class Meta:
        order_by = "location"


class StatisticsLinkTable(StatisticsTable):

    location = Column(link=lambda cell:
                                reverse("district-stats",
                                    args=[cell.object['location'].id]
                                )
                    )
    births_com = NamedColumn(col_name="COM")
    births_fac = NamedColumn(col_name="FAC")
    births_total = NamedColumn(col_name="Total")
    infant_deaths_com = NamedColumn(col_name="COM")
    infant_deaths_fac = NamedColumn(col_name="FAC")
    infant_deaths_total = NamedColumn(col_name="Total")
    mother_deaths_com = NamedColumn(col_name="COM")
    mother_deaths_fac = NamedColumn(col_name="FAC")
    mother_deaths_total = NamedColumn(col_name="Total")
    anc1 = NamedColumn(col_name="1 ANC")
    anc2 = NamedColumn(col_name="2 ANCs")
    anc3 = NamedColumn(col_name="3 ANCs")
    anc4 = NamedColumn(col_name="4 ANCs")
    pos1 = NamedColumn(col_name="1 POS")
    pos2 = NamedColumn(col_name="2 POS")
    pos3 = NamedColumn(col_name="3 POS")

    class Meta:
        order_by = "location"