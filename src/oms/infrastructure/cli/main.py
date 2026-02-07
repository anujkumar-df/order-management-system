import click

from oms.infrastructure.cli.order_commands import order_create, order_show
from oms.infrastructure.cli.product_commands import product_list, product_update


@click.group()
def cli() -> None:
    """OMS — Order Management System"""


@cli.group()
def order() -> None:
    """Manage orders."""


@cli.group()
def product() -> None:
    """Manage products."""


# Register subcommands
order.add_command(order_create)
order.add_command(order_show)
product.add_command(product_list)
product.add_command(product_update)
