"""CLI commands for the Product aggregate."""

from __future__ import annotations

import click

from oms.application.add_product import AddProductHandler
from oms.application.update_product import UpdateProductHandler
from oms.domain.exceptions import DomainException
from oms.infrastructure.bootstrap import product_repository


@click.command("add")
@click.option("--name", required=True, help="Product name.")
@click.option("--price", required=True, help="Price (e.g. 15.00).")
def product_add(name: str, price: str) -> None:
    """Add a new product to the catalog."""
    handler = AddProductHandler(product_repo=product_repository())

    try:
        product = handler.handle(name=name, price=price)
    except DomainException as exc:
        raise click.ClickException(str(exc))

    click.echo(f"Product #{product.id} '{product.name}' added at {product.price}")


@click.command("list")
def product_list() -> None:
    """List all products in the catalog."""
    repo = product_repository()
    products = repo.list_all()

    if not products:
        click.echo("No products found.")
        return

    click.echo(f"{'ID':<6} {'Name':<20} {'Price':>10}")
    click.echo("-" * 38)
    for p in products:
        click.echo(f"{p.id:<6} {p.name:<20} {str(p.price):>10}")


@click.command("update")
@click.option("--id", "product_id", required=True, help="Product ID.")
@click.option("--price", required=True, help="New price (e.g. 29.99).")
def product_update(product_id: str, price: str) -> None:
    """Update a product's price."""
    handler = UpdateProductHandler(product_repo=product_repository())

    try:
        handler.handle(product_id=product_id, new_price=price)
    except DomainException as exc:
        raise click.ClickException(str(exc))

    click.echo(f"Product #{product_id} price updated to ${price}")
