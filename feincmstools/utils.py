from operator import add
from django.db.models import FileField
from django.db.models.signals import post_delete

def _get_subclasses(klass):
    return (klass,) + reduce(add, map(_get_subclasses, klass.__subclasses__()), ())

def get_subclasses(model, include_abstract=False):
    """
    Returns a list of unique models that inherit from the specified model. If
    include_abstract is True, abstract inheriting models will also be returned.
    """
    return list(set([klass for klass in _get_subclasses(model) \
        if hasattr(klass, '_meta') and (include_abstract or not klass._meta.abstract)]))


def _delete_files(sender, instance=None, **kwargs):
    if instance:
        for file_field in [field.name
                for field in instance._meta.fields
                if isinstance(field, FileField)
                and getattr(instance, field.name)]:
            print file_field, getattr(instance, file_field).path
            getattr(instance, file_field).delete(save=False)

def delete_files_on_delete(model):
    """
    A convenience function to delete any files referred to by File/Image fields
    in a model when an instance or subclass of that model is deleted.
    
    If invoking this for extensively inherited models, this should be placed
    somehwere that executed after all models have been initialised, such as
    urls.py.
    
    This function is only useful in Django 1.2.5 and later. Previous versions
    have this behaviour built-in.
    """
    for klass in get_subclasses(model):
        if any(isinstance(field, FileField) for field in klass._meta.fields):
            post_delete.connect(_delete_files, sender=klass)
