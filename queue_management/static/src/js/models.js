odoo.define('queue_management.classes', function (require) {
'use strict';

var Class = require('web.Class');
var rpc = require('web.rpc');


var Line = Class.extend({
    init: function (values) {
        Object.assign(this, values);
    },
    update: function () {
        var self = this;
        return rpc.query({
            model: 'queue_management.head',
            method: 'read',
            args: [[this.id]],
            kwargs: {fields: ['id', 'ticket_id', 'window_id', 'service_id']}
        }).then(function (line_values) {
            Object.assign(self, line_values[0]);
            return self;
        });
    },
});


var Screen = Class.extend({
    init: function (values) {
        Object.assign(this, values);
        this.lines = [];
    },
    fetchAllLines: function () {
        var self = this;
        return rpc.query({
            model: 'queue_management.head',
            method: 'search_read',
            args: [[['ticket_state', '=', 'invited']]],
            kwargs: {fields: ['id', 'ticket_id', 'window_id', 'service_id']}
        }).then(function (line_values) {
            for (var vals of line_values) {
                self.lines.push(new Line(vals));
            }
            return self;
        });
    },
});

return {
    Line: Line,
    Screen: Screen,
};
});
