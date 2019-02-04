import logging

import click

from app import create_app

app = create_app('config')


@app.cli.command('create_superuser')
@click.argument('email')
@click.argument('password')
def create_superuser(email, password):
    from app.services.superuser import create_admin
    create_admin(email, password)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    app.run(debug=True, host=app.config['HOST'], port=app.config['PORT'])
