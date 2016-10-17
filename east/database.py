"""
    east.db
    =======
    EastModel class definition - extension of Peewee Model

    :copyright: (c) 2016 by Zvonimir Jurelinac
    :license: MIT
"""
import inspect

from peewee import *

from .exceptions import *
from .helpers import serialize, to_jsontype


class EastModel(Model):
    """
    East extension of Peewee model

    Extends basic Peewee model by replacing builtin Peewee exceptions with
    those subclassed from BaseAPIException to allow easier error handling in
    REST APIs.

    Also, provides a `to_jsondict` method for direct model object
    serialization to JSON for returning responses from the API.

    And finally, it supplies a `document_response` method for describing model
    instance's JSON representation defined using `__serialization__` class
    variable - return fields and their JSON datatypes. Aside from fields, it
    can also include methods, in which case it describes their return type.
    """

    _TYPE_MAP = {IntegerField: 'integer', BigIntegerField: 'Bigint',
                 PrimaryKeyField: 'integer', ForeignKeyField: 'integer',
                 FloatField: 'float', DoubleField: 'double',
                 DecimalField: 'double', CharField: 'string',
                 TextField: 'string', DateTimeField: 'Datetime',
                 DateField: 'Date', TimeField: 'Time',
                 TimestampField: 'Timestamp', BooleanField: 'bool'}

    @classmethod
    def create(cls, **attributes):
        """
        Create a new instance of model and insert the data into the database

        Extends Peewee's builtin `create` method with BaseAPIExceptions.
        """
        try:
            super().create(**attributes)
        except IntegrityError as e:
            if 'UNIQUE' in str(e):
                raise ValueNotUniqueError('Cannot create `%s`, value already in use [%s].'
                                          % (cls.__name__, e))
            else:
                raise IntegrityViolationError('Database integrity violated [%s].' % e)
        except OperationalError as e:
            raise DatabaseError('Database operational error [%s].' % e)

    @classmethod
    def replace_exceptions(cls, call, *args, **kwargs):
        """
        Replace Peewee exceptions with BaseAPIExceptions

        Replace builtin Peewee exceptions raised by calling `call` with
        those inheriting from BaseAPIException to allow for easier handling.
        """
        try:
            call(*args, **kwargs)
        except IntegrityError as e:
            if 'UNIQUE' in str(e):
                raise ValueNotUniqueError('Cannot create `%s`, value already in use [%s].'
                                          % (cls.__name__, e))
            else:
                raise IntegrityViolationError('Database integrity violated [%s].' % e)
        except OperationalError as e:
            raise DatabaseError('Database operational error [%s].' % e)

    def to_jsondict(self, view=''):
        """Serialize the model instance to a JSON-encodable dictionary"""
        if hasattr(self, '__serialization__') and view:
            return {key: serialize(getattr(self, key), view)
                    for key in self.__serialization__[view]}
        else:
            return self._data

    @classmethod
    def document_response(cls, view):
        """Return a dictionary describing model's JSON representation"""
        attrs = (cls.__serialization__[view] if view else
                 [k for k, v in cls.__dict__.items()
                  if isinstance(v, FieldDescriptor)])

        return {k: cls.to_attr_jsontype(getattr(cls, k), view) for k in attrs}

    @classmethod
    def to_attr_jsontype(cls, attr, view=None):
        """Determine the return type of the supplied field/method"""
        if type(attr) in cls._TYPE_MAP:
            return cls._TYPE_MAP[type(attr)]
        elif inspect.isfunction(attr):
            return_type = attr.__annotations__.get('return', None)
            if return_type:
                if isinstance(return_type, tuple) and len(return_type) == 2:
                    return_type, view = return_type
                basic_type = (return_type[0] if isinstance(return_type, list)
                              else return_type)
                format = (basic_type.document_response(view=view)
                          if issubclass(basic_type, EastModel)
                          else to_jsontype(basic_type))
                return [format] if isinstance(return_type, list) else format
            else:
                return 'object'
        return 'object'
