# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .quality import *


def register():
    Pool.register(
        Template,
        module='quality_control_trigger', type_='model')
