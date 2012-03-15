from django.contrib import admin
from django.conf import settings
from django.utils.translation import ugettext as _

from feincms.admin.item_editor import ItemEditor
from feincms.admin.tree_editor import TreeEditor

class LumpyContentAdmin(ItemEditor):
    
    def get_template_list(self):
        opts = self.model._meta
        return [
            'admin/%s/%s/item_editor.html' % (
                opts.app_label, opts.object_name.lower()),
            'admin/%s/item_editor.html' % opts.app_label
            ] + super(LumpyContentAdmin, self).get_template_list()
    
class HierarchicalLumpyContentAdmin(LumpyContentAdmin, TreeEditor):
    raw_id_fields = ('parent',)

    def _actions_column(self, content):
        actions = super(HierarchicalLumpyContentAdmin, self)._actions_column(
            content)
        actions.insert(0,
                       u'<a href="add/?parent=%s" title="%s">' \
                       u'<img src="%simg/icon_addlink.gif" alt="%s"></a>' % (
                           content.pk,
                           _('Add child content'),
                           settings.ADMIN_MEDIA_PREFIX,
                           _('Add child content'))

        )
        if hasattr(content, 'get_absolute_url'):
            actions.insert(0,
                           u'<a href="%s" title="%s">' \
                           u'<img src="%simg/selector-search.gif" alt="%s" /></a>' % (
                               content.get_absolute_url(),
                               _('View on site'),
                               settings.ADMIN_MEDIA_PREFIX,
                               _('View on site'))
            )
        return actions

ADMIN_THUMBNAIL_SIZE = (100, 100)

class ImageAdmin(admin.ModelAdmin):
    list_display = ('admin_thumbnail', 'name',)
    search_fields = ('name',)
    
    def admin_thumbnail(self, image):
        return '<img src="%s" />' % (
            image.get_thumbnail(size=ADMIN_THUMBNAIL_SIZE).url)
    admin_thumbnail.allow_tags = True
    admin_thumbnail.short_description = 'Thumbnail'
