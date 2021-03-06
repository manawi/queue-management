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


class QueueManagementQueue(models.Model):
    _name = 'queue_management.queue'

    service_id = fields.Many2one('queue_management.service', 'Service')
    ticket_ids = fields.One2many('queue_management.ticket', 'queue_id', readonly=True)


class QueueManagementHead(models.Model):
    _name = 'queue_management.head'
    ticket_id = fields.Many2one('queue_management.ticket', 'Ticket', readonly=True)
    window_id = fields.Many2one('queue_management.window', string='Service window', required=True)
    service_id = fields.Many2one('queue_management.service', 'Service', related='ticket_id.service_id', readonly=True)
    ticket_state = fields.Selection(string='Ticket State', related='ticket_id.ticket_state', readonly=True, store=True)

    def _generate_order_by(self, order_spec, query):
        my_order = "CASE WHEN ticket_state = 'in_progress' THEN 0 WHEN ticket_state = 'invited' THEN 1 WHEN ticket_state = 'done' THEN 2 WHEN ticket_state = 'no-show' THEN 3 END"
        if order_spec:
            return super(QueueManagementHead, self)._generate_order_by(order_spec, query) + ", " + my_order
        return " order by " + my_order


class QueueManagementTicket(models.Model):
    _name = 'queue_management.ticket'
    name = fields.Char(string='Ticket Name', readonly=True)
    queue_id = fields.Many2one('queue_management.queue', 'Queue', required='True')
    service_id = fields.Many2one('queue_management.service', 'Service', related='queue_id.service_id')
    ticket_state = fields.Selection([
        ('waiting', 'Waiting'),
        ('in_progress', 'In Progress'),
        ('next', 'Next'),
        ('invited', 'Invited'),
        ('done', 'Done'),
        ('no-show', 'No-show')], 'Ticket State', required=True, copy=False, default='waiting', readonly=True)

    def _generate_order_by(self, order_spec, query):
        my_order = "CASE WHEN ticket_state = 'in_progress' THEN 0 WHEN ticket_state = 'invited' THEN 1 WHEN ticket_state = 'next' THEN 2 WHEN ticket_state = 'waiting' THEN 3 END"
        if order_spec:
            return super(QueueManagementTicket, self)._generate_order_by(order_spec, query) + ", " + my_order
        return " order by " + my_order

    @api.multi
    def write(self, vals):
        result = super().write(vals)
        ticket_state = vals.get('ticket_state')
        if ticket_state and (ticket_state == 'invited' or ticket_state == 'in_progress'):
            (channel, message) = ((self._cr.dbname, 'screen.ticket'), ('current_ticket', self.ids))
            self.env['bus.bus'].sendone(channel, message)
        elif ticket_state:
            (channel, message) = ((self._cr.dbname, 'screen.ticket'), ('done_ticket', self.ids))
            self.env['bus.bus'].sendone(channel, message)
        return result

    @api.model
    def is_next_exists(self, service_id):
        return self.search_count([('ticket_state', '=', 'next'), ('service_id', '=', service_id)])

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            service = self.env['queue_management.service'].browse(vals.get('service_id'))
            vals['name'] = service.sequence_id.next_by_id()
        if not self.is_next_exists(vals['service_id']):
            vals['ticket_state'] = 'next'
        if not vals.get('queue_id'):
            queue = self.env['queue_management.queue'].search([('service_id', '=', vals.get('service_id'))])
            if queue:
                vals['queue_id'] = queue.id
            else:
                new_queue = self.env['queue_management.queue'].sudo().create({'service_id': vals.get('service_id')})
                vals['queue_id'] = new_queue.id
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

    @api.multi
    def change_state_in_progress(self):
        for record in self:
            record.ticket_state = 'in_progress'
        self._refresh_ticket_list()

    @api.model
    def get_next_ticket(self, service_id):
        if self.is_next_exists(service_id):
            return None
        next_ticket = self.search([('ticket_state', '=', 'waiting'),
                                   ('service_id', '=', service_id)], limit=1, order='name')
        return next_ticket

    @api.multi
    def call_client(self):
        self.ensure_one()
        if self.search([('ticket_state', 'in', ('invited', 'in_progress'))]):
            raise UserError(_('You already have "%s" client') % self.service_id.name)
        else:
            self.ticket_state = 'invited'
            self.env['queue_management.head'].sudo().create({'ticket_id': self.id, 'window_id': self.env.user.window_id.id})
            ticket = self.get_next_ticket(self.service_id.id)
            if ticket and ticket.id != self.id:
                ticket.ticket_state = 'next'
            self._refresh_ticket_list()


class QueueManagementServiceWindow(models.Model):
    _name = 'queue_management.window'
    name = fields.Integer(required=True, string='Service window')
