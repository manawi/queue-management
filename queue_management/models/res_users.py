# -*- encoding: utf-8 -*-
from odoo import fields
from odoo import models


class ResUsers(models.Model):
    _inherit = 'res.users'
    window_id = fields.Many2one('queue_management.window', string="Service window")
