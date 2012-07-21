from django.forms.widgets import Widget

class HierarchicalSlugWidget(Widget):
    def render(self, name, value, attrs=None):
        if value is not None:
            value = value.rsplit('/', 1)[-1]
        return super(HierarchicalSlugWidget, self).render(name, value, attrs)

