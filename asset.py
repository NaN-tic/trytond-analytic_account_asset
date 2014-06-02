#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction

__all__ = ['Asset', 'UpdateAsset', 'Account']
__metaclass__ = PoolMeta


class AnalyticMixin:

    def analytic_accounts_available(self):
        return True

    @classmethod
    def analytic_accounts_available_create(cls, vals):
        return True

    @classmethod
    def _view_look_dom_arch(cls, tree, type, field_children=None):
        AnalyticAccount = Pool().get('analytic_account.account')
        AnalyticAccount.convert_view(tree)
        return super(AnalyticMixin, cls)._view_look_dom_arch(tree, type,
            field_children=field_children)

    @classmethod
    def fields_get(cls, fields_names=None):
        AnalyticAccount = Pool().get('analytic_account.account')

        fields = super(AnalyticMixin, cls).fields_get(fields_names)

        analytic_accounts_field = super(AnalyticMixin, cls).fields_get(
                ['analytic_accounts'])['analytic_accounts']

        fields.update(AnalyticAccount.analytic_accounts_fields_get(
                analytic_accounts_field, fields_names,
                states=cls.analytic_accounts.states,
                required_states=Eval('type') == 'record'))
        return fields

    @classmethod
    def default_get(cls, fields, with_rec_name=True, with_on_change=False):
        fields = [x for x in fields if not x.startswith('analytic_account_')]
        return super(AnalyticMixin, cls).default_get(fields,
            with_rec_name=with_rec_name, with_on_change=with_on_change)

    @classmethod
    def read(cls, ids, fields_names=None):
        if fields_names:
            fields_names2 = [x for x in fields_names
                    if not x.startswith('analytic_account_')]
        else:
            fields_names2 = fields_names

        res = super(AnalyticMixin, cls).read(ids, fields_names=fields_names2)

        if not fields_names:
            fields_names = cls._fields.keys()

        root_ids = []
        for field in fields_names:
            if field.startswith('analytic_account_') and '.' not in field:
                root_ids.append(int(field[len('analytic_account_'):]))
        if root_ids:
            id2record = {}
            for record in res:
                id2record[record['id']] = record
            records = cls.browse(ids)
            for record in records:
                for root_id in root_ids:
                    id2record[record.id]['analytic_account_'
                        + str(root_id)] = None
                if not record.analytic_accounts_available():
                    continue
                if not record.analytic_accounts:
                    continue
                for account in record.analytic_accounts.accounts:
                    if account.root.id in root_ids:
                        id2record[record.id]['analytic_account_'
                            + str(account.root.id)] = account.id
                        for field in fields_names:
                            if field.startswith('analytic_account_'
                                    + str(account.root.id) + '.'):
                                ham, field2 = field.split('.', 1)
                                id2record[record.id][field] = account[field2]
        return res

    @classmethod
    def create(cls, vlist):
        Selection = Pool().get('analytic_account.account.selection')
        vlist = [x.copy() for x in vlist]
        to_write = []
        for vals in vlist:
            selection_vals = {}
            for field in vals.keys():
                if field.startswith('analytic_account_'):
                    if vals[field]:
                        selection_vals.setdefault('accounts', [])
                        selection_vals['accounts'].append(('add',
                                [vals[field]]))
                    del vals[field]
            if vals.get('analytic_accounts'):
                to_write.extend((
                        [Selection(vals['analytic_accounts'])],
                        selection_vals
                        ))
            elif cls.analytic_accounts_available_create(vals):
                selection, = Selection.create([selection_vals])
                vals['analytic_accounts'] = selection.id
        if to_write:
            Selection.write(*to_write)
        return super(AnalyticMixin, cls).create(vlist)

    @classmethod
    def write(cls, *args):
        Selection = Pool().get('analytic_account.account.selection')
        actions = iter(args)
        args = []
        to_write = []
        for records, vals in zip(actions, actions):
            vals = vals.copy()
            selection_vals = {}
            for field in vals.keys():
                if field.startswith('analytic_account_'):
                    root_id = int(field[len('analytic_account_'):])
                    selection_vals[root_id] = vals[field]
                    del vals[field]
            if selection_vals:
                for record in records:
                    if not record.analytic_accounts_available():
                        continue
                    accounts = []
                    if not record.analytic_accounts:
                        # Create missing selection
                        with Transaction().set_user(0):
                                selection, = Selection.create([{}])
                        cls.write([record], {
                                'analytic_accounts': selection.id,
                                })
                    for account in record.analytic_accounts.accounts:
                        if account.root.id in selection_vals:
                            value = selection_vals[account.root.id]
                            if value:
                                accounts.append(value)
                        else:
                            accounts.append(account.id)
                    for account_id in selection_vals.values():
                        if account_id \
                                and account_id not in accounts:
                            accounts.append(account_id)
                    to_remove = list(
                        set((a.id for a in
                                record.analytic_accounts.accounts))
                        - set(accounts))
                    to_write.extend(([record.analytic_accounts], {
                            'accounts': [
                                ('remove', to_remove),
                                ('add', accounts),
                                ],
                            }))
            args.extend((records, vals))
        if to_write:
            Selection.write(*to_write)
        super(AnalyticMixin, cls).write(*args)

    @classmethod
    def delete(cls, records):
        Selection = Pool().get('analytic_account.account.selection')

        selection_ids = []
        for record in records:
            if record.analytic_accounts:
                selection_ids.append(record.analytic_accounts.id)

        super(AnalyticMixin, cls).delete(records)
        Selection.delete(Selection.browse(selection_ids))

    @classmethod
    def copy(cls, records, default=None):
        Selection = Pool().get('analytic_account.account.selection')

        new_records = super(AnalyticMixin, cls).copy(records, default=default)

        to_write = []
        for record in new_records:
            if record.analytic_accounts:
                selection, = Selection.copy([record.analytic_accounts])
                to_write.extend([
                        [record], {
                        'analytic_accounts': selection.id,
                        }])
        if to_write:
            cls.write(*to_write)
        return new_records


class Asset(AnalyticMixin):
    __name__ = 'account.asset'

    analytic_accounts = fields.Many2One(
        'analytic_account.account.selection', 'Analytic Accounts')

    def get_move(self, line):
        move = super(Asset, self).get_move(line)
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
        if line.account == self.product.account_depreciation_used:
            if self.analytic_accounts:
                for account in self.analytic_accounts.accounts:
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


class Account:
    __name__ = 'analytic_account.account'

    @classmethod
    def delete(cls, accounts):
        pool = Pool()
        Asset = pool.get('account.asset')
        super(Account, cls).delete(accounts)
        # Restart the cache on the fields_view_get method
        Asset._fields_view_get_cache.clear()

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        Asset = pool.get('account.asset')
        accounts = super(Account, cls).create(vlist)
        # Restart the cache on the fields_view_get method
        Asset._fields_view_get_cache.clear()
        return accounts

    @classmethod
    def write(cls, *args):
        pool = Pool()
        Asset = pool.get('account.asset')
        super(Account, cls).write(*args)
        # Restart the cache on the fields_view_get method of
        Asset._fields_view_get_cache.clear()
