"""CLI commands for inventory management."""

from __future__ import annotations

import click

from oms.application.set_inventory import SetInventoryHandler
from oms.application.show_inventory import ShowInventoryHandler
from oms.domain.exceptions import DomainException
from oms.infrastructure.bootstrap import inventory_repository, product_repository


@click.command("set")
@click.option("--product", required=True, help="Product name.")
@click.option("--quantity", required=True, type=int, help="Total quantity in stock.")
def inventory_set(product: str, quantity: int) -> None:
    """Set inventory level for a product."""
    handler = SetInventoryHandler(
        inventory_repo=inventory_repository(),
        product_repo=product_repository(),
    )

    try:
        handler.handle(product_name=product, quantity=quantity)
    except DomainException as exc:
        raise click.ClickException(str(exc))

    click.echo(f"Inventory for '{product}' set to {quantity}")


@click.command("show")
def inventory_show() -> None:
    """Show current inventory levels."""
    handler = ShowInventoryHandler(inventory_repo=inventory_repository())
    lines = handler.handle()

    if not lines:
        click.echo("No inventory records found.")
        return

    click.echo(f"{'Product':<20} {'Total':>8} {'Reserved':>10} {'Available':>10}")
    click.echo("-" * 50)
    for line in lines:
        click.echo(
            f"{line.product_name:<20} {line.total:>8} {line.reserved:>10} {line.available:>10}"
        )
