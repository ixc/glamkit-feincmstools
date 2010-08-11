""" IxC extensions to FeinCMS. May perhaps be pushed back to FeinCMS core """
import os

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext as _
from easy_thumbnails.files import get_thumbnailer

from base import *
from forms import TextileContentAdminForm, ImageForm
from django.template.loader import render_to_string

__all__ = ['LumpyContent', 'HierarchicalLumpyContent', 'Reusable', 'OneOff', 'TextContent', 'DownloadableContent', 'ImageContent', 'AudioContent', 'VideoContent']

class Reusable(object):
	__metaclass__ = ReusableBase
	
	class Meta:
		abstract = True

class OneOff(object):
	__metaclass__ = OneOffBase
	
	class Meta:
		abstract = True

MAX_ALT_TEXT_LENGTH = 1024

UPLOAD_PATH = getattr(settings, 'UPLOAD_PATH', 'uploads/')
TEXT_FORMATTER = getattr(settings, 'TEXT_FORMATTER', lambda self, content: content)

class TextContent(models.Model):
	content = models.TextField()

	formatter = TEXT_FORMATTER
	content_field_name = 'text_block'
	
	class Meta:
		abstract = True
		verbose_name = _("Text Block")

	def render(self, **kwargs):
		return self.formatter(self.content)

	form = TextileContentAdminForm
	feincms_item_editor_form = TextileContentAdminForm
	
	feincms_item_editor_includes = {
		'head': [ 'feincmstools/textilecontent/init.html' ],
		}

class AbstractFile(models.Model):
	title = models.CharField(max_length=255, blank=True, help_text=_('The filename will be used if not given.'))
	
	with_extension = False
	
	class Meta:
		abstract = True
	
	def __unicode__(self):
		return self.get_title()
	
	def get_title(self):
		if self.title:
			return self.title
		if hasattr(self, file):
			return self.file.name if self.with_extension else os.path.splitext(self.file.name)[1]
		return None
	
class DownloadableContent(AbstractFile):
	file = models.FileField(upload_to=UPLOAD_PATH+'file/%Y/%m/%d/')
	
	content_field_name = 'file'
	with_extension = True
	
	class Meta:
		abstract = True
		verbose_name = "Downloadable File"
		verbose_name_plural = "Downloadable Files"

	def render(self, **kwargs):
		return render_to_string('feincmstools/content/file.html', dict(file=self))

# --- Media models ------------------------------------------------------------

class ImageContent(AbstractFile):
	file = models.ImageField(upload_to=UPLOAD_PATH+'images/%Y/%m/%d/',
							 height_field='file_height', width_field='file_width',
							 max_length=255)
	file_height = models.PositiveIntegerField(editable=False)
	file_width = models.PositiveIntegerField(editable=False)
	alt_text = models.CharField('Alternate text', blank=True,
								max_length=MAX_ALT_TEXT_LENGTH,
								help_text= 'Description of the image content')
#	attribution = models.CharField(max_length=255, blank=True)
	
	form_base = ImageForm
	content_field_name = 'image'

	class Meta:
		abstract = True
	
	def render(self, **kwargs):
		return render_to_string('feincmstools/content/image.html', dict(image=self))
	
	def get_thumbnail(self, **kwargs):
		options = dict(size=(100, 100), crop=True)
		options.update(kwargs)
		return get_thumbnailer(self.file).get_thumbnail(options)

class VideoContent(AbstractFile):
	file = models.FileField(upload_to=UPLOAD_PATH+'video/%Y/%m/%d/', max_length=255)
	image = models.ImageField(upload_to=UPLOAD_PATH+'video/%Y/%m/%d/still_image/', max_length=255, blank=True)
	
	content_field_name = 'video'
	
	class Meta:
		abstract = True

class AudioContent(models.Model):
	file = models.FileField(upload_to=UPLOAD_PATH+'audio/%Y/%m/%d/', max_length=255)
	
	content_field_name = 'audio'
	
	class Meta:
		abstract = True
