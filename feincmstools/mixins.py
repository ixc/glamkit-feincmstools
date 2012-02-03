from django import forms
from django.db import models
from django.template.loader import render_to_string
from django.forms.widgets import TextInput, Widget
from django.core.exceptions import ObjectDoesNotExist, ImproperlyConfigured

class FriendlyNamedMixin(models.Model):
    name = models.CharField('Friendly name',
                            max_length=255,
                            blank=True,
                            help_text='Used in the admin interface only')
    
    class Meta:
        abstract = True
    
    def __unicode__(self):
        return self.name


MAX_CAPTION_LENGTH = 1024

class ImageOptionsMixin(models.Model):
    """ Convenient default options for controlling the display of an image.
        Feel free to use it as-is if it fits your needs, or use it as a reference to
        make your own.
    """
    
    IMAGE_POSITIONS = (
        ('L', 'Left'),
        ('R', 'Right'),
        ('C', 'Centre'),
        )
    EXPAND_OPTIONS = (
        ('100%', '100%'),
        ('75%', '75%'),
        ('50%', '50%'),
        ('33%', '33%'),
        ('25%', '25%'),
    )
    
    caption = models.CharField(max_length=MAX_CAPTION_LENGTH, blank=True)
    link_to_original = models.BooleanField(
        default=False, help_text='Allow users to download original file?')
    link_url = models.CharField(max_length=255, blank=True, help_text='Turns the image into a link to the given URL. Will override "Link to original" if provided')
    position = models.CharField(max_length=1, choices=IMAGE_POSITIONS, blank=True)
    wrappable = models.BooleanField(default=False, blank=True, help_text="Tick to let the following item wrap around the image")
    
    # Move these to the NFSA app or to a different mixin?
    expand = models.CharField(max_length=50, choices=EXPAND_OPTIONS, blank=True, help_text="Expands the image's width relatively to its container")
    width = models.PositiveIntegerField(blank=True, null=True, help_text="Forces the width to a certain value (in pixels)")
    height = models.PositiveIntegerField(blank=True, null=True, help_text="Forces the height to a certain value (in pixels)")
    
    render_template = 'feincmstools/lumps/imageoptions/render.html'
    
    def render(self, **kwargs):
        from easy_thumbnails.files import get_thumbnailer
        
        context = kwargs['context'] if 'context' in kwargs else Context()
        region_maximum_width = context['region_maximum_width'] if 'region_maximum_width' in context else None
        self.image_width = self.image_height = None
        w = h = None
        if self.expand:
            if region_maximum_width:
                w = float(self.expand[:-1]) * region_maximum_width / 100
                h = float(self.get_content().file_height * w / self.get_content().file_width)
        else:
            if self.width:
                w = float(self.width)
                h = float(self.get_content().file_height * w / self.get_content().file_width)
            else:
                if region_maximum_width and region_maximum_width < self.get_content().file_width:
                    w = float(region_maximum_width)
                    h = float(self.get_content().file_height * w / self.get_content().file_width)
            if self.height:
                h = float(self.height)
                if not w:
                    w = float(self.get_content().file_width * h / self.get_content().file_height)
        
        if w and h:
            self.image_width = w
            self.resized_url = get_thumbnailer(self.get_content().file).get_thumbnail(dict(size=(w, h), quality=100)).url
        else:
            self.image_width = self.get_content().file_width
            self.resized_url = self.get_content().file.url
    
        return super(ImageOptionsMixin, self).render(**kwargs)
    
    class Meta:
        abstract = True

# Hierarchical slug

class HierarchicalSlugWidget(Widget):
    def render(self, name, value, attrs=None):
        if value is not None:
            value = value.rsplit('/', 1)[-1]
        return super(HierarchicalSlugWidget, self).render(name, value, attrs)

class HierarchicalSlugField(forms.SlugField):
    def __init__(self, *args, **kwargs):
        super(HierarchicalSlugField, self).__init__(*args, **kwargs)
        self.widget = type('HierarchicalSlug%s' % self.widget.__class__.__name__,
            (HierarchicalSlugWidget, self.widget.__class__),
            {'__module__': HierarchicalSlugWidget.__module__})\
            (attrs=self.widget.attrs)
        
