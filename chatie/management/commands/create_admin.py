from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from decouple import config


class Command(BaseCommand):
    help = 'Creates or resets a superuser using environment variables'

    def handle(self, *args, **options):
        username = config('ADMIN_USERNAME', default=None)
        password = config('ADMIN_PASSWORD', default=None)

        if not username or not password:
            self.stdout.write('ADMIN_USERNAME or ADMIN_PASSWORD not set, skipping.')
            return

        user, created = User.objects.get_or_create(username=username)
        user.set_password(password)
        user.is_superuser = True
        user.is_staff = True
        user.save()

        if created:
            self.stdout.write(f'Created new superuser: {username}')
        else:
            self.stdout.write(f'Reset password for existing superuser: {username}')