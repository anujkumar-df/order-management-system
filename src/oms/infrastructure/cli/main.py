import click

from oms.infrastructure.cli.inventory_commands import inventory_set, inventory_show
from oms.infrastructure.cli.order_commands import (
    order_cancel,
    order_confirm,
    order_create,
    order_fulfill,
    order_show,
)
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


@cli.group()
def inventory() -> None:
    """Manage inventory."""


# Register subcommands
order.add_command(order_cancel)
order.add_command(order_confirm)
order.add_command(order_create)
order.add_command(order_fulfill)
order.add_command(order_show)
product.add_command(product_list)
product.add_command(product_update)
inventory.add_command(inventory_set)
inventory.add_command(inventory_show)
