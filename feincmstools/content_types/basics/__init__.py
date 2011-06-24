from ...models import Lump, AbstractText, AbstractGenericFile, AbstractImage

class BasicText(AbstractText, Lump):
    class Meta:
        abstract = True
        verbose_name = "Text"

class BasicImage(AbstractImage, Lump):
    class Meta:
        abstract = True
        verbose_name = "Image"

        
class BasicFile(AbstractGenericFile, Lump):
    class Meta:
        abstract = True
        verbose_name = "File"
           