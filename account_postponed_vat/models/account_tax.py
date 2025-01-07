""" import modules """
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountTax(models.Model):
    """ inherit account.tax """
    _inherit = 'account.tax'

    is_postponed_vat = fields.Boolean('Is a Postponed VAT', default=False)

    @api.onchange('is_postponed_vat')
    def _onchange_is_postponed_vat(self):
        '''
        Check the type of tax
        '''
        for rec in self:
            if rec.type_tax_use != 'purchase' and rec.is_postponed_vat:
                raise ValidationError(_('You can not use Postponed VAT on a non-purchase tax'))
