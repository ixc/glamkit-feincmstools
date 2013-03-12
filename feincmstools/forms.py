from django.contrib import admin
from django.contrib.admin.widgets import (
    ForeignKeyRawIdWidget,
    FilteredSelectMultiple,
)
from feincms.admin.item_editor import ItemEditorForm
from warnings import warn


class FormWithAdminFeatures(ItemEditorForm):
    def __init__(self, *args, **kwargs):
        if self.raw_id_fields:
            for field_name in self.raw_id_fields:
                self.base_fields[field_name].widget = ForeignKeyRawIdWidget(
                    rel=self._meta.model._meta.get_field(field_name).rel,
                    admin_site=admin.site
                )
        if self.filter_horizontal:
            for field_name in self.filter_horizontal:
                self.base_fields[field_name].widget = FilteredSelectMultiple(
                    field_name, 0
                )

        super(FormWithAdminFeatures, self).__init__(*args, **kwargs)
        if hasattr(self, 'content_field_name') \
                and self.content_field_name in self.fields:
            self.fields.insert(
                1,
                self.content_field_name,
                self.fields.pop(self.content_field_name)
            )


class FormWithRawIDFields(FormWithAdminFeatures):
    raw_id_fields = []

    def __init__(self, *args, **kwargs):
        warning_message = (
            "FormWithRawIDFields is deprecated. "
            "Use FormWithAdminFeatures instead. "
        )
        warn(warning_message, DeprecationWarning)

        super(FormWithRawIDFields, self).__init__(*args, **kwargs)


try:
    from adminboost.preview import ImagePreviewInlineForm # Soft dependency on adminboost
    import os
    from django.core.files import File
    from django.conf import settings
    from easy_thumbnails.files import Thumbnailer

    class ImagePreviewContentForm(ImagePreviewInlineForm, ItemEditorForm):

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
