.. feincmstools documentation master file, created by
   sphinx-quickstart on Thu Feb  2 15:54:52 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.
   Contents:
   .. toctree::
      :maxdepth: 2

FeinCMS-tools
=============

.. note:: This guide assumes a familiarity with FeinCMS and that
 FeinCMS is already installed for the project.

FeinCMS-tools is a wrapper around FeinCMS which provides a different,
and hopefully more convenient way to register content types.

Use cases
#########

FeinCMS-tools can be useful if the project requires any of the following:

* Attaching ``content_types`` to arbitrary Django models.
* More convenient, DRY and more extendable syntax for ``content_types`` declaration.
* The ability to create custom ``content types`` with less typing: no need to override
  ``render`` method if only the custom template needs to be provided.
* Terminology which does not clash with ``django.contrib.contenttypes``.
* Easier migrations with ``django-south``.

Terminology
###########

We've found ``content types`` terminology used in FeinCMS confusing as it clashes
with ``django.contrib.contenttypes``. Hence, following terms are used:

* ``Lump`` - same as ``content type`` in the FeinCMS world.
* ``LumpyContent`` - the model to which ``Lumps`` can be attached.

Installation
############

Assuming you already have ``FeinCMS`` installed, just add ``feincmstools`` to ``INSTALLED_APPS``.
No new dependencies are introduced.

Configuration
#############

Lupms Definition
****************

By convention ``Lumps`` live in ``<app_name>/lumps.py``.
Defined lumps should inherit from :py:class:`feincmstools.models.Lump`.

.. highlight:: python

Sample lumps definition::

    from feincmstools.models import Lump

    class ReusableImageLump(Lump):

        # Note that without "related_name='+'" name clashes will occur
        # if this ``Lump`` is used in many parent models.
        image_model = models.ForeignKey("images.Image", related_name="+")

        alt_text = models.CharField(max_length=100)

        class Meta:
            # Lumps have to be abstract
            abstract = True
            verbose_name = "reusable image"

    class OneOffImageLump(Lump):
            image = models.ImageField(upload_to='uploads/images')
            alt_text = models.CharField(max_length=100)

            class Meta:
                abstract = True
                verbose_name = "one-off image"

.. autoclass:: feincmstools.models.Lump
    :members:

Lumpy content definition
************************

New lumpy contents should extend :py:class:`feincmstools.base.LumpyContent`. Like normal models,
they live inside ``models.py``.

.. autoclass:: feincmstools.base.LumpyContent
    :members:

South migration helper
**********************
For every defined ``Lump``, table needs to be created for
every ``LumpyContent`` it is attached to.

FeinCMS-tools provides the command ``lumpy_migration``::

    ./manage.py lumpy_migration

It is equivalent to running ``./manage.py schemamigration <app_name> auto`` for every app
which contains models extending ``LumpyContent``.

It can also be used to get the list of all apps which will need migrations::

    ./manage.py lumpy_migration --dry-run