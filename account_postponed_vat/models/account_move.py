""" import modules """
from datetime import date

from odoo import models, _


class AccountMove(models.Model):
    """ inherit account.move """
    _inherit = 'account.move'

    def _postponed_vat_reverse_move(self, amount):
        """
        Prepare to create the refund bill and its line
        """
        account_reversed = self.env['account.account']
        move_type = self.move_type.replace('invoice', 'refund')

        if self.move_type == 'out_invoice':
            account_reversed = self.env.ref('l10n_uk.1_2200')
        else: 
            account_reversed = self.env.ref('l10n_uk.1_2201')

        # prepare Reversed Entry for the Postponed VAT
        vals = [{
            'partner_id': self.partner_id.id,
            'ref': _('Postponed VAT of: %(move_name)s', move_name=self.name),
            'invoice_date': self.invoice_date,
            'date': date.today(),
            'invoice_date_due': self.invoice_date_due,
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'auto_post': 'no',
            'currency_id': self.currency_id.id,
            'move_type': move_type,
            'reversed_entry_id': self.id,
            'invoice_date_due': self.invoice_date_due if self.invoice_date_due else '',
            'invoice_payment_term_id': self.invoice_payment_term_id.id if self.invoice_payment_term_id else '',
            'partner_bank_id': self.partner_bank_id.id if self.partner_bank_id else '',
            'invoice_line_ids': [(0, 0 , {
                'currency_id': self.currency_id.id,
                'name': 'Postponed VAT',
                'account_id': account_reversed.id,
                'quantity': 1,
                'price_unit': amount,
                'balance': -(amount),
                'amount_currency': -(amount),
                'tax_ids': False,
            })],
        }]
        # create the Reversed Entry for the Postponed VAT
        reversed_move = self.env['account.move'].create(vals)

        reversed_move._message_log(body=_(
            'This entry has been created from %s',
            self._get_html_link()
        ))
        reversed_move.action_post()

        # Get the outstanding entries
        outstanding_credit = reversed_move.invoice_outstanding_credits_debits_widget
        for entry in outstanding_credit.get('content'):
            if entry.get('move_id') == self.id:
                reversed_move.js_assign_outstanding_line(entry.get('id'))
        return reversed_move

    def action_post(self):
        """
        Adding condition to create a new refund bill from vendor bill that have at least one product with postponed VAT
        """
        res = super(AccountMove, self).action_post()
        for move in self.filtered(lambda x: x.move_type == 'in_invoice'):
            line_with_tax = move.invoice_line_ids.filtered(lambda line: line.tax_ids)
            if line_with_tax:
                postponed_amount = 0
                for line in line_with_tax:
                    postponed_taxes = line.tax_ids.filtered(lambda tax: tax.is_postponed_vat)
                    for tax in postponed_taxes:
                        postponed_amount += (line.quantity * line.price_unit) * (tax.amount / 100)
                if postponed_amount:
                    # create new credit/bill note
                    move._postponed_vat_reverse_move(postponed_amount)
        return res

    def button_draft(self):
        """
        Set to draft and unlink for the reversed move
        """
        res = super(AccountMove, self).button_draft()

        for move in self:
            reversed_entries = self.search([('reversed_entry_id', '=', move.id)], limit=1)
            if reversed_entries:
                reversed_entries.button_draft()
                reversed_entries.unlink()
        return res
