====================
GLAMkit-feincmstools
====================

Wrapper around `FeinCMS <http://github.com/matthiask/feincms>`_ with many extra features.

Principally, feincmstools allows you to create content types for `FeinCMS.Base` models more intuitively and DRYly, with `feincms.FeinCMSDocument`. You can quickly define normal or hierarchical FeinCMS-content-type-aware models.

Feincmstools also provides a `Content` abstract model that you can use for creating FeinCMS content types. If you use `feincmstools.Content`, it looks through hierarchy of template paths, allowing you to finely control the appearance of content types in different regions and/or apps.

GLAMkit-feincmstools is a part of the `GLAMkit framework <http://glamkit.com/>`_.

Dependencies:

  - Django
  - FeinCMS
