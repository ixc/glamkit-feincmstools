# -*- coding: utf8 -*-

from collections import defaultdict, OrderedDict
import sys

from django.db import models
from django.utils.translation import ugettext as _

from feincms.models import create_base_model
from mptt.models import MPTTModel, MPTTModelBase

from django.template.loader import render_to_string, find_template
from django.template.context import RequestContext, Context
from django.template import TemplateDoesNotExist

__all__ = ['LumpyContent', 'LumpyContentBase', 'HierarchicalLumpyContent', 'Lump']

# --- Lumpy models ------------------------------------------------------------

class LumpyContentBase(models.base.ModelBase):
    """
    Metaclass which simply calls ``register()`` for each new class.
    """

    def __new__(mcs, name, bases, attrs):
        new_class = super(LumpyContentBase, mcs).__new__(mcs, name, bases, attrs)
        new_class._register()
        return new_class

class LumpyContent(create_base_model()):
    """
    A model which can have FeinCMS content regions, aka 'Lumps' attached to it.

    See :py:meth:`feincmstools.base.LumpyContent.lumps_by_region` for sample definition and a
    quick intro.

    See feincms.models.create_base_model for definitions of the register_* and
    create_content_type.

    1. Register regions OR templates. The former is simpler but the latter is
    more flexible, as you can define different regions for different templates.

        Page.register_regions(
            ('main', _('Main content area')),
        )

    OR

        Page.register_templates({
        'key': 'base',
        'title': _('Standard template'),
        'path': 'feincms_base.html',
        'regions': (
            ('main', _('Main content area')),
            ('sidebar', _('Sidebar'), 'inherited'),
            ),
        }, {
        'key': '2col',
        'title': _('Template with two columns'),
        'path': 'feincms_2col.html',
        'regions': (
            ('col1', _('Column one')),
            ('col2', _('Column two')),
            ('sidebar', _('Sidebar'), 'inherited'),
            ),
        })

    FeinCMSTools registers the template config in
        cls.feincms_templates = [{...}, {...}, ...]
    or the regions in
        cls.feincms_regions = [(...), (...), ...]

    Where the list contents are the *args to the functions above.

    2. Register content types (aka Lumps).

    In FeinCMS, you do this with successive calls to
    Page.create_content_type(lump_model, regions=None, class_name=None, **kwargs)

    FeinCMSTools steps through the regions, and registers the content types in
    cls.lumps_by_region(region). Define lumps_by_region in subclasses.
    """

    # PUBLIC
    feincms_templates = None
    feincms_regions = None

    class Meta:
        abstract = True

    @classmethod
    def lumps_by_region(cls, region):
        """
        This should return the list of content types that
        are allowed in that region, grouped by section.

        This method should be overridden for the subclasses.

        :return: The lumps definitions for the given region.
        Each returned list is formatted ('category', [Lumps]), thus:

        [
            (None, (TextileLump,)),
            ('Media resources', (OneOffImage, ReusableImage, Video,)),
            ('Files', (OneOffFile, ReusableFile)),
        ]

        If category is ``None``, these content types will appear first in the menu.

        :rtype:
            ``list`` of ``tuples`` →
                category_name, ``str``, ``list`` of lumps registered under the given category in the given region.

        Which results in the following menu in the admin edit form:

            Textile
            (Media resources)
                One-off image
                Reusable image
                Video
            (Files)
                One-off file
                Reusable file

        .. note:: Because ``lumps_by_region`` is called from the metaclass,
        using python ``super`` leads to crashes. Explicitly call ``ParentClass.lumps_by_region``
        instead. See below for example.

        """
        return []

    def region_has_content(self, region):
        """
        Returns ``True`` if the model has a region named
        ``region`` containing some content.
        """
        if region in self.content._fetch_regions():
            return True
        return False

    @classmethod
    def get_used_lumps(cls):
        """
        :return: All lumps used by the class. Useful for migrations.
        :rtype: ``set``
        """
        lxr = cls._get_lumps_by_region()

        r = set()

        for reg, categories in lxr:
            for category, types in categories:
                r = r.union(types)
        return r

    #PRIVATE

    __metaclass__ = LumpyContentBase

    @classmethod
    def _get_lumps_by_region(cls):
        """
        :return: All lumps grouped by category, then into regions.
        :rtype: ``list`` of ``tuple``s
        """
        return [(r.key, cls.lumps_by_region(r.key)) for r in cls._feincms_all_regions]


    @classmethod
    def _register(cls):
        """
        Create the tables for the attached lumps.
        """
        if not cls._meta.abstract: # concrete subclasses only
            # register templates or regions
            cls._register_templates_or_regions()
            cls._register_content_types()

    @classmethod
    def _register_templates_or_regions(cls):
        if cls.feincms_templates:
            if (cls.feincms_regions):
                import warnings
                warnings.warn('In `%s`: `feincms_regions` is ignored as '
                    '`feincms_templates` takes precedence.'
                    % cls.__name__, RuntimeWarning
                )
            cls.register_templates(*cls.feincms_templates)
        else:
            if cls.feincms_regions:
                # auto-register FeinCMS regions
                cls.register_regions(*cls.feincms_regions)

    @classmethod
    def _register_content_types(cls):

        # retrieve a mapping of content types for each region
        types_by_regions = cls._get_lumps_by_region()

        # populate a dict of registration parameters for each type
        # e.g. type: (category, [regions])
        # registration order matters as we want to control the ordering in
        # the admin menu. Hence OrderedDict.
        types_to_register = OrderedDict()
        for region, category_types in types_by_regions:
            for category, types in category_types:
                for type in types:
                    if type not in types_to_register:
                        types_to_register[type] = (category, set())
                    types_to_register[type][1].add(region)

        for type, params in types_to_register.iteritems():
            new_content_type = cls.create_content_type(
                type,
                regions=params[1],
                class_name="%s%s" % (cls.__name__, type.__name__),
                optgroup=params[0],
            )

            # FeinCMS does not correctly fake the module appearance,
            # and shell_plus becomes subsequently confused.
            setattr(
                sys.modules[cls.__module__],
                new_content_type.__name__,
                new_content_type
            )