class HierarchicalSlug(models.Model):
    def __init__(self, *args, **kwargs):
        self._prepare_model()
        super(HierarchicalSlug, self).__init__(*args, **kwargs)
    
    def _prepare_model(self):
        if not '_the_slug' in self.__class__.__dict__:
            # Find the slug field
            slug_field_name = None
            # First, look in the MPTTMeta options for a 'slug_attr' definition
            if hasattr(self, '_mptt_meta') and hasattr(self._mptt_meta, 'slug_attr'):
                if not hasattr(self, self._mptt_meta.slug_attr):
                    raise ImproperlyConfigured(
                        'The slug field %s specified in the MPTT options is not defined on the %s model.' % \
                        (self._mptt_meta.slug_attr, self.__class__.__name__))
                slug_field_name = self._mptt_meta.slug_attr
            # Check if 'slug_attr' has been defined as a property of the model
            # itself (in case MPTT is not being used)
            elif hasattr(self, 'slug_attr'):
                if self.slug_attr not in self._meta.get_all_field_names():
                    raise ImproperlyConfigured(
                        'The slug field %s specified in the "slug_attr" property is not defined on the %s model.' % \
                        (self.slug_attr, self.__class__.__name__))
                slug_field_name = self.slug_attr
            # Oh well, let's see if there's a "slug" field
            elif 'slug' in self._meta.get_all_field_names():
                slug_field_name = 'slug'
            # Last resort: if the model has only one SlugField, use that
            elif len([field for field in self._meta.fields if isinstance(field, models.SlugField)]) == 1:
                [slug_field_name] = [field.name for field in self._meta.fields if isinstance(field, models.SlugField)]
            else:
                raise ImproperlyConfigured(
                    'Could not determine the slug field on model %s. Consider defining it using "slug_attr".' % \
                    self.__class__.__name__)
            
            # Find the parent-child relationship fields
            parent_field_name = None
            children_accessor = None
            # First, look in the MPTTMeta options for a 'parent_attr' definition;
            # this should exist for any MPTTModel.
            if hasattr(self, '_mptt_meta') \
                    and hasattr(self._mptt_meta, 'parent_attr') \
                    and hasattr(self, 'get_children'):
                # Validation of parent_attr is handled by MPTT
                parent_field_name = self._mptt_meta.parent_attr
                children_accessor = lambda self_: self_.get_children()
            # Check if 'parent_attr' has been defined as a property of the model
            # itself (in case MPTT is not being used)
            elif hasattr(self, 'parent_attr'):
                if not hasattr(self, self.parent_attr):
                    raise ImproperlyConfigured(
                        'The parent field %s specified in the "parent_attr" property is not defined on the %s model.' % \
                        (self.parent_attr, self.__class__.__name__))
                if not hasattr(self._meta.get_field_by_name(self.parent_attr), 'rel') \
                        or not self._meta.get_field_by_name(self.parent_attr).rel.to == self.__class__:
                    raise ImproperlyConfigured(
                        'The parent field %s specified in the "parent_attr" property of the %s model is not a relationship with itself.' % \
                        (self.parent_attr, self.__class__.__name__))
                parent_field_name = self.parent_attr
            # See if there's a "parent" field that relates to "self"
            elif 'parent' in self._meta.get_all_field_names() \
                    and hasattr(self._meta.get_field_by_name('parent'), 'rel') \
                    and self._meta.get_field_by_name('parent').rel.to == self.__class__:
                parent_field_name = 'parent'
            else:
                raise ImproperlyConfigured(
                    'Could not determine the parent field on model %s. Consider defining it using "parent_attr".' % \
                    self.__class__.__name__)
            
            # If the model is not an MPTTModel, work out the children accessor
            # from the parent field
            if not children_accessor:
                children_field_name = self._meta.get_field_by_name(parent_field_name).related.get_accessor_name()
                children_accessor = lambda self_: getattr(self_, children_field_name).all()
            
            # Add accessor properties and methods to the class
            self.__class__._the_slug = property(
                lambda self_: getattr(self_, slug_field_name),
                lambda self_, value: setattr(self_, slug_field_name, value))
            self.__class__._get_parent = lambda self_: getattr(self_, parent_field_name)
            self.__class__._get_children = children_accessor
            
            def formfield(self_, **kwargs):
                kwargs['form_class'] = HierarchicalSlugField
                return models.Field.formfield(self_, **kwargs)
            field = self._meta.get_field_by_name(slug_field_name)[0]
            # Transform the function into a bound method
            field.formfield = formfield.__get__(field)
    
    def truncated_slug(self):
        self._prepare_model()
        return self._the_slug.rsplit('/', 1)[-1]
    truncated_slug.short_description = 'Slug'
    
    def _generate_slug(self):
        # Recalculate the slug by taking the part of the current slug after the
        # last slash and appending it to the parent's slug
        self._prepare_model()
        self._the_slug = self.truncated_slug()
        if self._get_parent() and self._get_parent()._the_slug:
            self._the_slug = '%s/%s' % (self._get_parent()._the_slug, self._the_slug)
    
    def validate_unique(self, *args, **kwargs):
        self._generate_slug()
        super(HierarchicalSlug, self).validate_unique(*args, **kwargs)
    
    def save(self, *args, **kwargs):
        # Check if the slug has changed
        slug_changed = False
        self._generate_slug()
        try:
            # If self.pk is None, the correct exception will still be thrown
            slug_changed = self._the_slug != self.__class__.objects.get(pk=self.pk)._the_slug
        except ObjectDoesNotExist:
            pass
        # Save self so that the slug is available for its children
        super(HierarchicalSlug, self).save(*args, **kwargs)
        # Resave the children if the slug has changed
        if slug_changed:
            for child in self._get_children():
                child.save()
    
    class Meta:
        abstract = True
