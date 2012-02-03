from feincmstools.models import LumpyContent

class MyLumpyContent(LumpyContent):
    @classmethod
    def lumps(cls):
        return dict(
            main = dict(

            )
        )