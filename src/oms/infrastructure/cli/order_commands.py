"""CLI commands for the Order aggregate."""

from __future__ import annotations

import click

from oms.application.cancel_order import CancelOrderHandler
from oms.application.confirm_order import ConfirmOrderHandler
from oms.application.create_order import CreateOrderHandler
from oms.application.dto import OrderItemSpec
from oms.application.fulfill_order import FulfillOrderHandler
from oms.application.show_order import ShowOrderHandler
from oms.domain.exceptions import DomainException
from oms.infrastructure.bootstrap import (
    inventory_repository,
    order_repository,
    product_repository,
)


def _parse_items(raw: str) -> list[OrderItemSpec]:
    """Parse 'Widget:3,Gadget:5' into OrderItemSpec list."""
    specs: list[OrderItemSpec] = []
    for pair in raw.split(","):
        pair = pair.strip()
        if ":" not in pair:
            raise click.BadParameter(
                f"Invalid item format '{pair}'. Expected 'ProductName:Quantity'."
            )
        name, qty_str = pair.rsplit(":", 1)
        try:
            qty = int(qty_str)
        except ValueError:
            raise click.BadParameter(
                f"Invalid quantity '{qty_str}' for product '{name}'."
            )
        specs.append(OrderItemSpec(product_name=name.strip(), quantity=qty))
    return specs


@click.command("create")
@click.option("--customer", required=True, help="Customer name.")
@click.option("--items", required=True, help="Items as 'Product:Qty,Product:Qty'.")
def order_create(customer: str, items: str) -> None:
    """Create a new purchase order."""
    specs = _parse_items(items)

    handler = CreateOrderHandler(
        order_repo=order_repository(),
        product_repo=product_repository(),
    )

    try:
        dto = handler.handle(customer_name=customer, item_specs=specs)
    except DomainException as exc:
        raise click.ClickException(str(exc))

    click.echo(f"Order #{dto.id} created  (status={dto.status})")
    click.echo(f"Customer: {dto.customer_name}")
    click.echo()
    click.echo(f"  {'Product':<20} {'Qty':>5} {'Price':>10} {'Total':>10}")
    click.echo(f"  {'-'*47}")
    for item in dto.items:
        click.echo(
            f"  {item.product_name:<20} {item.quantity:>5} {item.unit_price:>10} {item.line_total:>10}"
        )
    click.echo(f"  {'-'*47}")
    click.echo(f"  {'Order Total':<27} {dto.total:>20}")


def _display_order(dto) -> None:
    """Shared formatting for displaying an order."""
    click.echo(f"Order #{dto.id}  (status={dto.status})")
    click.echo(f"Customer: {dto.customer_name}")
    click.echo(f"Created:  {dto.created_at}")
    click.echo()

    if dto.has_shipments:
        # Extended table with shipped / remaining columns
        click.echo(
            f"  {'Product':<20} {'Qty':>5} {'Shipped':>8} {'Remaining':>10} {'Price':>10} {'Total':>10}"
        )
        click.echo(f"  {'-'*65}")
        for item in dto.items:
            click.echo(
                f"  {item.product_name:<20} {item.quantity:>5} "
                f"{item.shipped_quantity:>8} {item.remaining_quantity:>10} "
                f"{item.unit_price:>10} {item.line_total:>10}"
            )
        click.echo(f"  {'-'*65}")
    else:
        click.echo(f"  {'Product':<20} {'Qty':>5} {'Price':>10} {'Total':>10}")
        click.echo(f"  {'-'*47}")
        for item in dto.items:
            click.echo(
                f"  {item.product_name:<20} {item.quantity:>5} {item.unit_price:>10} {item.line_total:>10}"
            )
        click.echo(f"  {'-'*47}")

    click.echo(f"  {'Order Total':<27} {dto.total:>20}")


@click.command("show")
@click.option("--id", "order_id", required=True, type=int, help="Order ID to display.")
def order_show(order_id: int) -> None:
    """Show details of an existing order."""
    handler = ShowOrderHandler(order_repo=order_repository())

    try:
        dto = handler.handle(order_id)
    except DomainException as exc:
        raise click.ClickException(str(exc))

    _display_order(dto)


@click.command("confirm")
@click.option("--id", "order_id", required=True, type=int, help="Order ID to confirm.")
def order_confirm(order_id: int) -> None:
    """Confirm a draft order (reserves inventory)."""
    handler = ConfirmOrderHandler(
        order_repo=order_repository(),
        inventory_repo=inventory_repository(),
    )

    try:
        handler.handle(order_id)
    except DomainException as exc:
        raise click.ClickException(str(exc))

    click.echo(f"Order #{order_id} confirmed — inventory reserved.")


@click.command("cancel")
@click.option("--id", "order_id", required=True, type=int, help="Order ID to cancel.")
def order_cancel(order_id: int) -> None:
    """Cancel an order (releases reserved inventory if confirmed)."""
    handler = CancelOrderHandler(
        order_repo=order_repository(),
        inventory_repo=inventory_repository(),
    )

    try:
        handler.handle(order_id)
    except DomainException as exc:
        raise click.ClickException(str(exc))

    click.echo(f"Order #{order_id} cancelled.")


def _parse_fulfill_items(raw: str) -> dict[str, int]:
    """Parse 'Widget:20,Gadget:10' into {name: qty} dict."""
    result: dict[str, int] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if ":" not in pair:
            raise click.BadParameter(
                f"Invalid item format '{pair}'. Expected 'ProductName:Quantity'."
            )
        name, qty_str = pair.rsplit(":", 1)
        try:
            qty = int(qty_str)
        except ValueError:
            raise click.BadParameter(
                f"Invalid quantity '{qty_str}' for product '{name}'."
            )
        result[name.strip()] = qty
    return result


@click.command("fulfill")
@click.option("--id", "order_id", required=True, type=int, help="Order ID to fulfill.")
@click.option("--partial", is_flag=True, default=False, help="Partial fulfillment mode.")
@click.option("--items", "items_str", default=None, help="Items to ship as 'Product:Qty,Product:Qty'.")
def order_fulfill(order_id: int, partial: bool, items_str: str | None) -> None:
    """Fulfill an order (ships items, deducts inventory).

    Without --partial: fulfills all remaining items.
    With --partial --items: fulfills specified quantities only.
    """
    if partial and not items_str:
        raise click.ClickException("--partial requires --items")

    handler = FulfillOrderHandler(
        order_repo=order_repository(),
        inventory_repo=inventory_repository(),
    )

    partial_items = _parse_fulfill_items(items_str) if items_str else None

    try:
        handler.handle(order_id, partial_items=partial_items)
    except DomainException as exc:
        raise click.ClickException(str(exc))

    if partial:
        click.echo(f"Order #{order_id} partially fulfilled — items shipped.")
    else:
        click.echo(f"Order #{order_id} fulfilled — items shipped.")
