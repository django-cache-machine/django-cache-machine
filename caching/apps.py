from importlib import import_module

from django.apps import AppConfig, apps
from django.db.models.manager import Manager

from .base import CachingManager, CachingMixin
from .config import settings


class CacheMachineConfig(AppConfig):
    name = 'caching'
    verbose_name = 'Cache Machine'

    def ready(self):
        for model_path, model_options in settings.CACHE_MACHINE_MODELS.items():
            model_parts = model_path.split('.')

            # We use negative indexing so we can support contrib apps out of
            # the box.
            #
            # Example:
            #
            #   'django.contrib.contenttypes.models.ContentType'
            #
            #   app_name: contenttypes
            #   model_name: ContentType
            #
            app_name = model_parts[-3]
            model_name = model_parts[-1]

            # Support auto-generated through models for ManyToManyFields
            #
            # Example:
            #
            #   `models.py`:
            #
            #   class OtherThing(models.Model):
            #       ...
            #
            #
            #   class Thing(models.Model):
            #       ...
            #       other_things = models.ManyToManyField(OtherThing)
            #
            #
            #   `settings.py`:
            #
            #   'testapp.models.TestThing.other_things.through'
            #
            #   app_name: testapp
            #   model_name: Thing_other_things
            #
            if model_name == 'through':
                _app, _, _model, _field = model_parts[-5:-1]
                _Model = apps.get_model(_app, _model)

                field = getattr(_Model, _field)

                app_name = field.through.__module__.split('.')[-2]
                model_name = field.through.__name__
                Model = apps.get_model(app_name, model_name)

                # Use CachingManager for automatically generated through models
                #
                # The related_manager_cls function in
                # django/db/models/fields/related_descriptors.py
                # uses model._default_manager.__class__, so we set that to an
                # *instance* of CachingManager here
                #
                field.through._default_manager = CachingManager()
            else:
                # Grab the model
                Model = getattr(import_module('{}.models'.format(app_name)), model_name)

            # Add CachingMixin to the model's bases
            if CachingMixin not in Model.__bases__:
                Model.__bases__ = (CachingMixin,) + Model.__bases__

            # Support arbitrarily-named managers
            manager_name = model_options.get('manager_name', 'objects')

            # model_manager is the *instance* of the manager
            model_manager = getattr(Model, manager_name)

            # ModelManager is the manager *class*
            ModelManager = model_manager.__class__

            # We have to specially handle boring managers; luckily, this is much
            # more straightforward
            if ModelManager == Manager:
                model_manager.__class__ = CachingManager

            elif not any(issubclass(Base, CachingManager) for Base in ModelManager.__bases__):
                # Dynamically create a new type of manager with a CachingManager
                # mixin and swap the model's manager's *type* out for it
                new_bases = (CachingManager,) + ModelManager.__bases__

                new_manager_type_name = 'Caching{}'.format(ModelManager.__name__)

                NewManagerType = type(new_manager_type_name, new_bases, {})

                model_manager.__class__ = NewManagerType
