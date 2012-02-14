# -*- coding: utf8 -*-

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
        new_class.register()
        return new_class


class LumpyContent(Base):
    """
    A model which has ``Lumps`` attached to it.

    See :py:meth:`feincmstools.base.LumpyContent.lumps_by_region` for sample definition and a
    quick intro.
    """
    #: Available templates, overrides ``regions`` and ``lumps_by_region``.
    #: See FeinCMS documentation for ``register_templates``.
    template_specs = None # FIXME: Maybe rename to `available_templates`

    #: Auto-register default regions and all available feincmstools content types
    regions = (
        ('main', _('Main')),
    )

    @classmethod
    def register(cls):
        """
        Create the tables for the attached lumps.
        """
        # Concrete subclasses only.
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
                cls._reformat_lumps_datastructure(cls.lumps_by_region())
            )

    @classmethod
    def lumps_by_region(cls):
        """
        Defines the lumps embedded in the given class.

        Lumps which belong to the non-existing regions
        will get ignored.

        .. highlight:: python

        The ``default`` value for the returned ``defaultdict``
        will be used for the regions for which lump list wasn't
        explicitly defined.

        For example, consider the following definition::

            class MyProjectLumpyContent(LumpyContent):

                regions = (
                    ('body', 'Body'),
                    ('learn_more', 'Learn More')
                )

                @classmethod
                def lumps_by_region(cls):
                    return defaultdict(
                        lambda: dict(       # Default set of lumps
                            main = [
                                ImageLump,
                                TextLump
                            ]
                        ),
                        body = dict(        # Region name
                            main = [        # Category name, ``optgroup`` in FeinCMS
                                QuoteLump,
                                TextileTextLump
                            ]
                        ),
                        unused_region = dict(
                            main = [
                                SecretLump
                            ]
                        )
                    )

        In this example ``body`` region will get ``QuoteLump`` and ``TextileText``,
        ``learn_more`` will get ``ImageLump`` and ``TextLump``, while ``SecretLump`` will be,
        alas, unused.

        This method should be overridden for the subclasses.

        .. note:: Because ``lumps_by_region`` is called from the metaclass,
            ``super``  lead to crashes. It's safer to explicitly call ``ParentClass.lumps_by_region``
            if required. See below for example.

        .. highlight:: python

        It is convenient to define per-project ``LumpyContent`` super class
        (EG ``MyProjectLumpyContent`` in our example). Inherited ``LumpyContent``s can
        get reuse and extend ``MyProjectLumpyContent`` lump definitions::

            class LumpyPage(MyProjectLumpyContent):

                @classmethod
                def lumps_by_region(cls):
                    # Alas, using ``super`` leads to crashes.
                    lumps = MyProjectLumpyContent.lumps_by_region()
                    lumps['body']['main'] += [
                        ArtistLump,
                        ArtworkLump
                    ]
                    return lumps

        :return: The lumps definitions.

        :rtype:
            ``defaultdict``:  region name, ``str`` →
                ``dict``: category_names, ``str`` →
                    ``list`` of lumps registered under the given category in the given region.
        """
        return defaultdict(
            lambda: dict(
                main={}
            )
        )

    @classmethod
    def get_used_lumps(cls):
        """
        :return: All lumps used by the class. Useful for migrations.
        :rtype: set
        """
        return set(
            sum(
                [sum(map(list, cls.lumps_by_region()[r[0]].values()), [])
                 for r in cls.regions],
                []
            )
        )

    @classmethod
    def _register_lumps(cls, lumps):
        """
        Register ``lumps`` in IxC terminology or ``content types`` in
        FeinCMS terminology.
        """
        for category, lumps_data in lumps.items():
            for lump, regions in lumps_data.items():
                new_content_type = cls.create_content_type(
                    lump,
                    class_name="%s%s" % (cls.__name__, lump.__name__),
                    regions=regions,
                    optgroup=cls._verbosify(category),
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
        Converts the datastructure from what feincmstools expect
        to what feinCMS expects.

        It is necessary because FeinCMS and FeinCMS tools use different
        datastructures to describe the content types attached to an object.
        """
        # To get the right order, lumps must be sorted by categories in the order they came.
        # The most natural datastructure is:
        # Category -> (Lump -> List of Regions)

        lump_registry = {}

        regions = [r[0] for r in cls.regions]
        for region in regions:
            region_data = lumps_definition[region]

            for category, lumps in region_data.items():
                for lump in lumps:
                    lump_registry.setdefault(category, {}).setdefault(lump, []).append(
                        region
                    )

        return lump_registry

    @classmethod
    def _verbosify(cls, s):
        """
        Convert the category name to it's verbose version.

            >>> LumpyContent._verbosify('')
            ''

            >>> LumpyContent._verbosify('learn_more')
            'Learn more'
        """
        if not s:
            # Will catch the empty string.
            return s
        return (s[0].upper() + s[1:]).replace("_", " ")

    __metaclass__ = LumpyContentBase

    class Meta:
        abstract = True

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