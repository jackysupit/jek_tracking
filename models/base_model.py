# -*- coding: utf-8 -*-
from odoo import models

parent_method = models.AbstractModel._valid_field_parameter  # Get the parent class method by name

def _valid_field_parameter(self, field, name):
    custom_attributes = {'track_state_field', 'track_state'}  # Use a set instead of list
    return name in custom_attributes or parent_method(self, field, name)

models.AbstractModel._valid_field_parameter = _valid_field_parameter