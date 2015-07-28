# -*- coding: utf-8 -*-

from collections import defaultdict
import sys

from django.db import models
from django.http import HttpRequest
from django.utils.datastructures import SortedDict
from django.utils.translation import ugettext_lazy as _

from feincms.models import create_base_model
from mptt.models import MPTTModel, MPTTModelBase

from django.template.loader import render_to_string, get_template
from django.template.context import RequestContext, Context
from django.template import TemplateDoesNotExist, Template

from .models import create_content_types
from . import settings as feincmstools_settings


__all__ = ['FeinCMSDocument', 'FeinCMSDocumentBase', 'HierarchicalFeinCMSDocument', 'Content']

# --- Models that use FeinCMS Content ------------------------------------------------------------

class FeinCMSDocumentBase(models.base.ModelBase):
    """
    Metaclass which simply calls ``register()`` for each new class.
    """

    def __new__(mcs, name, bases, attrs):
        new_class = super(FeinCMSDocumentBase, mcs).__new__(mcs, name, bases, attrs)
        new_class._register()
        return new_class

class FeinCMSDocument(create_base_model()):
    """
    A model which can have FeinCMS content chunks attached to it.

    See :py:meth:`feincmstools.base.FeinCMSDocument.content_types_by_region` for sample
    definition and a quick intro.

    See feincms.models.create_base_model for definitions of the register_* and
    create_content_type.

    1. Register regions OR templates. The former is simpler but the latter is
    more flexible, as you can define different regions for different templates.

        Page.register_regions(
            ('main', _('Main content area')),
        )

    OR

        Page.register_templates(
            {
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
            }
        )

    FeinCMSTools registers the template config in
        cls.feincms_templates = [{...}, {...}, ...]
    or the regions in
        cls.feincms_regions = [(...), (...), ...]

    Where the list contents are the *args to the functions above.

    2. Register content types (use Content model subclasses for auto-templating, but any abstract model will work).

    In FeinCMS, you do this with successive calls to
    Page.create_content_type(SomeContent, regions=None, class_name=None, **kwargs)

    FeinCMSTools steps through the regions, and registers the content types in
    cls.content_types_by_region(region). Define content_types_by_region in subclasses.
    """

    # PUBLIC
    feincms_templates = None
    feincms_regions = None

    class Meta:
        abstract = True

    @classmethod
    def _get_content_type_class_name(cls, content_type):
        """
        Hook to allow overriding of class_name passed to create_content_type.

        Previous default retained for backwards compatibility.
        However, this produces db_table names such as:
            <app_name>_<base_name>_<base_name><content_type_name>
        But for longer class names, this becomes problematic, e.g.:
            >>> len("experiences_articletranslation_"
            ...     "articletranslationfullwidthcenteredtextblock")
            75
        This is problematic for database backends such as MySQL, which
        imposes a 64-character limit on table names.

        There may be other reasons for wanting to change the class/table name.

        Returning None from this method will cause FeinCMS to fallback
        onto the default configuration of using simply `content_type.__name__`

        If registering the same Content type against multiple FeinCMSDocument base
        classes in the same app, unique class_name values must be provided
        for each to avoid collisions.
        """
        if feincmstools_settings.USE_LEGACY_TABLE_NAMES:
            return "%s%s" % (cls.__name__, content_type.__name__)

    @classmethod
    def content_types_by_region(cls, region):
        """
        This should return the list of content types that
        are allowed in that region, grouped by section.

        This method should be overridden for the subclasses.

        :return: The content types defined for the given region.
        Each returned list is formatted ('category', [SomeContent,  ...]), thus:

        [
            (None, (TextileContent,)),
            ('Media resources', (OneOffImageContent, ReusableImageContent, VideoContent,)),
            ('Files', (OneOffFileContent, ReusableFileContent)),
        ]

        If category is ``None``, these content types will appear first in the menu.

        :rtype:
            ``list`` of ``tuples`` →
                category_name, ``str``, ``list`` of content_types registered under the given category in the given region.

        Which results in the following menu in the admin edit form:

            Textile
            (Media resources)
                One-off image
                Reusable image
                Video
            (Files)
                One-off file
                Reusable file

        .. note:: Because ``content_types_by_region`` is called from the metaclass,
        using python ``super`` leads to crashes. Explicitly call ``ParentClass.content_types_by_region``
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
    def get_used_content_types(cls):
        """
        :return: All Content models used by the class. Useful for migrations.
        :rtype: ``set``
        """
        lxr = cls._get_content_types_by_region()

        r = set()

        for reg, categories in lxr:
            for category, types in categories:
                r = r.union(types)
        return r

    #PRIVATE

    __metaclass__ = FeinCMSDocumentBase

    @classmethod
    def _get_content_types_by_region(cls):
        """
        :return: All content_types grouped by category, then into regions.
        :rtype: ``list`` of ``tuple``s
        """
        return [(r.key, cls.content_types_by_region(r.key)) for r in cls._feincms_all_regions]


    @classmethod
    def _register(cls):
        """
        Create the tables for the attached content_types.
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
        return create_content_types(cls, cls.content_types_by_region)

    def search_text(self):
        request = HttpRequest()
        template = Template('''{% load feincms_tags %}
            {% filter striptags %}
            {% feincms_render_region object "main" request %}
            {% endfilter %}
            ''')
        context = RequestContext(request)
        context['object'] = self
        #import pdb;pdb.set_trace()
        return template.render(context)

