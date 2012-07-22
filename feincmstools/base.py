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

__all__ = ['ChunkyContent', 'ChunkyContentBase', 'HierarchicalChunkyContent', 'Chunk']

# --- Chunky models ------------------------------------------------------------

class ChunkyContentBase(models.base.ModelBase):
    """
    Metaclass which simply calls ``register()`` for each new class.
    """

    def __new__(mcs, name, bases, attrs):
        new_class = super(ChunkyContentBase, mcs).__new__(mcs, name, bases, attrs)
        new_class._register()
        return new_class

class ChunkyContent(create_base_model()):
    """
    A model which can have FeinCMS content regions, aka ``Chunk``s attached to it.

    See :py:meth:`feincmstools.base.ChunkyContent.chunks_by_region` for sample
    definition and a quick intro.

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

    2. Register content types (aka Chunks).

    In FeinCMS, you do this with successive calls to
    Page.create_content_type(chunk_model, regions=None, class_name=None, **kwargs)

    FeinCMSTools steps through the regions, and registers the content types in
    cls.chunks_by_region(region). Define chunks_by_region in subclasses.
    """

    # PUBLIC
    feincms_templates = None
    feincms_regions = None

    class Meta:
        abstract = True

    @classmethod
    def chunks_by_region(cls, region):
        """
        This should return the list of content types that
        are allowed in that region, grouped by section.

        This method should be overridden for the subclasses.

        :return: The chunks defined for the given region.
        Each returned list is formatted ('category', [Chunks]), thus:

        [
            (None, (TextileChunk,)),
            ('Media resources', (OneOffImageChunk, ReusableImageChunk, VideoChunk,)),
            ('Files', (OneOffFileChunk, ReusableFileChunk)),
        ]

        If category is ``None``, these content types will appear first in the menu.

        :rtype:
            ``list`` of ``tuples`` →
                category_name, ``str``, ``list`` of chunks registered under the given category in the given region.

        Which results in the following menu in the admin edit form:

            Textile
            (Media resources)
                One-off image
                Reusable image
                Video
            (Files)
                One-off file
                Reusable file

        .. note:: Because ``chunks_by_region`` is called from the metaclass,
        using python ``super`` leads to crashes. Explicitly call ``ParentClass.chunks_by_region``
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
    def get_used_chunks(cls):
        """
        :return: All chunk models used by the class. Useful for migrations.
        :rtype: ``set``
        """
        lxr = cls._get_chunks_by_region()

        r = set()

        for reg, categories in lxr:
            for category, types in categories:
                r = r.union(types)
        return r

    #PRIVATE

    __metaclass__ = ChunkyContentBase

    @classmethod
    def _get_chunks_by_region(cls):
        """
        :return: All chunks grouped by category, then into regions.
        :rtype: ``list`` of ``tuple``s
        """
        return [(r.key, cls.chunks_by_region(r.key)) for r in cls._feincms_all_regions]


    @classmethod
    def _register(cls):
        """
        Create the tables for the attached chunks.
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
        types_by_regions = cls._get_chunks_by_region()

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

class HierarchicalChunkyContentBase(ChunkyContentBase, MPTTModelBase):
    pass

class HierarchicalChunkyContent(ChunkyContent, MPTTModel):
    """
    ChunkyContent arranged hierarchically via MPTT.

    This defines and handles the 'parent' field in a similar way to feincms.Page
    """

    __metaclass__ = HierarchicalChunkyContentBase

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

