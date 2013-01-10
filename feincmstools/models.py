from django.utils.datastructures import SortedDict
from . import settings as feincmstools_settings
import sys

def _get_content_type_class_name(cls, content_type):
    """
    Hook to allow overriding of class_name passed to create_content_type.

    Previous default retained for backwards compatibility.
    However, this produces db_table names such as:
        <app_name>_<base_name>_<base_name><content_type_name>
    But for longer class names, this becomes problematic, e.g.:
        >>> len("experiences_articletranslation_"
        ...     "articletranslationfullwidthcenteredtextblock")
        75
    This is problematic for database backends such as MySQL, which
    imposes a 64-character limit on table names.

    There may be other reasons for wanting to change the class/table name.

    Returning None from this method will cause FeinCMS to fallback
    onto the default configuration of using simply `content_type.__name__`

    If registering the same Content type against multiple FeinCMSDocument base
    classes in the same app, unique class_name values must be provided
    for each to avoid collisions.
    """
    if feincmstools_settings.INCLUDE_CONTENT_TYPE_BASE_NAMES:
        return "%s%s" % (cls.__name__, content_type.__name__)


def create_content_types(feincms_model, content_types_by_region_fn):


    # retrieve a mapping of content types for each region
    types_by_regions = [(r.key, content_types_by_region_fn(r.key)) for r in feincms_model._feincms_all_regions]

    # populate a dict of registration parameters for each type
    # e.g. type: (category, [regions])
    # registration order matters as we want to control the ordering in
    # the admin menu. Hence SortedDict.
    types_to_register = SortedDict()
    for region, category_types in types_by_regions:
        for category, types in category_types:
            for type in types:
                if type not in types_to_register:
                    types_to_register[type] = (category, set())
                types_to_register[type][1].add(region)

    for type, params in types_to_register.iteritems():
        new_content_type = feincms_model.create_content_type(
            type,
            regions=params[1],
            class_name= _get_content_type_class_name(feincms_model, type),
            optgroup=params[0],
        )

        # FeinCMS does not correctly fake the module appearance,
        # and shell_plus becomes subsequently confused.
        # -- but we need to be careful if using a class_name which
        # might already exist in that module, which can create some
        # very confusing bugs...

        if not hasattr(sys.modules[feincms_model.__module__],
                       new_content_type.__name__):
            setattr(
                sys.modules[feincms_model.__module__],
                new_content_type.__name__,
                new_content_type
            )

