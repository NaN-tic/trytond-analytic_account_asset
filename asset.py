# This file is part of Tryton.  The COPYRIGHT file at the top level of this
# repository contains the full copyright notices and license terms.
from trytond.pool import Pool, PoolMeta

__all__ = ['Asset', 'UpdateAsset']
__metaclass__ = PoolMeta


class Asset:
    __name__ = 'account.asset'

    def get_move(self, line):
        move = super(Asset, self).get_move(line)
        self.set_analytic_lines(move)
        return move

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
        if line.account == self.product.account_depreciation_used:
            for account in self.product.analytic_accounts_used:
                analytic_line = self.get_analytic_line_template(move, line)
                analytic_line.account = account
                lines.append(analytic_line)
        return lines

    def get_closing_move(self, account):
        """
        Returns closing move values.
        """
        move = super(Asset, self).get_closing_move(account)
        for line in move.lines:
            analytic_lines = self.get_analytic_lines(move, line)
            if analytic_lines:
                line.analytic_lines = analytic_lines
        return move


class UpdateAsset:
    'Update Asset'
    __name__ = 'account.asset.update'

    def get_move_lines(self, asset):
        lines = super(UpdateAsset, self).get_move_lines(asset)
        move = self.get_move(asset)
        for line in lines:
            analytic_lines = asset.get_analytic_lines(move, line)
            if analytic_lines:
                line.analytic_lines = analytic_lines
        return lines
