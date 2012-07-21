from optparse import make_option

from django.core.management.base import BaseCommand

from south.migration import Migrations
from south.exceptions import NoMigrations
from south.management.commands.schemamigration import Command as SchemaMigration

from ...models import LumpyContent
from ...utils import get_subclasses

class ExitCommand(Exception):
    pass

command_log = []
unchanged_count = 0

def error_log(self, error):
    global command_log
    global unchanged_count
    if error.startswith('You cannot use automatic detection'):
        raise Exception(error)
    elif error.startswith('Nothing seems to have changed.'):
        unchanged_count += 1
    command_log.append(error)
    raise ExitCommand()

class Command(BaseCommand):
    processor = None
    option_list = BaseCommand.option_list + (
        make_option('--force', action='store_true', dest='force', default=False, help='Create migrations regardless of other changes.'),
        make_option('--dry-run', action='store_true', dest='dry_run', default=False, help='Show the list of apps with lumps without creating migrations.'),
        )
    help = 'Create schema migrations for all apps using lumpy models.'

    def handle(self, *args, **options):
        global command_log
        global unchanged_count
        unchanged_count = 0
        ok_to_migrate = True
        force = options.pop('force', False)
        dry_run = options.pop('dry_run', False)
        verbosity = int(options.get('verbosity', 1))
        
        # Workaround South's sneaky method of ending commands with error() calls
        SchemaMigration.error = error_log
        # Get list of apps that have models which subclass LumpyContent
        apps_to_migrate = [model._meta.app_label for model in get_subclasses(LumpyContent)]
        if verbosity:
            print 'Automatic schema migrations will be created for the following apps:'
            print '\t%s' % ', '.join(apps_to_migrate)
        # Exit if running a dry run
        if dry_run:
            return
        # First check if the apps already have migrations
        for app in apps_to_migrate:
            try:
                existing_migrations = Migrations(app, force_creation=False, verbose_creation=False)
                if not existing_migrations:
                    raise NoMigrations(app)
            except NoMigrations:
                if not force:
                    print 'The app "%s" is not tracked by South, either create an initial migration or run this command with "--force" to do so automatically.' % app
                    ok_to_migrate = False
        # Now migrate the apps
        if ok_to_migrate:
            for app in apps_to_migrate:
                try:
                    SchemaMigration().handle(app, auto=True, interactive=False, **options)
                except ExitCommand:
                    pass
            if verbosity > 1:
                print 'Done. The output from the commands was:\n\t',
                print '\n\t'.join(command_log)
            elif verbosity:
                if unchanged_count == len(apps_to_migrate):
                    print 'No changes detected in any of the above apps.'
                else:
                    print 'Finished creating migrations.'
        
