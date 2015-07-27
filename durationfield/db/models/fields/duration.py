# -*- coding: utf-8 -*-
from datetime import timedelta
from django.core import exceptions
from django.db.models.fields import Field
from django.db import models
from django.utils import six
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import smart_text

from durationfield.utils.timestring import str_to_timedelta
from durationfield.forms.fields import DurationField as FDurationField

try:
    from south.modelsinspector import add_introspection_rules
except ImportError:
    add_introspection_rules = None


class DurationField(six.with_metaclass(models.SubfieldBase, Field)):
    """
    A duration field is used
    """
    description = _("A duration of time")

    default_error_messages = {
        'invalid': _("This value must be in \"w d h min s ms us\" format."),
        'unknown_type': _("The value's type could not be converted"),
    }

    def __init__(self, precision='microseconds', *args, **kwargs):
        """
        :param precision: Defines the precision stored within the database - currently
        supported values are 'microseconds', 'seconds' and 'days'.
        """
        if precision not in ('microseconds', 'seconds', 'days'):
            raise NotImplementedError("Precision '%s' is not implemented." % self.precision)

        self.precision = precision

        super(DurationField, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(DurationField, self).deconstruct()
        if self.precision is not None:
            kwargs['precision'] = self.precision
        return name, path, args, kwargs

    def get_internal_type(self):
        return "DurationField"

    def db_type(self, connection=None):
        """
        Returns the database column data type for this field, for the provided connection.
        Django 1.1.X does not support multiple db's and therefore does not pass in the db
        connection string. Called by Django only when the framework constructs the table
        """
        return "bigint"

    def get_db_prep_value(self, value, connection=None, prepared=False):
        """
        Returns field's value prepared for interacting with the database backend.
        In our case this is an integer representing the number of microseconds
        elapsed.
        """
        if value is None:
            return None  # db NULL
        if isinstance(value, six.integer_types):
            kwargs = {self.precision: value}
            value = timedelta(**kwargs)
        value = abs(value)  # all durations are positive

        if self.precision == 'microseconds':
            return (
                value.days * 24 * 3600 * 1000000
                + value.seconds * 1000000
                + value.microseconds
            )
        elif self.precision == 'seconds':
            return (
                value.days * 24 * 3600
                + value.seconds
            )
        elif self.precision == 'days':
            return value.days
        else:
            raise NotImplementedError("Precision '%s' is not implemented." % self.precision)

    def get_db_prep_save(self, value, connection=None):
        return self.get_db_prep_value(value, connection=connection)

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return smart_text(value)

    def to_python(self, value):
        """
        Converts the input value into the timedelta Python data type, raising
        django.core.exceptions.ValidationError if the data can't be converted.
        Returns the converted value as a timedelta.
        """

        # Note that value may be coming from the database column or a serializer so we should
        # handle a timedelta, string or an integer
        if value is None:
            return value

        if isinstance(value, timedelta):
            return value

        if isinstance(value, six.integer_types):
            kwargs = {self.precision: value}
            return timedelta(**kwargs)

        # Try to parse the value
        str_val = smart_text(value)
        if isinstance(str_val, six.string_types):
            try:
                return str_to_timedelta(str_val, self.precision)
            except ValueError:
                raise exceptions.ValidationError(self.default_error_messages['invalid'])

        raise exceptions.ValidationError(self.default_error_messages['unknown_type'])

    def formfield(self, **kwargs):
        defaults = {'form_class': FDurationField}
        defaults.update(kwargs)
        return super(DurationField, self).formfield(**defaults)


if add_introspection_rules:
    # Rules for South field introspection
    duration_rules = [
        (
            (DurationField,),
            [],
            {}
        )
    ]
    add_introspection_rules(
        duration_rules, ["^durationfield\.db\.models\.fields"]
    )
