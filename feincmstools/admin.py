from django.conf import settings
from django.utils.translation import ugettext as _

from feincms.admin.item_editor import ItemEditor
from feincms.admin.tree_editor import TreeEditor

class FeinCMSDocumentAdmin(ItemEditor):

    def get_template_list(self):
        opts = self.model._meta
        return [
            'admin/%s/%s/item_editor.html' % (
                opts.app_label, opts.object_name.lower()),
            'admin/%s/item_editor.html' % opts.app_label
            ] + super(FeinCMSDocumentAdmin, self).get_template_list()

class HierarchicalFeinCMSDocumentAdmin(FeinCMSDocumentAdmin, TreeEditor):
    raw_id_fields = ('parent',)

    def _actions_column(self, content):
        actions = super(HierarchicalFeinCMSDocumentAdmin, self)._actions_column(
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

def LumpyContentAdmin(*args, **kwargs):
    from warnings import warn
    warn("Lumps are Content Types now: "
    "LumpyContentAdmin is deprecated; use FeinCMSDocumentAdmin instead.",
    DeprecationWarning, stacklevel=2)
    return FeinCMSDocumentAdmin(*args, **kwargs)

def HierarchicalLumpyContentAdmin(*args, **kwargs):
    from warnings import warn
    warn("Lumps are Content Types now: "
    "HierarchicalLumpyContentAdmin is deprecated; use HierarchicalFeinCMSDocumentAdmin instead.",
    DeprecationWarning, stacklevel=2)
    return HierarchicalFeinCMSDocumentAdmin(*args, **kwargs)
