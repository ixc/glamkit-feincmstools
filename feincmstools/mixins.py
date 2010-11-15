from django.db import models
from django.template.loader import render_to_string

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
