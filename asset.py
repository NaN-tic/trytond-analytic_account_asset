# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, If

from trytond.modules.analytic_account import AnalyticMixin

__all__ = ['Asset', 'UpdateAsset', 'AnalyticAccountEntry', 'Line']


class Asset(AnalyticMixin):
    __name__ = 'account.asset'

    @classmethod
    def __setup__(cls):
        super(Asset, cls).__setup__()
        cls.analytic_accounts.domain = [
            ('company', '=', If(~Eval('company'),
                    Eval('context', {}).get('company', -1),
                    Eval('company', -1))),
            ]
        cls.analytic_accounts.depends.append('company')

    def get_move(self, line):
        move = super(Asset, self).get_move(line)
        return self.set_analytic_lines(move)

    def get_closing_move(self, account):
        """
        Returns closing move values.
        """
        move = super(Asset, self).get_closing_move(account)
        return self.set_analytic_lines(move)

    def set_analytic_lines(self, move):
        """
        Sets analytics lines for an asset move
        """
        for line in move.lines:
            analytic_lines = self.get_analytic_lines(move, line)
            if analytic_lines:
                line.analytic_lines = analytic_lines
        return move

    def get_analytic_line_template(self, move, line):
        pool = Pool()
        AnalyticLine = pool.get('analytic_account.line')
        return AnalyticLine(name=self.rec_name, debit=line.debit,
            credit=line.credit, journal=self.account_journal, active=True,
            date=move.date, reference=self.reference)

    def get_analytic_lines(self, move, line):
        lines = []
        if self.analytic_accounts:
            for account in self.analytic_accounts.accounts:
                if (line.account.analytic_constraint(account)
                        == 'forbidden'):
                    continue
                analytic_line = self.get_analytic_line_template(move, line)
                analytic_line.account = account
                lines.append(analytic_line)
        return lines


class UpdateAsset:
    __name__ = 'account.asset.update'
    __metaclass__ = PoolMeta

    def get_move_lines(self, asset):
        lines = super(UpdateAsset, self).get_move_lines(asset)
        move = self.get_move(asset)
        for line in lines:
            analytic_lines = asset.get_analytic_lines(move, line)
            if analytic_lines:
                line.analytic_lines = analytic_lines
        return lines


class AnalyticAccountEntry:
    __name__ = 'analytic.account.entry'
    __metaclass__ = PoolMeta

    @classmethod
    def _get_origin(cls):
        origins = super(AnalyticAccountEntry, cls)._get_origin()
        return origins + ['account.asset']

    @fields.depends('origin')
    def on_change_with_company(self, name=None):
        pool = Pool()
        Asset = pool.get('account.asset')
        company = super(AnalyticAccountEntry, self).on_change_with_company(
            name)
        if isinstance(self.origin, Asset):
            company = self.origin.company.id
        return company

    @classmethod
    def search_company(cls, name, clause):
        domain = super(AnalyticAccountEntry, cls).search_company(name, clause),
        return ['OR',
            domain,
            (('origin.company',) + tuple(clause[1:]) + ('account.asset',)),
            ]


class Line:
    __name__ = 'analytic_account.line'
    __metaclass__ = PoolMeta

    @classmethod
    def create(cls, vlist):
        for value in vlist:
            credit = value.get('credit')
            debit = value.get('debit')
            if credit < 0 or debit < 0:
                value['debit'] = abs(credit)
                value['credit'] = abs(debit)
        return super(Line, cls).create(vlist)
