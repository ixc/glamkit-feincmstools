""" IxC extensions to FeinCMS. May perhaps be pushed back to FeinCMS core """

from django.db import models
from django.utils.translation import ugettext as _
from feincms.models import Base, Region, Template
from template_utils.templatetags.generic_markup import apply_markup
from feincmstools.forms import TextileContentAdminForm
from feincmstools.media.models import OneOffImage, ReusableImage
import mptt
import sys

#---[ FeinCMS content types ]--------------------------------------------------

class TextileContent(models.Model):
    content = models.TextField()

    class Meta:
        abstract = True
        verbose_name = _("Text Block")

    def render(self, **kwargs):
        # this should possibly be done via a call to smartembed/textile
        # methods directly; just directly replacing the templatetag for now
        return apply_markup(self.content)

    form = TextileContentAdminForm
    feincms_item_editor_form = TextileContentAdminForm
    
    feincms_item_editor_includes = {
        'head': [ 'feincmstools/textilecontent/init.html' ],
        }


def get_project_path(instance, filename):
    return "project_assets/%s/%s" % (instance.project.slug, filename)

class DownloadableContent(models.Model):
    link_text = models.CharField(max_length=255)
    downloadable = models.FileField(upload_to=get_project_path) 
    include_icon = models.BooleanField(default=True)

    def get_file_name(self):
        return (os.path.split(self.downloadable.file.name)[1])

    def get_file_extension(self):
        extension = (os.path.split(self.downloadable.file.name)[1]).split('.')[1].lower()
        if extension in ['ppt','pptx','pptm','pot','potx','potm','pps','ppsx','ppsm','key']:
            extension = 'ppt'
        elif extension in ['pdf']:
            extension = 'pdf'
        else:
            extension = 'generic'
        return extension

    class Meta:
        abstract = True
        verbose_name = "Downloadable File"
        verbose_name_plural = "Downloadable Files"

    # def render(self, **kwargs):
    #     downloadable = self.downloadable
    #     template = get_template("lumpypages/downloadable.html")
    #     c = Context({'downloadable': {'file': self.downloadable, 'link_text': self.link_text, 'include_icon': self.include_icon, 'filename': self.get_file_name(), 'file_extension': self.get_file_extension()}})
    #     return template.render(c)

    
#------------------------------------------------------------------------------
    
class LumpyMetaclass(models.base.ModelBase):
    """ Metaclass which simply calls _register() for each new class. """
    def __new__(cls, name, bases, attrs):
	new_class = super(LumpyMetaclass, cls).__new__(cls, name, bases, attrs)
        new_class._register()
        return new_class


class LumpyContent(Base):
    """ As opposed to FlatPage content -- can have FeinCMS content regions. """

    __metaclass__ = LumpyMetaclass

    class Meta:
        abstract = True
    
    # auto-registered default FeinCMS regions and content types:
    default_regions = (('main', _('Main')),)
    default_content_types = (TextileContent, ReusableImage, OneOffImage,
                             DownloadableContent)

    # undocumented trick:
    feincms_item_editor_includes = {
        'head': set(['feincmstools/item_editor_head.html' ]),
        }

    @classmethod
    def _register(cls):
        if not cls._meta.abstract: # concrete subclasses only
            # auto-register FeinCMS regions
            # cls.register_regions(cls.default_regions)
            # -- produces odd error, do manually:
            cls.template = Template('','',cls.default_regions)
            cls._feincms_all_regions = cls.template.regions
            # auto-register FeinCMS content types:
            for content_type in cls.default_content_types:
                new_content_type = cls.create_content_type(content_type)
                # make it available in the module for convenience
                name = '%s%s' % (cls.__name__, content_type.__name__)
                if hasattr(sys.modules[cls.__module__], name):
                    pass # don't overwrite anything though...
                else:
                    setattr(sys.modules[cls.__module__], name,
                            new_content_type)
                        

                
class HierarchicalLumpyContent(LumpyContent):
    """ LumpyContent with hierarchical encoding via MPTT. """

    parent = models.ForeignKey('self', verbose_name=_('Parent'), blank=True,
                               null=True, related_name='children')
    parent.parent_filter = True # Custom FeinCMS list_filter
    
    class Meta:
        abstract = True
        ordering = ['tree_id', 'lft'] # required for FeinCMS TreeEditor

    @classmethod
    def _register(cls):
        if not cls._meta.abstract: # concrete subclasses only
            # auto-register with mptt
            try:
                mptt.register(cls)
            except mptt.AlreadyRegistered:
                pass
            super(HierarchicalLumpyContent, cls)._register()
            
    def get_path(self):
        """ Returns list of slugs from tree root to self. """
        # TODO: cache in database for efficiency?
        page_list = list(self.get_ancestors()) + [self]
        return '/'.join([page.slug for page in page_list])

