====================
GLAMkit-feincmstools
====================

Wrapper around `FeinCMS <http://github.com/matthiask/feincms>`_ with many extra features.

Principally, feincmstools allows you to create FeinCMS content types, and register them to your Document models  more intuitively and DRYly.

GLAMkit-feincmstools is a part of the `GLAMkit framework <http://glamkit.com/>`_.

A demo app is available `here <https://github.com/ixc/feincmstools-demo>`_.

To make a FeinCMS Document:
---------------------------

1) In `models.py` Define your model as a subclass of `feincmstools.base.FeinCMSDocument` (or `feincmstools.base.HierarchicalFeinCMSDocument` for documents you want to arrange in a tree).

If you are using `HierarchicalFeinCMSDocument`, you may want to mix in `HierarchicalSlugField`, which generates a slug value based on concatenations of the slugs of the document's parents.
::

	from feincmstools.fields import HierarchicalSlugField
	from feincmstools.base import HierarchicalFeinCMSDocument
	from django.db import models

	class Article(HierarchicalFeinCMSDocument, HierarchicalSlugField):
			title = models.CharField(max_length=255)
			slug = models.SlugField('slug', max_length=255, unique=True, db_index=True)

Create an admin for the model, in `admin.py`::

	from django.contrib import admin
	from feincmstools.admin import HierarchicalFeinCMSDocumentAdmin
	from .models import Article

	class ArticleAdmin(HierarchicalFeinCMSDocumentAdmin):
			prepopulated_fields = {"slug": ("title", )}


2) Define `feincms_regions` OR `feincms_templates` as an attribute of your model. feincms_regions is a list of region name/title tuples. feincms_templates allows different regions to be used and different templates rendered depending on user selection.
::

	class Article(HierarchicalFeinCMSDocument, HierarchicalSlugField):
			...

			feincms_regions = (
					('main', 'Main'),
					('left', 'Left sidebar'),
			)

			OR

			feincms_templates = [
					{
							'key': 'base',
							'title': 'Standard template',
							'path': 'magazine/article.html',
							'regions': (
									('main', 'Main content area'),
									('related', 'Related articles', 'inherited'),
							),
					}, {
							'key': '2col',
							'title': 'Template with two columns',
							'path': 'magazine/article_2col.html',
							'regions': (
									('col1', 'Column one'),
									('col2', 'Column two'),
									('related', 'Related articles', 'inherited'),
							),
					}
			]


3) Define the classmethod `content_types_by_region(region)`. This should return a list of which content types are allowed in which region, grouped into menu sections that appear in the admin UI. To define content types, see the next section.
::

	class Article(HierarchicalFeinCMSDocument, HierarchicalSlugField):
		...

		@classmethod
		def content_types_by_region(region):
				standard_content_types = [
						(None, (Text, HorizontalRule)),
						('Media', (OEmbedContent)), #The string 'Media' is shown in the admin menu.
						('Advanced', (RawHTMLContent,)),
				]

				other_content_types = {
						'related': [
								(None, (RelatedArticle,)),
						],
						'col2': [
								(None, (Text,)),
								('Advanced', (RawHTMLContent,)),
						]
				}

				return other_content_types.get(region, standard_content_types)

5) To render the FeinCMS content in the article template, use:

	{% load feincms_tags %}
	{% feincms_render_region article "main" request %}

To make a FeinCMS Content Type:
-------------------------------

FeinCMStools also provides a `Content` abstract model that you can use for creating FeinCMS content types. If you use `feincmstools.base.Content`, it looks through hierarchy of template paths, allowing you to finely control the appearance of content types in different regions and/or apps. To create a content type:

1) In content_types.py (the name doesn't matter, but this is a good convention), define an abstract model that subclasses Content::

	from django.db import models
	from feincmstools.base import Content

	class Text(Content):
			text = models.TextField(blank=True)

			class Meta:
					abstract=True

2) Create a template to render the content at /templates/content_types/<your_app>/text/render.html. The template is provided with a context variable `content`, which is the Content model instance. You can treat it as any other Django model, e.g.::

	{{ content.text|linebreaks }}

3) Add `Text` to the content_types_by_region lists, where you want it to be available.

4) Create a schema migration for EVERY app that uses `Text` in its content_types_by_region. If you are confident there are no other schema changes in these apps, use `manage.py feincms_models_migration`, which creates automatic migrations for every feincms app.

