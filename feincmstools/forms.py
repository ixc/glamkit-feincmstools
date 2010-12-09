from django import forms
from django.utils.translation import ugettext as _
from django.contrib.admin.widgets import ForeignKeyRawIdWidget

from feincms.admin.editor import ItemEditorForm


class FormWithRawIDFields(ItemEditorForm):
	raw_id_fields = []

	def __init__(self, *args, **kwargs):
		if self.raw_id_fields:
			for field_name in self.raw_id_fields:
				self.base_fields[field_name].widget=ForeignKeyRawIdWidget(
					rel=self._meta.model._meta.get_field(field_name).rel)
		super(FormWithRawIDFields, self).__init__(*args, **kwargs)
		if hasattr(self, 'content_field_name') and self.content_field_name in self.fields:
			self.fields.insert(1, self.content_field_name, self.fields.pop(self.content_field_name))


try:
    from adminboost.preview import ImagePreviewInlineForm # Soft dependency on adminboost
    import os
    from django.core.files import File
    from django.conf import settings
    from easy_thumbnails.files import Thumbnailer
            
    class ImagePreviewLumpForm(ImagePreviewInlineForm, ItemEditorForm):
    
        def get_images(self, instance):
            return [instance.get_content()]
    
    class FixedImagePreviewForm(ImagePreviewInlineForm, ItemEditorForm):
        preview_instance_required = False
        preview_paths = []
        
        def get_images(self, instance):
            images = []
            for path in self.preview_paths:
                file_data = open(os.path.join(settings.MEDIA_ROOT, path), 'r')
                class MockImage(object):
                    pass
                image = MockImage()
                image.file = Thumbnailer(File(file_data), name=path)
                images.append(image)
            return images    
        
except ImportError:
    pass
