# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import Warning as UserError
from odoo.tools.translate import _


class QueueManagementWindow(models.Model):
    _name = 'queue_management.window'
    name = fields.Char(required=True, string='Window name')
    active = fields.Boolean(default=True)


class QueueManagementService(models.Model):
    _name = 'queue_management.service'
    _order = 'priority'

    name = fields.Char(required=True, string='Description')
    active = fields.Boolean(default=True)
    sequence_id = fields.Many2one('ir.sequence', string='Letter', required=True)
    priority = fields.Integer(default=5)

    @api.multi
    def new_ticket(self):
        self.ensure_one()
        self.env['queue_management.ticket'].create({'service_id': self.id})


class QueueManagementQueueu(models.Model):
    _name = 'queue_management.queue'

    service_id = fields.Many2one('queue_management.service', 'Service')
    ticket_ids = fields.One2many('queue_management.ticket', 'queue_id', readonly=True)


class QueueManagementHead(models.Model):
    _name = 'queue_management.head'
    ticket_id = fields.Many2one('queue_management.ticket', 'Ticket', readonly=True)
    window_id = fields.Many2one('queue_management.window', string='Service window', required=True)
    service_id = fields.Many2one('queue_management.service', 'Service', related='ticket_id.service_id', readonly=True)
    ticket_state = fields.Selection(string='Ticket State', related='ticket_id.ticket_state', readonly=True)


class QueueManagementTicket(models.Model):
    _name = 'queue_management.ticket'
    name = fields.Char(string='Ticket Name', readonly=True)
    queue_id = fields.Many2one('queue_management.queue', 'Queue', required='True')
    service_id = fields.Many2one('queue_management.service', 'Service', related='queue_id.service_id', readonly=True)
    ticket_state = fields.Selection([
        ('pending', 'Pending'),
        ('previous', 'Previous'),
        ('current', 'Current'),
        ('next', 'Next'),
        ('done', 'Done'),
        ('no-show', 'No-show')], 'Ticket State', required=True, copy=False, default='pending', readonly=True)

    def _generate_order_by(self, order_spec, query):
        my_order = "CASE WHEN ticket_state = 'current' THEN 0 WHEN ticket_state = 'next' THEN 1 WHEN ticket_state = 'pending' THEN 2 END"
        if order_spec:
            return super(QueueManagementTicket, self)._generate_order_by(order_spec, query) + ", " + my_order
        return " order by " + my_order

    @api.model
    def is_next_exists(self, service_id):
        return self.search_count([('ticket_state', '=', 'next'), ('service_id', '=', service_id)])

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            service = self.env['queue_management.service'].browse(vals.get('service_id'))
            vals['name'] = service.sequence_id.next_by_id()
        if not self.is_next_exist(vals['service_id']):
            vals['ticket_state'] = 'next'
        return super(QueueManagementTicket, self).create(vals)

    @api.model
    def _refresh_ticket_list(self):
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'queue_management.ticket'
        }

    @api.multi
    def change_state_done(self):
        for record in self:
            record.ticket_state = 'done'
        self._refresh_ticket_list()

    @api.multi
    def change_state_no_show(self):
        for record in self:
            record.ticket_state = 'no-show'
        self._refresh_ticket_list()

    @api.model
    def get_next_ticket(self, service_id):
        if self.is_next_exists(service_id):
            return None
        next_ticket = self.search([('ticket_state', '=', 'pending'),
                                   ('service_id', '=', service_id)], limit=1, order='name')
        return next_ticket

    # @api.multi
    # def call_client(self):
    #     self.ensure_one()
    #     current = self.search([('ticket_state', '=', 'current'),
    #                            ('service_id', 'in', self.env.user.service_ids.mapped('id'))])
    #     if current:
    #         raise UserError(_('You already have current ticket, make it done first.'))
    #     else:
    #         self.ticket_state = 'current'
    #         self.env['queue_management.head'].sudo().create({'ticket_id': self.id, 'window_id': self.env.user.window_id.id})
    #         ticket = self.get_next_ticket(self.env.user.service_ids[0].id)
    #         if ticket and ticket.id != self.id:
    #             ticket.ticket_state = 'next'
    #         self._refresh_ticket_list()