""" IxC extensions to FeinCMS. May perhaps be pushed back to FeinCMS core """
from django.template.base import TemplateDoesNotExist
import os

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext as _
from django.template.loader import render_to_string, get_template
from django.template.context import RequestContext, Context
from django.utils.importlib import import_module
from django.core.exceptions import ImproperlyConfigured

from base import *
import settings as feincmstools_settings

__all__ = ['LumpyContent', 'HierarchicalLumpyContent', 'Lump',
           'AbstractText', 'AbstractGenericFile', 'AbstractImage',
           'AbstractAudio', 'AbstractVideo']

UPLOAD_PATH = getattr(settings, 'UPLOAD_PATH', 'uploads/')
MAX_ALT_TEXT_LENGTH = 1024

class Lump(models.Model):
    """
    FeinCMS content type with default ``render`` method.
    """
    #: Path to the template for the initialization in the admin.
    #: :py:meth:`_find_templates` will be used if set to ``None``.
    #: If ``init_template`` is not found, it's ignored.
    init_template = None

    #: Path to the template for frontend rendering.
    #: :py:meth:`_find_templates` will be used if set to ``None``.
    render_template = None

    def __init__(self, *args, **kwargs):
        parent_class = getattr(self, '_feincms_content_class', None)

        try:
            init_template = self.init_template or self._find_template('init.html')

        except TemplateDoesNotExist:
            init_template = None

        if parent_class and init_template:
            if not hasattr(parent_class, 'feincms_item_editor_includes'):
                setattr(parent_class, 'feincms_item_editor_includes', {})
            parent_class.feincms_item_editor_includes.setdefault('head',
                set()).add(init_template)

        super(Lump, self).__init__(*args, **kwargs)

    def render(self, **kwargs):
        """
        Render ``self`` using :py:attr:`render_template`.

        If latter is not specified, the default path
        ``<app_label>/lumps/<model_name>/(init|render).html`` is tried
        for every model in the inheritance chain until the existing template is found.

        For example, consider the app ``pages``, where ``File`` and ``Image`` lumps have
        undefined :py:attr:`render_template`.

        * templates
            * pages
                * file
                    * render.html
                    * init.html
        * lumps
            * ``File``
            * ``Image(File)``

        In this case:

        * ``File`` will be rendered using ``templates/pages/file/render.html``.
        * ``Image`` has no corresponding template, hence it will use same template as ``File``
          for rendering.

        :return: Rendered content type.
        :throws: :py:class:`TemplateDoesNotExist`
        :rtype: unicode.
        """
        request = kwargs['request']
        render_template = self.render_template or self._find_template('render.html')

        context = Context(dict(
            content=self
        ))
        context.update(
            kwargs.get('context', {})
        )
        if hasattr(self, 'extra_context') and callable(self.extra_context):
            context.update(self.extra_context(request))

        return render_to_string(render_template,
                                context,
                                context_instance=RequestContext(request))
    
    @classmethod
    def _find_template(cls, name):
        """
        Choose a template for rendering out of a list of template candidates, going up along
        the inheritance chain.

        :returns: Existing template for rendering the lumpy content.
        :rtype: str
        :throws: TemplateDoesNotExist
        """
        get_template_name = lambda kls: '%(app_label)s/lumps/%(model_name)s/%(name)s' % {
            'app_label': kls._meta.app_label,
            'model_name': kls._meta.module_name,
            'name': name,
        }

        out = []
        for kls in cls.mro():
            if kls == Lump:
                break

            template_name = get_template_name(kls)
            try:

                # Check whether template exists:
                get_template(template_name)

                return template_name
            except TemplateDoesNotExist:
                continue
        raise TemplateDoesNotExist()

    class Meta:
        abstract = True

class AbstractText(models.Model):
    content = models.TextField()

    content_field_name = 'text_block'

    class Meta:
        abstract = True
        verbose_name = _("Text Block")

class AbstractTitledFile(models.Model):
    title = models.CharField(max_length=255, blank=True, help_text=_('The filename will be used if not given.'))

    with_extension = False

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.get_title()

    def get_title(self):
        if self.title:
            return self.title
        if hasattr(self, 'file'):
            return os.path.split(self.file.name)[1] if self.with_extension else os.path.splitext(self.file.name)[0]
        return None

    def save(self, *args, **kwargs):
        if not self.title:
            self.title = self.get_title()
        return super(AbstractTitledFile, self).save(*args, **kwargs)

class AbstractGenericFile(AbstractTitledFile):
    file = models.FileField(upload_to=UPLOAD_PATH+'file/%Y/%m/%d/', max_length=255)

    content_field_name = 'file'
    with_extension = True

    class Meta:
        abstract = True
        verbose_name = "File"
        verbose_name_plural = "Files"

class AbstractImage(AbstractTitledFile):
    file = models.ImageField(upload_to=UPLOAD_PATH+'images/%Y/%m/%d/',
                             height_field='file_height', width_field='file_width',
                             max_length=255)
    file_height = models.PositiveIntegerField(editable=False)
    file_width = models.PositiveIntegerField(editable=False)
    alt_text = models.CharField('Alternate text', blank=True,
                                max_length=MAX_ALT_TEXT_LENGTH,
                                help_text= 'Description of the image')

    content_field_name = 'image'
    
    try:
        from forms import ImagePreviewLumpForm # Soft dependency on adminboost
        form_base = ImagePreviewLumpForm
    except ImportError:
        pass

    class Meta:
        abstract = True

    def get_thumbnail(self, **kwargs):
        from easy_thumbnails.files import get_thumbnailer
        options = dict(size=(100, 100), crop=True)
        options.update(kwargs)
        return get_thumbnailer(self.file).get_thumbnail(options)

class AbstractVideo(AbstractTitledFile):
    file = models.FileField(upload_to=UPLOAD_PATH+'video/%Y/%m/%d/', max_length=255)
    image = models.ImageField(upload_to=UPLOAD_PATH+'video/%Y/%m/%d/still_image/', max_length=255, blank=True)

    content_field_name = 'video'

    class Meta:
        abstract = True

    def width(self):
        return 512

    def height(self):
        return 384

class AbstractAudio(AbstractTitledFile):
    file = models.FileField(upload_to=UPLOAD_PATH+'audio/%Y/%m/%d/', max_length=255)

    content_field_name = 'audio'

    class Meta:
        abstract = True


class AbstractView(Lump):
    view = models.CharField(max_length=255, blank=False,
                            choices=feincmstools_settings.CONTENT_VIEW_CHOICES)

    class Meta:
        abstract = True

    @staticmethod
    def get_view_from_path(path):
        i = path.rfind('.')
        module, view_name = path[:i], path[i+1:]
        try:
            mod = import_module(module)
        except ImportError, e:
            raise ImproperlyConfigured(
                'Error importing AbstractView module %s: "%s"' %
                (module, e))
        try:
            view = getattr(mod, view_name)
        except AttributeError:
            raise ImproperlyConfigured(
                'Module "%s" does not define a "%s" method' %
                (module, view_name))
        return view

    def render(self, **kwargs):
        try:
            view = self.get_view_from_path(self.view)
        except:
            if settings.DEBUG:
                raise
            return '<p>Content could not be found.</p>'
        try:
            response = view(kwargs.get('request'))
        except:
            if settings.DEBUG:
                raise
            return '<p>Error rendering content.</p>'
        # extract response content if it is a HttpResponse object;
        # otherwise let's hope it is a raw content string...
        content = getattr(response, 'content', response)
        return content
