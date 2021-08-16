# -*- coding: utf-8 -*-

import logging
import json
import pprint
import werkzeug

from odoo import http
from odoo.http import request
from odoo.addons.payment_hesabe.models.hesabecrypt import decrypt

_logger = logging.getLogger(__name__)


class HesabeController(http.Controller):
    @http.route(['/payment/hesabe/knet/return',
                 '/payment/hesabe/knet/fail'], type='http', auth='public', csrf=False)
    def hesabe_knet_return(self, **post):
        hesabe = request.env['payment.acquirer'].search([('provider', '=', 'hesabe_knet')], limit=1).sudo()
        data = decrypt(post['data'], hesabe.secret_key, hesabe.iv_key)
        response = json.loads(data)
        _logger.info('Hesabe Knet: entering form_feedback with post data %s', pprint.pformat(response))
        if post:
            request.env['payment.transaction'].sudo().form_feedback(response, 'hesabe_knet')
        return werkzeug.utils.redirect('/payment/process')

    @http.route(['/payment/hesabe/mpgs/return',
                 '/payment/hesabe/mpgs/fail'], type='http', auth='public', csrf=False)
    def hesabe_mpgs_return(self, **post):
        hesabe = request.env['payment.acquirer'].search([('provider', '=', 'hesabe_mpgs')], limit=1).sudo()
        data = decrypt(post['data'], hesabe.secret_key, hesabe.iv_key)
        response = json.loads(data)
        _logger.info('Hesabe MPGS: entering form_feedback with post data %s', pprint.pformat(response))
        if post:
            request.env['payment.transaction'].sudo().form_feedback(response, 'hesabe_mpgs')
        return werkzeug.utils.redirect('/payment/process')

    @http.route('/payment/hesabe', type='http', auth="public",
                methods=['POST'], csrf=False)
    def hesabe_payment(self, **post):
        return werkzeug.utils.redirect(post.get('form_url'))
