import os

from django import template

from feincms.templatetags.feincms_tags import feincms_render_content

register = template.Library()

@register.filter
def is_parent_of(page1, page2):
    """
    Determines whether a given page is the parent of another page

    Example:

    {% if page|is_parent_of:feincms_page %} ... {% endif %}
    """

    if page1 is None:
        return False
    
    return (page1.tree_id == page2.tree_id and
            page1.lft < page2.lft and
            page1.rght > page2.rght)

@register.filter
def is_equal_or_parent_of(page1, page2):
    return (page1.tree_id == page2.tree_id and
            page1.lft <= page2.lft and
            page1.rght >= page2.rght)


@register.filter
def is_sibling_of(page1, page2):
    """
    Determines whether a given page is a sibling of another page

    {% if page|is_sibling_of:feincms_page %} ... {% endif %}
    """

    if page1 is None or page2 is None:
        return False
    return (page1.parent_id == page2.parent_id)

@register.filter
def get_extension(filename):
    """ Return the extension from a file name """
    return os.path.splitext(filename)[1][1:]


@register.assignment_tag(takes_context=True)
def feincms_render_content_as(context, content, request=None):
    return feincms_render_content(context, content, request)