class HierarchicalFeinCMSDocumentBase(FeinCMSDocumentBase, MPTTModelBase):
    pass

class HierarchicalFeinCMSDocument(FeinCMSDocument, MPTTModel):
    """
   FeinCMSDocument arranged hierarchically via MPTT.

    This defines and handles the 'parent' field in a similar way to feincms.Page
    """

    __metaclass__ = HierarchicalFeinCMSDocumentBase

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

class Content(models.Model):
    """
    A feincms content type that uses a template
    to render itself, in admin and front-end.

    Template locations are the first matching of:

    content_types/[content_type_defining_app]/[content_model]/[content_type_using_app]_[content_type_using_model]_[region_name].html
    content_types/[content_type_defining_app]/[content_model]/[content_type_using_model]_[region_name].html
    content_types/[content_type_defining_app]/[content_model]/[region_name].html
    content_types/[content_type_defining_app]/[content_model]/render.html

    And for admin:

    content_types/[content_type_defining_app]/[content_model]/admin_init.html

    The template searches up through the model hierarchy until it finds a
    suitable template.
    """
    class Meta:
        abstract = True

    admin_template = None # For initialisation in the admin
    render_template = None # For rendering on the front end

    def render(self, **kwargs):
        template = self.render_template or self._find_render_template_path(self.region)
        if not template:
            raise NotImplementedError(
                'No template found for rendering %s content. I tried ["%s"].' % (
                    self.__class__.__name__,
                    '", "'.join(self._render_template_paths(self.region))
                )
            )
        # Request is required, throw a KeyError if it's not there
        request = kwargs['request']
        context = kwargs.get('context', {})
        context['content'] = self
        if hasattr(self, 'extra_context') and callable(self.extra_context):
            context.update(self.extra_context(request))
        if hasattr(context, 'flatten'):
            # render_to_string expects a dictionary, not a context, this is
            # more strictly enforced in Django 1.8
            context = context.flatten()
        return render_to_string(template, context, context_instance=RequestContext(request))

    def __init__(self, *args, **kwargs):
        super(Content, self).__init__(*args, **kwargs)
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
        # Django <= 1.6 uses "module_name"; Django >= 1.7 uses "model_name"
        try:
            base_model_name = base._meta.model_name
        except AttributeError:
            base_model_name = base._meta.module_name
        try:
            klass_model_name = klass._meta.model_name
        except AttributeError:
            klass_model_name = klass._meta.module_name
        return {
            'content_type_defining_app': base._meta.app_label,
            'content_model_name': base_model_name,
            'content_type_using_app': klass._meta.app_label,
            'content_type_using_model': klass_model_name,
            'content_type_using_region': region,
        }

    @staticmethod
    def _bases_that_are_content_types(klass):
        """
        Returns the bases of klass that are subclasses of Content
        (not Content itself). Called recursively so as to approximate python MRO.
        """
        for base in klass.__bases__:
            if issubclass(base, Content) and base != Content:
                yield base

        for base in klass.__bases__:
            if issubclass(base, Content) and base != Content:
                for x in Content._bases_that_are_content_types(base):
                    yield x

    def _admin_template_paths(self):
        pt= "content_types/%(content_type_defining_app)s/%(content_model_name)s/admin_init.html"
        klass = type(self) #the concrete model
        for base in Content._bases_that_are_content_types(klass):
            path = pt % Content._template_params(klass, base)
            yield path

    def _find_admin_template_path(self):
        for p in self._admin_template_paths():
            if Content._detect_template(p):
                return p

    def _render_template_paths(self, region):
        """
        Return
        content_types/[content_type_defining_app]/[content_model]/[content_type_using_app]_[content_type_using_model]_[region_name].html
        content_types/[content_type_defining_app]/[content_model]/[content_type_using_model]_[region_name].html
        content_types/[content_type_defining_app]/[content_model]/[region_name].html
        content_types/[content_type_defining_app]/[content_model]/render.html

        And iterate up through content_model bases.
        """

        pt1= "content_types/%(content_type_defining_app)s/%(content_model_name)s/%(content_type_using_app)s_%(content_type_using_model)s_%(content_type_using_region)s.html"
        pt2= "content_types/%(content_type_defining_app)s/%(content_model_name)s/%(content_type_using_model)s_%(content_type_using_region)s.html"
        pt3= "content_types/%(content_type_defining_app)s/%(content_model_name)s/%(content_type_using_region)s.html"
        pt4= "content_types/%(content_type_defining_app)s/%(content_model_name)s/render.html"

        klass = type(self) #the concrete model
        for base in Content._bases_that_are_content_types(klass):
            params = Content._template_params(klass, base, region)
            yield pt1 % params
            yield pt2 % params
            yield pt3 % params
            yield pt4 % params

    def _find_render_template_path(self, region):
        for p in self._render_template_paths(region):
            if Content._detect_template(p):
                return p

    @staticmethod
    def _detect_template(path):
        """
        Look for template in given path.
        Return path to template or None if not found.
        """
        try:
            # find_template isn't available in Django 1.8
            get_template(path)
            return path
        except TemplateDoesNotExist:
            return None

def LumpyContent(*args, **kwargs):
    from warnings import warn
    warn("Lumps are Content now: "
    "LumpyContent is deprecated; use FeinCMSDocument instead.",
    DeprecationWarning, stacklevel=2)
    return FeinCMSDocument(*args, **kwargs)

def LumpyContentBase(*args, **kwargs):
    from warnings import warn
    warn("Lumps are Content now: "
    "LumpyContentBase is deprecated; use FeinCMSDocumentBase instead.",
    DeprecationWarning, stacklevel=2)
    return FeinCMSDocumentBase(*args, **kwargs)

def HierarchicalLumpyContent(*args, **kwargs):
    from warnings import warn
    warn("Lumps are Content now: "
    "HierarchicalLumpyContent is deprecated; use HierarchicalFeinCMSDocument instead.",
    DeprecationWarning, stacklevel=2)
    return HierarchicalFeinCMSDocument(*args, **kwargs)

def Lump(*args, **kwargs):
    from warnings import warn
    warn("Lumps are Content now: "
    "Lump is deprecated; use Content instead.",
    DeprecationWarning, stacklevel=2)
    return Content(*args, **kwargs)

