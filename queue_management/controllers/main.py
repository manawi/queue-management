# -*- coding: utf-8 -*-
import werkzeug.utils
from odoo import http
from odoo.addons.bus.controllers.main import BusController
from odoo.http import request


class QueueManagement(BusController):
    def _poll(self, dbname, channels, last, options):
        if options.get('screen.ticket'):
            channels = list(channels)
            screen_channel = (
                request.db,
                'screen.ticket',
                options.get('screen.ticket')
            )
            channels.append(screen_channel)
        return super(QueueManagement, self)._poll(dbname, channels, last, options)

    # @http.route('/queue/services/', auth='public')
    # def service(self, **kw):
    #     branch_id = int(kw.get('branch_id'))
    #     branch = request.env['queue.management.branch'].sudo().browse(branch_id)
    #     service_ids = request.env['queue.management.service'].sudo().search([('branch_id', '=', branch.id), ('state', '=', 'opened')])
    #     values = {
    #         'service_ids': service_ids,
    #     }
    #     return http.request.render('queue_management.queue_service', values)

    # @http.route('/queue/new_ticket/', auth='public')
    # def new_ticket(self, **kw):
    #     service_id = int(kw.get('service_id'))
    #     service = request.env['queue.management.service'].sudo().browse(service_id)
    #     service.new_ticket()
    #     return werkzeug.utils.redirect('/queue/services?branch_id={}'.format(service.branch_id.id))

    @http.route('/queue/screen/', auth='public')
    def screen(self, **kw):
        log_records = request.env['queue_management.head'].sudo().search([('ticket_state', 'in', ('invited', 'in_progress'))])
        values = {
            'log_records': log_records,
        }
        return http.request.render('queue_management.queue_screen', values)
