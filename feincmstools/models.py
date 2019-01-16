from collections import OrderedDict as SortedDict
import sys

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
                kwargs = {}
                if isinstance(type, (list, tuple)):
                    kwargs = type[1]
                    type = type[0]
                if type not in types_to_register:
                    types_to_register[type] = (category, set(), kwargs)
                types_to_register[type][1].add(region)

    for type, params in types_to_register.iteritems():
        option_group, regions, kwargs = params

        class_name = None
        if hasattr(feincms_model, '_get_content_type_class_name'):
            class_name= feincms_model._get_content_type_class_name(type)

        new_content_type = feincms_model.create_content_type(
            type,
            regions=regions,
            class_name= class_name,
            optgroup=option_group,
            **kwargs
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

