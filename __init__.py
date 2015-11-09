#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.

from trytond.pool import Pool
from .asset import *


def register():
    Pool.register(
        Asset,
        Account,
        module='analytic_account_asset', type_='model')
    Pool.register(
        UpdateAsset,
        module='analytic_account_asset', type_='wizard')
