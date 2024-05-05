# -*- coding: utf-8 -*-
from odoo import models
from odoo.exceptions import MissingError, AccessError
import logging

_logger = logging.getLogger(__name__)

'''
    requirements: 
        - a field with tracking=True 


    How to use it?
    simply define your fields like this: 

        ```
            notes = fields.Char(tracking=True, track_state=['confirmed','started','ended'])
        ```
    
        track_state=['confirmed','started','ended']
        this means, your field will be tracked only when the record.state in ['confirmed','started','ended']

        that is of course assuming that you a field.state = selection()
        you can use other field name = track_state_field

        example:

        ```
            color = fields.Selection(string='color', selection=[('red', 'Red'),('green','Green'),('blue','Blue')])

            notes = fields.Char(tracking=True, track_state=['green','blue'], track_state_field='color')
        ```

        this tells odoo that we want to track the fields only when the color is green / blue. 
'''
class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def filter_tracking_fields_by_state(self, tracked_fields, initial_values_dict):
        print("############### tracked_fields: ", tracked_fields)

        new_tracking_fields = {}
        for record in self:
            for field_name, field_value in tracked_fields.items():
                track_state_field = getattr(record._fields.get(field_name), 'track_state_field') if hasattr(record._fields.get(field_name), 'track_state_field') else 'state'
                track_state = getattr(record._fields.get(field_name), 'track_state') if hasattr(record._fields.get(field_name), 'track_state') else []

                old_state = initial_values_dict[record.id].get(track_state_field)
                new_state = getattr(self, track_state_field) if hasattr(self, track_state_field) else ''

                is_tracking = False
                if not track_state:
                    is_tracking = True
                else:
                    if (old_state and old_state in track_state) or (new_state and new_state in track_state):
                        is_tracking = True
                
                if is_tracking:
                    new_tracking_fields[field_name] = field_value
        
        print("############### new_tracking_fields: ", new_tracking_fields)
        return new_tracking_fields


    def _message_track(self, fields_iter, initial_values_dict):
        """ Track updated values. Comparing the initial and current values of
        the fields given in tracked_fields, it generates a message containing
        the updated values. This message can be linked to a mail.message.subtype
        given by the ``_track_subtype`` method.

        :param iter fields_iter: iterable of field names to track
        :param dict initial_values_dict: mapping {record_id: initial_values}
        where initial_values is a dict {field_name: value, ... }
        :return: mapping {record_id: (changed_field_names, tracking_value_ids)}
            containing existing records only
        """
        if not fields_iter:
            return {}

        tracked_fields = self.fields_get(fields_iter, attributes=('string', 'type', 'selection', 'currency_field'))
        tracked_fields = self.filter_tracking_fields_by_state(tracked_fields, initial_values_dict)
        tracking = dict()
        for record in self:
            try:
                tracking[record.id] = record._mail_track(tracked_fields, initial_values_dict[record.id])
            except MissingError:
                continue

        # find content to log as body
        bodies = self.env.cr.precommit.data.pop(f'mail.tracking.message.{self._name}', {})
        for record in self:
            changes, tracking_value_ids = tracking.get(record.id, (None, None))
            if not changes:
                continue

            # find subtypes and post messages or log if no subtype found
            subtype = record._track_subtype(
                dict((col_name, initial_values_dict[record.id][col_name])
                    for col_name in changes)
            )
            if subtype:
                if not subtype.exists():
                    _logger.debug('subtype "%s" not found' % subtype.name)
                    continue
                record.message_post(
                    body=bodies.get(record.id) or '',
                    subtype_id=subtype.id,
                    tracking_value_ids=tracking_value_ids
                )
            elif tracking_value_ids:
                record._message_log(
                    body=bodies.get(record.id) or '',
                    tracking_value_ids=tracking_value_ids
                )

        return tracking


    def _valid_field_parameter(self, field, name):
        custom_attributes = ['track_state_field','track_state']
        return name in [custom_attributes] or super()._valid_field_parameter(field, name)
