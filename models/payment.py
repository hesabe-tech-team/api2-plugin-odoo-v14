# -*- coding: utf-8 -*-

from werkzeug import urls

from odoo import api, fields, models, _
from odoo.addons.payment_hesabe.models.hesabecrypt import encrypt, decrypt
from odoo.addons.payment_hesabe.models.hesabeutil import checkout
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.tools.float_utils import float_compare

import json
import logging

_logger = logging.getLogger(__name__)


class PaymentAcquirerHesabe(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('hesabe_knet', 'Hesabe KNET'), ('hesabe_mpgs', 'Hesabe MPGS')], ondelete={'hesabe_knet': 'set default', 'hesabe_mpgs': 'set default'})
    secret_key = fields.Char(groups='base.group_user')
    merchant_code = fields.Char(groups='base.group_user')
    access_code = fields.Char(groups='base.group_user')
    iv_key = fields.Char(groups='base.group_user')
    api_version = fields.Char(groups='base.group_user', default='2.0')
    production_url = fields.Char(groups='base.group_user')
    sandbox_url = fields.Char(groups='base.group_user')

    def _get_hesabe_urls(self, environment):
        self.ensure_one()
        if environment == 'test':
            return {'hesabe_form_url': self.sandbox_url}
        elif environment == 'enabled':
            return {'hesabe_form_url': self.production_url}
        else:
            return {'hesabe_form_url': ''}

    def _get_hesabe_form_generate_values(self, values):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        payload = {
            "merchantCode": self.merchant_code,
            "currency": values['currency'] and values['currency'].name or '',
            "amount": values['amount'],
            "responseUrl": urls.url_join(base_url, '/payment/hesabe/%s/return' % ('knet' if self.provider == 'hesabe_knet' else 'mpgs')),
            "paymentType": 1 if self.provider == 'hesabe_knet' else 2,
            "version": self.api_version,
            "orderReferenceNumber": values['reference'],
            "failureUrl": urls.url_join(base_url, '/payment/hesabe/%s/fail' % ('knet' if self.provider == 'hesabe_knet' else 'mpgs')),
            # Add more variables here
            # "variable1": values['reference'],
            # Use to compare with response value amount
            "variable2": values['amount'],
            # "variable3": values['reference'],
            # "variable4": values['reference'],
            # "variable5": values['reference'],
        }

        url = self._get_hesabe_urls(self.state)['hesabe_form_url']

        encryptedText = encrypt(str(json.dumps(payload)), self.secret_key, self.iv_key)
        checkoutToken = checkout(encryptedText, url, self.access_code, 'production' if self.state == 'enabled' else 'test')
        if '"status":false' in checkoutToken:
            raise ValidationError(_("This Merchant doesn't support this payment method!"))
        else:
            result = decrypt(checkoutToken, self.secret_key, self.iv_key)
            if '"status":false' in result:
                raise ValidationError(
                    _("Service Unavailable: We are sorry the service is not available for this account. Please contact the business team for further information."))
            response = json.loads(result)
            decryptToken = response['response']['data']
            if decryptToken != '':
                url = urls.url_join(url, "/payment?data=%s" % (decryptToken))
            else:
                url = "/shop"

        vals = {
            'form_url': url
        }
        return vals

    def hesabe_knet_form_generate_values(self, values):
        self.ensure_one()
        return self._get_hesabe_form_generate_values(values)

    def hesabe_mpgs_form_generate_values(self, values):
        self.ensure_one()
        return self._get_hesabe_form_generate_values(values)

    def _get_hesabe_action_url(self):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return base_url + '/payment/hesabe'

    def hesabe_knet_get_form_action_url(self):
        return self._get_hesabe_action_url()

    def hesabe_mpgs_get_form_action_url(self):
        return self._get_hesabe_action_url()


class PaymentTransactionHesabe(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def _hesabe_form_get_tx_from_data(self, data, provider):
        reference = data.get('response').get('orderReferenceNumber')
        transaction = self.search([('reference', '=', reference)])
        if not transaction:
            error_msg = (_(
                'Hesabe %s: received data for reference %s; no order found') % (provider, reference))
            raise ValidationError(error_msg)
        elif len(transaction) > 1:
            error_msg = (_(
                'Hesabe %s: received data for reference %s; multiple orders found') % (provider, reference))
            raise ValidationError(error_msg)
        return transaction

    @api.model
    def _hesabe_knet_form_get_tx_from_data(self, data):
        return self._hesabe_form_get_tx_from_data(data, 'KNET')

    @api.model
    def _hesabe_mpgs_form_get_tx_from_data(self, data):
        return self._hesabe_form_get_tx_from_data(data, 'MPGS')

    def _hesabe_form_get_invalid_parameters(self, data):
        invalid_parameters = []
        if self.acquirer_reference and data.get('response').get(
            'orderReferenceNumber') != self.acquirer_reference:
            invalid_parameters.append(
                ('Transaction Id', data.get('response').get('orderReferenceNumber'),
                 self.acquirer_reference))
        if float_compare(float(data.get('response').get('variable2', '0.0')),
                         self.amount, 2) != 0:
            invalid_parameters.append(
                ('Amount', data.get('response').get('variable2'),
                 '%.2f' % self.amount))
        return invalid_parameters

    def _hesabe_knet_form_get_invalid_parameters(self, data):
        return self._hesabe_form_get_invalid_parameters(data)

    def _hesabe_mpgs_form_get_invalid_parameters(self, data):
        return self._hesabe_form_get_invalid_parameters(data)

    def _hesabe_form_validate(self, data):
        status = data.get('status')
        result = self.write({
            'acquirer_reference': data.get('response').get('paymentId'),
            'date': fields.Datetime.now(),
        })
        if status:
            self._set_transaction_done()
        else:
            self._set_transaction_cancel()
        return result

    def _hesabe_knet_form_validate(self, data):
        return  self._hesabe_form_validate(data)

    def _hesabe_mpgs_form_validate(self, data):
        return self._hesabe_form_validate(data)