class Chunk(models.Model):
    """
    A feincms content type that uses a template
    to render itself, in admin and front-end.

    Template locations are the first matching of:

    chunks/[chunk_defining_app]/[chunk_model]/[chunk_using_app]_[chunk_using_model]_[region_name].html
    chunks/[chunk_defining_app]/[chunk_model]/[chunk_using_model]_[region_name].html
    chunks/[chunk_defining_app]/[chunk_model]/[region_name].html
    chunks/[chunk_defining_app]/[chunk_model]/render.html

    And for admin:

    chunks/[chunk_defining_app]/[chunk_model]/admin_init.html

    The template searches up through the model hierarchy until it finds a
    suitable template.
    """
    class Meta:
        abstract = True

    admin_template = None # For initialisation in the admin
    render_template = None # For rendering on the front end

    def render(self, **kwargs):
        assert 'request' in kwargs

        template = self.render_template or self._find_render_template_path(self.region)
        if not template:
            raise NotImplementedError('No template found for rendering %s content. I tried ["%s"].' % (self.__class__.__name__, '", "'.join(self._render_template_paths(self.region))))
        context = Context()
        if 'context' in kwargs:
            context.update(kwargs['context'])
        context['content'] = self
        if hasattr(self, 'extra_context') and callable(self.extra_context):
            context.update(self.extra_context(kwargs['request']))
        return render_to_string(template, context, context_instance=RequestContext(kwargs['request']))

    def __init__(self, *args, **kwargs):
        super(Chunk, self).__init__(*args, **kwargs)
        if not hasattr(self, '__templates_initialised'):
            parent_class = getattr(self, '_feincms_content_class', None)
            self.render_template = self.render_template or self._find_render_template_path(self.region)
            self.admin_template = self.admin_template or self._find_admin_template_path()
            if parent_class and self.admin_template:
                if not hasattr(parent_class, 'feincms_item_editor_includes'):
                    setattr(parent_class, 'feincms_item_editor_includes', {})
                parent_class.feincms_item_editor_includes.setdefault('head', set()).add(self.admin_template)

        self.__templates_initialised = True


    @staticmethod
    def _template_params(klass, base, region=None):
        return {
            'chunk_defining_app': base._meta.app_label,
            'chunk_model_name': base._meta.module_name,
            'chunk_using_app': klass._meta.app_label,
            'chunk_using_model': klass._meta.module_name,
            'chunk_using_region': region,
        }

    @staticmethod
    def _bases_that_are_chunks(klass):
        """
        Returns the bases of klass that are subclasses of Chunk
        (not Chunk itself). Called recursively so as to approximate python MRO.
        """
        for base in klass.__bases__:
            if issubclass(base, Chunk) and base != Chunk:
                yield base

        for base in klass.__bases__:
            if issubclass(base, Chunk) and base != Chunk:
                for x in Chunk._bases_that_are_chunks(base):
                    yield x

    def _admin_template_paths(self):
        pt= "chunks/%(chunk_defining_app)s/%(chunk_model_name)s/admin_init.html"
        klass = type(self) #the concrete model
        for base in Chunk._bases_that_are_chunks(klass):
            path = pt % Chunk._template_params(klass, base)
            yield path

    def _find_admin_template_path(self):
        for p in self._admin_template_paths():
            if Chunk._detect_template(p):
                return p

    def _render_template_paths(self, region):
        """
        Return
        chunks/[chunk_defining_app]/[chunk_model]/[chunk_using_app]_[chunk_using_model]_[region_name].html
        chunks/[chunk_defining_app]/[chunk_model]/[chunk_using_model]_[region_name].html
        chunks/[chunk_defining_app]/[chunk_model]/[region_name].html
        chunks/[chunk_defining_app]/[chunk_model]/render.html

        And iterate up through chunk_model bases.
        """

        pt1= "chunks/%(chunk_defining_app)s/%(chunk_model_name)s/%(chunk_using_app)s_%(chunk_using_model)s_%(chunk_using_region)s.html"
        pt2= "chunks/%(chunk_defining_app)s/%(chunk_model_name)s/%(chunk_using_model)s_%(chunk_using_region)s.html"
        pt3= "chunks/%(chunk_defining_app)s/%(chunk_model_name)s/%(chunk_using_region)s.html"
        pt4= "chunks/%(chunk_defining_app)s/%(chunk_model_name)s/render.html"

        klass = type(self) #the concrete model
        for base in Chunk._bases_that_are_chunks(klass):
            params = Chunk._template_params(klass, base, region)
            yield pt1 % params
            yield pt2 % params
            yield pt3 % params
            yield pt4 % params

    def _find_render_template_path(self, region):
        for p in self._render_template_paths(region):
            if Chunk._detect_template(p):
                return p

    @staticmethod
    def _detect_template(path):
        """
        Look for template in given path.
        Return path to template or None if not found.
        """
        try:
            find_template(path)
            return path
        except TemplateDoesNotExist:
            return None

def LumpyContent(*args, **kwargs):
    from warnings import warn
    warn("Lumps are Chunks now: "
    "LumpyContent is deprecated; use ChunkyContent instead.",
    DeprecationWarning, stacklevel=2)
    return ChunkyContent(*args, **kwargs)

def LumpyContentBase(*args, **kwargs):
    from warnings import warn
    warn("Lumps are Chunks now: "
    "LumpyContentBase is deprecated; use ChunkyContentBase instead.",
    DeprecationWarning, stacklevel=2)
    return ChunkyContentBase(*args, **kwargs)

def HierarchicalLumpyContent(*args, **kwargs):
    from warnings import warn
    warn("Lumps are Chunks now: "
    "HierarchicalLumpyContent is deprecated; use HierarchicalChunkyContent instead.",
    DeprecationWarning, stacklevel=2)
    return HierarchicalChunkyContent(*args, **kwargs)

def Lump(*args, **kwargs):
    from warnings import warn
    warn("Lumps are Chunks now: "
    "Lump is deprecated; use Chunk instead.",
    DeprecationWarning, stacklevel=2)
    return Chunk(*args, **kwargs)