class HierarchicalLumpyContentBase(LumpyContentBase, MPTTModelBase):
    pass

class HierarchicalLumpyContent(LumpyContent, MPTTModel):
    """
    LumpyContent with hierarchical encoding via MPTT.

    This defines and handles the 'parent' field in a similar way to feincms.Page
    """

    __metaclass__ = HierarchicalLumpyContentBase

    parent = models.ForeignKey('self', verbose_name=_('Parent'), blank=True,
                               null=True, related_name='children')
    parent.parent_filter = True # Custom FeinCMS list_filter - see admin/filterspecs.py


    class Meta:
        abstract = True
        ordering = ['tree_id', 'lft'] # required for FeinCMS TreeEditor

    def get_path(self):
        """ Returns list of slugs from tree root to self. """
        # TODO: cache in database for efficiency?
        page_list = list(self.get_ancestors()) + [self]
        return '/'.join([page.slug for page in page_list])


#-------------------------------------------------------------------------------

class Lump(models.Model):
    """
    A feincms content type that uses a template at
        '[app_label]/lumps/[model_name]/[init/render].html'
    to render itself, in admin and front-end.

    The template searches up through the model hierarchy until it finds a
    suitable template.
    """
    class Meta:
        abstract = True

    init_template = None # For initialisation IN THE ADMIN
    render_template = None # For rendering on the front end

    def render(self, **kwargs):
        assert 'request' in kwargs
        template = getattr(self, 'render_template', getattr(self.get_content(), 'render_template', None) if hasattr(self, 'get_content') else None)
        if not template:
            raise NotImplementedError('No template found for rendering %s content. I tried %s.' % (self.__class__.__name__, ", ".join(self.__class__._template_paths('render.html'))))
        context = Context()
        if 'context' in kwargs:
            context.update(kwargs['context'])
        context['content'] = self
        if hasattr(self, 'extra_context') and callable(self.extra_context):
            context.update(self.extra_context(kwargs['request']))
        return render_to_string(template, context, context_instance=RequestContext(kwargs['request']))

    def __init__(self, *args, **kwargs):
        if not hasattr(self, '_templates_initialised'):
            parent_class = getattr(self, '_feincms_content_class', None)
            init_path = self.init_template or self.__class__._detect_template('init.html')
            if parent_class and init_path:
                if not hasattr(parent_class, 'feincms_item_editor_includes'):
                    setattr(parent_class, 'feincms_item_editor_includes', {})
                parent_class.feincms_item_editor_includes.setdefault('head', set()).add(init_path)

            if self.render_template is None:
                self.render_template = self.__class__._detect_template('render.html')
        self._templates_initialised = True
        super(Lump, self).__init__(*args, **kwargs)

    @staticmethod
    def _template_path(base, name):
        return '%(app_label)s/lumps/%(model_name)s/%(name)s' % {
            'app_label': base._meta.app_label,
            'model_name': base._meta.module_name,
            'name': name,
        }

    @classmethod
    def _template_paths(cls, name):
        """
        Look for template in app/model-specific location.

        Return path to template or None if not found.
        Search using app/model names for parent classes to allow inheritance.

        """
        _class = cls
        # traverse parent classes up to (but not including) Lump
        while(Lump not in _class.__bases__):
            # choose the correct path for multiple inheritance
            base = [
                base for base in _class.__bases__ if issubclass(base, Lump)][0]
            # (this will only take the left-most relevant path in any rare
            # cases involving diamond-relationships with Lump)
            yield Lump._template_path(base, name)
            _class = base

    @classmethod
    def _detect_template(cls, name):
        """
        Look for template in app/model-specific location.

        Return path to template or None if not found.
        Search using app/model names for parent classes to allow inheritance.

        """
        # traverse parent classes up to (but not including) Lump
        for path in cls._template_paths(name):
            try:
                find_template(path)
            except TemplateDoesNotExist:
                pass
            else:
                return path
        return None
