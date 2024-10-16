""" import modules """
import logging

from odoo import fields
from odoo.tests import common

logger = logging.getLogger(__name__)

class TestAccountMove(common.TransactionCase):
    """ TestAccountMove testing class """

    def setUp(self):
        self.company_id = self.env.ref('base.main_company')
        self.country_id = self.env.ref('base.uk')
        self.tax_group_id = self.env.ref('account.tax_group_taxes')
        self.currency_id = self.env.ref('base.GBP')

        self.postponed_vat_purchase_id = self.env['account.tax'].create({
            'amount': 8,
            'amount_type': 'percent',
            'company_id': self.company_id.id,
            'country_id': self.country_id.id,
            'name': 'Postponed Purchase Test',
            'sequence': 1,
            'tax_group_id': self.tax_group_id.id,
            'type_tax_use': 'purchase',
            'is_postponed_vat': True,
        })
        self.assertTrue(self.postponed_vat_purchase_id)

        self.partner_id = self.env['res.partner'].create({
            'name': 'Testing Partner',
            'property_account_receivable_id': self.env.ref('l10n_uk.1_1100').id,
            'property_account_payable_id': self.env.ref('l10n_uk.1_2100').id,
        })

        self.product_id = self.env['product.product'].create({
            'name': 'Sample Product',
            'detailed_type': 'consu',
            'list_price': 100.0,
        })
        self.assertTrue(self.product_id)

    def test_vendor_bill(self):
        '''
        Test functions in vendor bills transaction
        '''
        bill_journal_id = self.env['account.journal'].create({
            'name': 'Vendor Bills Journal Test',
            'code': 'BILLT',
            'company_id': self.company_id.id,
            'default_account_id': self.env.ref('l10n_uk.1_5000').id,
            'refund_sequence': True,
            'type': 'purchase',
        })

        # Test 'action_post' function that will trigger '_postponed_vat_reverse_move' function
        bill_id = self.env['account.move'].create({
            'auto_post': 'no',
            'currency_id': self.currency_id.id,
            'date': fields.Date.today(),
            'invoice_date' : fields.Date.today(),
            'journal_id': bill_journal_id.id,
            'move_type': 'in_invoice',
            'state': 'draft',
            'invoice_line_ids': [(0, 0, {
                'account_id': self.env.ref('l10n_uk.1_5000').id,
                'product_id': self.product_id.id,
                'name': self.product_id.name,
                'quantity': 1,
                'price_unit': 200,
                'tax_ids': [(6, 0, self.postponed_vat_purchase_id.ids)]
            })],
            'partner_id': self.partner_id.id,
        })
        # Checking the Bill State before validation
        self.assertEqual(bill_id.state, 'draft', msg='The bill is not in Draft state')

        bill_id.action_post()
        # Checking the Bill State after validation
        self.assertEqual(bill_id.state, 'posted', msg='The bill is not in Posted state')
        reversal_move_id = bill_id.search([('reversed_entry_id', '=', bill_id.id)], limit=1)

        self.assertIn(bill_id, reversal_move_id.reversed_entry_id)

        # Checking the Postponed VAT value to not equal the Bill value
        self.assertNotEqual(reversal_move_id.amount_total, bill_id.amount_total)
        logger.info(' ===================== VB Note for Postponed Tax Created!')
