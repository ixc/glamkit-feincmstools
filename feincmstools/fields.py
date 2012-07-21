from django import forms
from feincmstools.widgets import HierarchicalSlugWidget

class HierarchicalSlugField(forms.SlugField):
    def __init__(self, *args, **kwargs):
        super(HierarchicalSlugField, self).__init__(*args, **kwargs)
        self.widget = type('HierarchicalSlug%s' % self.widget.__class__.__name__,
            (HierarchicalSlugWidget, self.widget.__class__),
            {'__module__': HierarchicalSlugWidget.__module__})\
            (attrs=self.widget.attrs)
