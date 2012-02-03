from collections import defaultdict
import warnings

from django.db import models
from django.utils.translation import ugettext as _
import sys

from feincms.models import Base
from mptt.models import MPTTModel, MPTTModelBase

__all__ = ['LumpyContent',
           'LumpyContentBase',
           'HierarchicalLumpyContent']

# --- Lumpy models ------------------------------------------------------------

class LumpyContentBase(models.base.ModelBase):
    """
    Metaclass which simply calls ``register()`` for each new class.
    """

    def __new__(mcs, name, bases, attrs):
        new_class = super(LumpyContentBase, mcs).__new__(mcs, name, bases, attrs)
        new_class.register(name)
        return new_class


class LumpyContent(Base):
    """
    As opposed to FlatPage content -- can have FeinCMS content regions.
    """

    __metaclass__ = LumpyContentBase

    class Meta:
        abstract = True


    # Public API

    #: Available templates.
    template_specs = None # FIXME: Maybe rename to `available_templates`

    #: Auto-register default regions and all available feincmstools content types
    regions = (
        ('main', _('Main')),
        )

    @classmethod
    def register(cls, name):
        """
        Create the tables for the attached lumps.
        """
        # Concrete subclasses only
        if cls._meta.abstract: return

        if cls.template_specs:
            if cls.regions:
                warnings.warn(
                    'In `%s`: `regions` is ignored as `template_specs` '
                    'takes precedence.' % cls.__name__, RuntimeWarning
                )
            cls.register_templates(*cls.template_specs)
        else:
            cls.register_regions(*cls.regions)
            cls._register_lumps(
                cls._reformat_lumps_datastructure(cls.lumps())
            )

    @classmethod
    def lumps(cls):
        """
        Returns the list of all lumps available for the embedding.
        The actual used list of lumps is determined by the ``cls.regions`` -
        lumps under unused regions are ignored and everything else is rendered.

        :return: The lumps definitions.
        Region -> Category -> List of lumps

        :rtype: Three level dict. String -> string -> List of lumps classes.
        """
        return defaultdict(
            lambda: dict(
                main={}
            )
        )

    @classmethod
    def _register_lumps(cls, lumps):
        """
        Register ``lumps`` in IxC terminology or ``content types`` in
        FeinCMS terminology.
        """

        for lump, regions in lumps.items():
            category = regions.keys()[0]
            regions = regions.values()[0]

            new_content_type = cls.create_content_type(
                lump,
                class_name="%s%s" % (cls.__name__, lump.__name__),
                regions=regions,
                optgroup=category,
            )

            # FeinCMS does not correctly fake the module appearance,
            # and shell_plus becomes subsequently confused.
            setattr(
                sys.modules[cls.__module__],
                new_content_type.__name__,
                new_content_type
            )

    @classmethod
    def _reformat_lumps_datastructure(cls, lumps_definition):
        """
        FeinCMS and FeinCMS tools use different datastructures to
        describe the content types attached to an object.

        Convert the datastructure from what feincmstools expect
        to what feinCMS expects.

        Change the datastructure describing lumps.

        NOTE that FeinCMS imposes an additional limitation of
        that each content type can be only available under one
        category.
        """
        lump_registry = defaultdict(# Lumps
            lambda: defaultdict(# Categories.
                lambda: []                  # Regions.
            )
        )

        regions = [r[0] for r in cls.regions]
        for region in regions:
            region_data = lumps_definition[region]

            for category, lumps in region_data.items():
                for lump in lumps:
                    lump_name = lump.__name__
                    lump_registry[lump][category].append(
                        region
                    )

                    if len(lump_registry[lump].keys()) > 1:
                        raise FeinCMSToolsConfigurationError(
                            "Due to FeinCMS limitations, lump can only "
                            "be registered under one category. "
                            "Lump %s was tried to be registered under categories "
                            "%s" % (
                                lump,
                                lump_registry[lump].keys()
                                )
                        )

        return lump_registry


class HierarchicalLumpyContentBase(LumpyContentBase, MPTTModelBase):
    pass


class HierarchicalLumpyContent(LumpyContent, MPTTModel):
    """ LumpyContent with hierarchical encoding via MPTT. """

    __metaclass__ = HierarchicalLumpyContentBase

    parent = models.ForeignKey('self', verbose_name=_('Parent'), blank=True,
        null=True, related_name='children')

    #: Custom FeinCMS list_filter
    parent.parent_filter = True

    class Meta:
        abstract = True
        ordering = ['tree_id', 'lft'] # required for FeinCMS TreeEditor

    def get_path(self):
        """ Returns list of slugs from tree root to self. """
        # FIXME: cache in database for efficiency?
        page_list = list(self.get_ancestors()) + [self]
        return '/'.join([page.slug for page in page_list])


class FeinCMSToolsConfigurationError(Exception):
    pass