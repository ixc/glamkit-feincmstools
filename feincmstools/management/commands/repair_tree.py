from itertools import count
from optparse import make_option

from django.core.management.base import LabelCommand
from django.db.models.loading import get_model

from mptt.models import MPTTModel

class Parser(object):
    def __init__(self, model):
        self.tree = {}
        self.parsed = []
        self.found = []
        self.counter = count(1)
        self.model = model
        
        self.build_tree()

    def parse_item(self, item):
        if item in self.parsed:
            return self.parsed[self.parsed.index(item)].level
        if item.parent:
            if item.parent not in self.parsed:
                print 'Uh-oh, encountered a child %s with unparsed parent %s.' % (item, item.parent)
            else:
                item.parent = self.parsed[self.parsed.index(item.parent)]
            item.level = self.parse_item(item.parent) + 1
            item.tree_id = item.parent.tree_id
        else:
            item.tree_id = self.counter.next()
            item.level = 0
        if item.tree_id not in self.tree:
            self.tree[item.tree_id] = [item,item]
        else:
            self.tree[item.tree_id].insert(
                self.tree[item.tree_id].index(
                    item.parent,
                    self.tree[item.tree_id].index(item.parent) + 1),
                item)
            self.tree[item.tree_id].insert(
                self.tree[item.tree_id].index(item),
                item)
        self.parsed.append(item)
        return item.level
    
    def build_tree(self):
        for item in self.model.objects.order_by('lft', 'tree_id'):
            self.parse_item(item)
    
        for subtree in self.tree.values():
            for idx, item in enumerate(subtree, 1):
                if item not in self.found:
                    item.lft = idx
                    self.found.append(item)
                else:
                    item.rght = idx
    
    def save(self):
        for item in self.found:
            item.save()
    

class Command(LabelCommand):
    args = '<app.Model app.Model ...>'
    label = 'app.Model'
    help = 'Repair a corrupt MPTT tree for specified model (in app.Model format).'

    def handle_label(self, arg, **options):
        verbosity = int(options.get('verbosity', 1))
        assert len(arg.split('.')) == 2, 'Arguments must be in app.Model format.'
        model = get_model(*arg.split('.'))
        assert issubclass(model, MPTTModel), 'The model must be an MPTT model.'
        parser = Parser(model)
        parser.save()
